from __future__ import annotations
import json, os
from typing import Any
from .content import CITATION_SUPPORT, answer_key_for
from .evaluator import reviewed_hint, verify_coach_draft


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
            client = OpenAI(api_key=os.environ["OPENAI_API_KEY"], timeout=6, max_retries=1)
            response = client.chat.completions.create(
                model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
                temperature=0,
                max_tokens=220,
                response_format={"type": "json_object"},
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a bounded D2 Coach. Return JSON only. "
                            "Use only the supplied diagnosis and source IDs. "
                            "Do not reveal the full answer at hint levels 1 or 2."
                        ),
                    },
                    {
                        "role": "user",
                        "content": json.dumps(
                            {
                                "itemId": item_id,
                                "diagnosisCode": diagnosis,
                                "hintLevel": level,
                                "learnerAnswer": answer,
                                "learnerReasoning": reasoning,
                                "allowedSourceIds": [s["sourceId"] for s in sources],
                            },
                            ensure_ascii=False,
                        ),
                    },
                ],
            )
            parsed = json.loads(response.choices[0].message.content or "{}")
            ok, reason, checked = verify_coach_draft(parsed, [diagnosis], level, level < 3, allowed)
            if ok and checked:
                return {"provider": "openai", "model": os.getenv("OPENAI_MODEL", "gpt-4o-mini"), "draft": checked.model_dump()}
            return {"provider": "offline", "model": None, "fallbackReason": f"verifier_{reason}", "draft": draft}
        except Exception as error:
            return {"provider": "offline", "model": None, "fallbackReason": type(error).__name__, "draft": draft}
