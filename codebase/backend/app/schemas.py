from __future__ import annotations
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field

Confidence = Literal["Chắc", "Khá chắc", "Chưa chắc"]
Basis = Literal["Đã học trước đó", "Suy luận", "Đoán", "Chưa có căn cứ"]
SessionState = Literal["attempt_1_open", "evaluating_attempt", "diagnosis", "retry", "explain_back", "transfer_check", "source_review", "clarify", "out_of_scope", "completed"]

class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

class CreateSessionBody(StrictModel):
    itemId: Literal["prompt-clarity-01"]
    itemVersion: Literal["2026-09-16.2"] | None = None
    mode: Literal["demo"] | None = None

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
