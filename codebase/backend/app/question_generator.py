"""Bounded question wording generator grounded in reviewed lesson sources."""
from __future__ import annotations

import json
import os
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class QuestionDraft(BaseModel):
    # Structured Outputs requires every object in its JSON schema to forbid
    # unspecified fields (additionalProperties: false).
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=8, max_length=120)
    statement: str = Field(min_length=20, max_length=320)
    taskText: str = Field(min_length=20, max_length=420)
    stakes: str = Field(min_length=20, max_length=300)


class QuestionGenerator:
    """Changes question wording only; misconception, sources and answer key stay fixed."""

    def __init__(self, mode: str = "offline"):
        self.mode = mode

    def generate(self, item: dict[str, Any], sources: list[dict[str, Any]]) -> dict[str, Any]:
        reviewed = {
            "provider": "reviewed",
            "model": None,
            "generated": False,
            "fallbackReason": None if self.mode != "live" else "missing_api_key",
            "item": item,
        }
        if self.mode != "live" or not os.getenv("OPENAI_API_KEY"):
            return reviewed

        try:
            from openai import OpenAI

            client = OpenAI(api_key=os.environ["OPENAI_API_KEY"], timeout=15, max_retries=1)
            source_context = [
                {
                    "sourceId": source.get("sourceId"),
                    "locator": source.get("locator"),
                    "excerpt": source.get("excerpt"),
                }
                for source in sources
            ]
            # GPT-5.6 models use the Responses API.  Do not send
            # Chat-Completions-only arguments (such as response_format or
            # temperature), which causes a 400 response from the API.
            response = client.responses.create(
                model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
                max_output_tokens=420,
                text={
                    "format": {
                        "type": "json_schema",
                        "name": "question_draft",
                        "schema": QuestionDraft.model_json_schema(),
                        "strict": True,
                    }
                },
                input=[
                    {
                        "role": "system",
                        "content": (
                            "Bạn là Question Agent của VLearn. Viết lại một pre-quiz Productive Failure bằng tiếng Việt. "
                            "Chỉ thay đổi cách diễn đạt; phải giữ nguyên misconception, phạm vi, mức khó và nguồn đã duyệt. "
                            "Không tiết lộ đáp án, không thêm kiến thức ngoài sourceContext. Trả JSON có đúng bốn field: "
                            "title, statement, taskText, stakes."
                        ),
                    },
                    {
                        "role": "user",
                        "content": json.dumps(
                            {
                                "reviewedItem": {
                                    "title": item["title"],
                                    "statement": item["statement"],
                                    "taskText": item["taskText"],
                                    "stakes": item["stakes"],
                                },
                                "sourceContext": source_context,
                                "constraints": {
                                    "keepItemId": item["itemId"],
                                    "keepSourceIds": item["sources"],
                                    "learnerSeesBeforeSlides": True,
                                },
                            },
                            ensure_ascii=False,
                        ),
                    },
                ],
            )
            parsed = json.loads(response.output_text or "{}")
            draft = QuestionDraft.model_validate(parsed)
            generated_item = {**item, **draft.model_dump()}
            return {
                "provider": "openai",
                "model": os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
                "generated": True,
                "fallbackReason": None,
                "item": generated_item,
            }
        except Exception as error:
            # Keep the UI actionable without ever exposing request headers or
            # the API key. The full error remains in the server console.
            detail = str(error).replace(os.getenv("OPENAI_API_KEY", ""), "[redacted]")
            detail = " ".join(detail.split())[:180]
            return {**reviewed, "fallbackReason": f"{type(error).__name__}: {detail}".rstrip(": ")}
