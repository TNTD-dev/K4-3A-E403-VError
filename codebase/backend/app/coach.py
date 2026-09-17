from __future__ import annotations
import json, os
from typing import Any
from .content import CITATION_SUPPORT, answer_key_for
from .evaluator import reviewed_hint, verify_coach_draft
from .schemas import CoachDraft


class Coach:
    def __init__(self, mode: str = "offline"):
        self.mode = mode

    def generate(self, diagnosis: str, level: int, answer: str, reasoning: str, sources: list[dict[str, Any]], item_id: str = "day04-s01-specificity") -> dict[str, Any]:
        allowed = answer_key_for(item_id)["allowed_sources"]
        if level == 0:
            draft = {
                "action": "diagnose_and_hint",
                "diagnosisCode": diagnosis,
                "confidence": "high",
                "hintLevel": None,
                "citationIds": allowed.get(diagnosis, CITATION_SUPPORT.get(diagnosis, []))[:1],
                "learnerMessage": (
                    "Mình thấy bài làm đang dựa trên một giả định cần kiểm tra. "
                    "Hãy đối chiếu đúng trang PDF được gắn trước khi sửa."
                ),
            }
        else:
            text, citations = reviewed_hint(diagnosis, level)
            draft = {
                "action": "diagnose_and_hint",
                "diagnosisCode": diagnosis,
                "confidence": "high",
                "hintLevel": level,
                "citationIds": citations,
                "learnerMessage": text,
            }
        if self.mode != "live" or not os.getenv("OPENAI_API_KEY"):
            return {"provider": "offline", "model": None, "draft": draft}
        try:
            from openai import OpenAI

            # A real call to this model measured ~9s; 8s was cutting it off before it could
            # ever return, so every diagnosis silently fell back to the static message.
            client = OpenAI(api_key=os.environ["OPENAI_API_KEY"], timeout=20, max_retries=1)
            # The initial diagnosis (level 0) anchors on a single primary source, same as
            # the deterministic draft above (`[:1]`) — only offer the model that one
            # source ID so it can't pick a second, differently-ordered one of its own.
            model_sources = sources[:1] if level == 0 else sources
            # GPT-5.6 models use the Responses API. Do not send Chat-Completions-only
            # arguments (such as response_format, temperature or max_tokens), which
            # causes a 400 response from the API.
            response = client.responses.create(
                model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
                # Structured output plus this model's own reasoning tokens both count
                # against the budget; 260 was too tight and truncated the JSON mid-string.
                max_output_tokens=600,
                text={
                    "format": {
                        "type": "json_schema",
                        "name": "coach_draft",
                        "schema": CoachDraft.model_json_schema(),
                        "strict": True,
                    }
                },
                input=[
                    {
                        "role": "system",
                        "content": (
                            "You are a bounded D2 Coach for VLearn. Return JSON only, matching the schema. "
                            "Use only the supplied diagnosis code and source IDs; never invent a citation. "
                            "Do not reveal the full answer or the corrected concept at hint levels 1 or 2. "
                            "hintLevel must be exactly the requestedHintLevel field: JSON null when it is 0, "
                            "otherwise that same integer. Keep learnerMessage under 400 characters. "
                            "citationIds must be a subset of allowedSourceIds — cite every id you were given, no more, no fewer."
                        ),
                    },
                    {
                        "role": "user",
                        "content": json.dumps(
                            {
                                "itemId": item_id,
                                "diagnosisCode": diagnosis,
                                "requestedHintLevel": level,
                                "learnerAnswer": answer,
                                "learnerReasoning": reasoning,
                                "allowedSourceIds": [s["sourceId"] for s in model_sources],
                            },
                            ensure_ascii=False,
                        ),
                    },
                ],
            )
            parsed = json.loads(response.output_text or "{}")
            # The server, not the model, is the source of truth for which hint level was
            # actually requested — override rather than trust the model to echo it back.
            parsed["hintLevel"] = level or None
            ok, reason, checked = verify_coach_draft(parsed, [diagnosis], level, level < 3, allowed)
            if ok and checked:
                return {"provider": "openai", "model": os.getenv("OPENAI_MODEL", "gpt-4o-mini"), "draft": checked.model_dump()}
            return {"provider": "offline", "model": None, "fallbackReason": f"verifier_{reason}", "draft": draft}
        except Exception as error:
            # Keep the UI actionable without ever exposing the API key. The full error
            # remains available server-side via the exception type/message only.
            detail = str(error).replace(os.getenv("OPENAI_API_KEY", "") or "\0", "[redacted]")
            detail = " ".join(detail.split())[:160]
            return {"provider": "offline", "model": None, "fallbackReason": f"{type(error).__name__}: {detail}".rstrip(": "), "draft": draft}
