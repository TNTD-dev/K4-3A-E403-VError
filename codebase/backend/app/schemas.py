from __future__ import annotations
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator
from .sections import SECTIONS

Confidence = Literal["Chắc", "Khá chắc", "Chưa chắc"]
Basis = Literal["Đã học trước đó", "Suy luận", "Đoán", "Chưa có căn cứ"]
SessionState = Literal[
    "attempt_1_open", "evaluating_attempt", "diagnosis", "retry", "explain_back",
    "transfer_check", "source_review", "clarify", "out_of_scope", "completed",
]
SECTION_IDS = {item["sectionId"] for item in SECTIONS}
ITEM_IDS = {item["itemId"] for item in SECTIONS}


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CreateSessionBody(StrictModel):
    itemId: str | None = None
    itemVersion: str | None = None
    sectionId: str = "prompt-fundamentals"
    mode: Literal["demo"] | None = None

    @field_validator("sectionId")
    @classmethod
    def validate_section(cls, value: str) -> str:
        if value not in SECTION_IDS:
            raise ValueError("SECTION_NOT_FOUND")
        return value

    @field_validator("itemId")
    @classmethod
    def validate_item(cls, value: str | None) -> str | None:
        if value is None:
            return value
        if value not in ITEM_IDS and value != "prompt-clarity-01":
            raise ValueError("ITEM_NOT_FOUND")
        return value


class Answer(StrictModel):
    text: str = Field(max_length=500)
    explanation: str = Field(max_length=500)


class AttemptBody(StrictModel):
    stateVersion: int = Field(gt=0)
    kind: Literal["attempt_1", "retry"]
    answer: Answer
    confidence: Confidence | None = None
    basis: Basis | None = None


class HintBody(StrictModel):
    stateVersion: int = Field(gt=0)
    level: Literal[1, 2, 3]


class ExplainBody(StrictModel):
    stateVersion: int = Field(gt=0)
    text: str = Field(min_length=1, max_length=500)


class TransferBody(StrictModel):
    stateVersion: int = Field(gt=0)
    answer: str = Field(max_length=500)
    reasoning: str = Field(max_length=500)


class StateVersionBody(StrictModel):
    stateVersion: int = Field(gt=0)


class CoachDraft(StrictModel):
    action: Literal["diagnose_and_hint", "ask_clarification", "abstain"]
    diagnosisCode: str | None
    confidence: Literal["high", "medium", "low"]
    hintLevel: Literal[1, 2, 3] | None
    citationIds: list[str] = Field(max_length=2)
    learnerMessage: str = Field(min_length=1, max_length=500)
