from __future__ import annotations
from datetime import datetime, timezone
from typing import Any
from .content import (
    DEFAULT_LEARNER,
    SOURCE_VERSION,
    answer_key_for,
    item_by_id,
    item_for_section,
    resolve_section_and_item,
    source,
    source_catalog,
    source_version_info,
)
from .db import Store
from .evaluator import evaluate_attempt, evaluate_explain_back, evaluate_transfer
from .schemas import AttemptBody, ExplainBody, HintBody, TransferBody
from .sections import section

TRANSITIONS = {
    "attempt_1_open": {"diagnosis", "retry", "source_review", "clarify", "out_of_scope", "explain_back"},
    "diagnosis": {"retry", "source_review", "evaluating_attempt", "explain_back"},
    "retry": {"evaluating_attempt", "retry", "source_review", "diagnosis", "explain_back"},
    "explain_back": {"transfer_check", "explain_back"},
    "transfer_check": {"completed", "transfer_check"},
    "source_review": {"attempt_1_open", "retry", "source_review"},
    "clarify": {"attempt_1_open", "retry", "source_review"},
    "out_of_scope": {"attempt_1_open", "retry", "source_review"},
    "completed": set(),
}


class DomainError(Exception):
    def __init__(self, code: str, status: int = 400, message: str | None = None):
        self.code, self.status, self.message = code, status, message or code


def citations(ids: list[str]) -> list[dict[str, Any]]:
    result = []
    for code in ids:
        item = source(code)
        if not item:
            continue
        page = None
        for location in item.get("approvedLocations", []):
            if location.get("kind") == "slide" and location.get("page"):
                page = location["page"]
                break
        result.append(
            {
                "sourceId": item["sourceId"],
                "label": item["locator"],
                "page": page,
                "excerpt": item["excerpt"],
                "locations": item["approvedLocations"],
            }
        )
    return result


def public_session(row: Any, attempts: list[Any], progress: dict[str, Any] | None = None) -> dict[str, Any]:
    item = item_by_id(row["item_id"])
    if not item:
        item = item_for_section(row["section_id"])
        if not item:
            raise DomainError("ITEM_NOT_FOUND", 500, "Session references an item that no longer exists in the content catalog")
    payload = {
        "sessionId": row["id"],
        "sectionId": row["section_id"],
        "itemId": row["item_id"],
        "stateVersion": row["state_version"],
        "state": row["state"],
        "hintLevel": row["hint_level"],
        "item": item,
        "sources": source_catalog(row["item_id"]),
        "attempts": [
            {
                "attemptNo": a["sequence"],
                "kind": a["kind"],
                "objectiveStatus": a["objective_status"],
                "errorCode": a["error_code"],
            }
            for a in attempts
        ],
    }
    if progress is not None:
        payload["progress"] = {
            "unlockedAttempts": sorted(progress["unlockedAttempts"]),
            "unlockedSlides": sorted(progress["unlockedSlides"]),
            "completedSections": sorted(progress["completedSections"]),
        }
    return payload


class Orchestrator:
    def __init__(self, store: Store, coach: Any, mode: str = "offline", learner_id: str = DEFAULT_LEARNER):
        self.store, self.coach, self.mode, self.learner_id = store, coach, mode, learner_id

    def require(self, session_id: str) -> Any:
        row = self.store.session(session_id)
        if not row:
            raise DomainError("SESSION_NOT_FOUND", 404)
        if datetime.fromisoformat(row["expires_at"]) < datetime.now(timezone.utc):
            raise DomainError("SESSION_EXPIRED", 410)
        return row

    def transition(self, row: Any, state: str, hint: int | None = None) -> Any:
        if state not in TRANSITIONS.get(row["state"], set()):
            raise DomainError("INVALID_TRANSITION", 409)
        try:
            return self.store.update_session(row["id"], row["state_version"], state, hint)
        except ValueError as e:
            raise DomainError(str(e), 409)

    def sections(self) -> dict[str, Any]:
        views = self.store.section_views(self.learner_id)
        progress = self.store.progress(self.learner_id)
        completed = len(progress["completedSections"])
        return {
            "day": {
                "dayId": "day-04",
                "label": "Bài 4 · DAY04",
                "title": "Prompt Engineering & Tool Calling",
                "totalSections": len(views),
                "completedSections": completed,
                "progressPercent": round((completed / max(len(views), 1)) * 100),
            },
            "sections": views,
            "progress": {
                "unlockedAttempts": sorted(progress["unlockedAttempts"]),
                "unlockedSlides": sorted(progress["unlockedSlides"]),
                "completedSections": sorted(progress["completedSections"]),
            },
        }

    def create(self, section_id: str = "prompt-fundamentals", item_id: str | None = None) -> dict[str, Any]:
        if item_id == "prompt-clarity-01":
            item_id = None
        try:
            meta, item = resolve_section_and_item(section_id if not item_id else None, item_id)
        except KeyError as error:
            raise DomainError(str(error), 400)
        section_id = meta["sectionId"]
        progress = self.store.progress(self.learner_id)
        if section_id not in progress["unlockedAttempts"]:
            raise DomainError("SECTION_ATTEMPT_LOCKED", 403, "Hoàn thành lần thử phần trước để mở phần này.")
        row = self.store.create_session(item["itemId"], item["version"], section_id)
        self.store.event(
            row["id"],
            "session_created",
            {
                "item_id": item["itemId"],
                "item_version": item["version"],
                "section_id": section_id,
                "source_version": SOURCE_VERSION,
                "mode": self.mode,
            },
        )
        return {
            **public_session(row, [], self.store.progress(self.learner_id)),
            "expiresAt": row["expires_at"],
            "sourceVersion": source_version_info(item["itemId"]),
        }

    def get(self, session_id: str) -> dict[str, Any]:
        row = self.require(session_id)
        return public_session(row, self.store.attempts(session_id), self.store.progress(self.learner_id))

    def coach_payload(self, result: dict[str, Any], status: str) -> dict[str, Any]:
        draft = result["draft"]
        cited = citations(draft["citationIds"])
        return {
            "status": status,
            "provider": result["provider"],
            "model": result.get("model"),
            "fallback": bool(result.get("fallbackReason")),
            "fallbackReason": result.get("fallbackReason"),
            "confidence": draft["confidence"],
            "diagnosisCode": draft["diagnosisCode"],
            "message": draft["learnerMessage"],
            "hint": {
                "level": draft["hintLevel"],
                "text": draft["learnerMessage"],
                "citations": cited,
            }
            if draft.get("hintLevel")
            else None,
            "citations": cited,
            "highlight": {
                "assumption": None,
                "pages": [c["page"] for c in cited if c.get("page")],
                "excerpts": [c["excerpt"] for c in cited],
            },
        }

    def submit_attempt(self, session_id: str, body: AttemptBody) -> dict[str, Any]:
        row = self.require(session_id)
        if body.stateVersion != row["state_version"]:
            raise DomainError("STATE_VERSION_CONFLICT", 409)
        if row["state"] not in {"attempt_1_open", "retry", "diagnosis"}:
            raise DomainError("INVALID_STATE", 409)
        if body.kind == "attempt_1" and row["state"] != "attempt_1_open":
            raise DomainError("INVALID_ATTEMPT_KIND", 409)
        if body.kind == "retry" and row["state"] not in {"retry", "diagnosis"}:
            raise DomainError("INVALID_ATTEMPT_KIND", 409)
        attempt_no = len(self.store.attempts(session_id)) + 1
        if attempt_no > 3:
            raise DomainError("ATTEMPT_LIMIT", 409)

        item_id = row["item_id"]
        objective = evaluate_attempt(body.answer.text, body.answer.explanation, body.basis, item_id)
        self.store.event(
            session_id,
            "attempt_submitted",
            {
                "attempt_no": attempt_no,
                "objective_status": objective["status"],
                "error_code": objective["errorCode"],
                "confidence": body.confidence,
                "basis": body.basis,
                "section_id": row["section_id"],
                "input_chars": len(body.answer.text) + len(body.answer.explanation),
            },
        )

        # First attempt unlocks this section's slides and the next section's attempt slot.
        progress = self.store.unlock_after_attempt(row["section_id"], self.learner_id)
        unlocked_next = None
        following = section(row["section_id"])
        if following:
            from .sections import next_section as _next
            nxt = _next(row["section_id"])
            unlocked_next = nxt["sectionId"] if nxt else None

        if objective["status"] == "clarify":
            next_row = self.transition(row, "clarify")
            self.store.event(session_id, "clarification_requested", {"attempt_no": attempt_no, "reason_code": objective["reason"]})
            return {
                "stateVersion": next_row["state_version"],
                "attempted": False,
                "evaluation": {"status": "unknown", "errorCode": None},
                "coach": {
                    "status": "clarify",
                    "message": "Mình đã nhận câu trả lời, nhưng chưa đủ để biết bạn đang dùng giả định nào.",
                    "citations": [],
                },
                "next": {"state": "clarify"},
                "progress": {
                    "unlockedAttempts": sorted(progress["unlockedAttempts"]),
                    "unlockedSlides": sorted(progress["unlockedSlides"]),
                    "completedSections": sorted(progress["completedSections"]),
                    "unlockedNextSectionId": unlocked_next,
                },
            }

        attempt = self.store.insert_attempt(
            {
                "session_id": session_id,
                "sequence": attempt_no,
                "kind": body.kind,
                "answer_text": body.answer.text,
                "explanation": body.answer.explanation,
                "confidence": body.confidence,
                "basis": body.basis,
                "objective_status": objective["status"],
                "error_code": objective["errorCode"],
            }
        )

        if objective["status"] == "out_of_scope":
            next_row = self.transition(row, "out_of_scope")
            self.store.event(session_id, "out_of_scope", {"attempt_no": attempt_no, "reason": objective["reason"]})
            return {
                "stateVersion": next_row["state_version"],
                "attempted": True,
                "attemptNo": attempt_no,
                "evaluation": {"status": objective["status"], "errorCode": None},
                "coach": {
                    "status": "out_of_scope",
                    "message": "Câu hỏi này nằm ngoài lát cắt Day 04 đã duyệt; VError không đoán thay bạn.",
                    "citations": [],
                },
                "next": {"state": "out_of_scope"},
                "progress": {
                    "unlockedAttempts": sorted(progress["unlockedAttempts"]),
                    "unlockedSlides": sorted(progress["unlockedSlides"]),
                    "completedSections": sorted(progress["completedSections"]),
                    "unlockedNextSectionId": unlocked_next,
                },
            }

        if objective["status"] == "unknown":
            next_row = self.transition(row, "source_review")
            self.store.event(session_id, "fallback_used", {"attempt_no": attempt_no, "fallback_reason": objective["reason"], "evidence_ids": []})
            return {
                "stateVersion": next_row["state_version"],
                "attempted": True,
                "attemptNo": attempt_no,
                "evaluation": {"status": "unknown", "errorCode": None},
                "coach": {
                    "status": "abstain",
                    "message": "Mình chưa có đủ căn cứ để kết luận bạn đang mắc lỗi nào. Hãy mở slide vừa mở khóa và thử lại.",
                    "citations": [],
                },
                "next": {"state": "source_review"},
                "progress": {
                    "unlockedAttempts": sorted(progress["unlockedAttempts"]),
                    "unlockedSlides": sorted(progress["unlockedSlides"]),
                    "completedSections": sorted(progress["completedSections"]),
                    "unlockedNextSectionId": unlocked_next,
                },
            }

        key = answer_key_for(item_id)
        if objective["status"] == "correct":
            anchor = list(key["allowed_sources"].values())[0][:1]
            next_row = self.transition(row, "explain_back")
            self.store.event(
                session_id,
                "diagnosis_returned",
                {"attempt_no": attempt_no, "objective_status": "correct", "provider": "deterministic", "citation_ids": anchor},
            )
            return {
                "stateVersion": next_row["state_version"],
                "attempted": True,
                "attemptNo": attempt_no,
                "evaluation": {"status": "correct", "errorCode": None},
                "coach": {
                    "status": "probe",
                    "message": "Lần thử này phù hợp với ý chính của phần này. Một câu đúng chưa đủ; hãy giảng lại và làm case chuyển giao.",
                    "citations": citations(anchor),
                    "highlight": {"assumption": None, "pages": [c.get("page") for c in citations(anchor)], "excerpts": [c["excerpt"] for c in citations(anchor)]},
                },
                "next": {"state": "explain_back"},
                "progress": {
                    "unlockedAttempts": sorted(progress["unlockedAttempts"]),
                    "unlockedSlides": sorted(progress["unlockedSlides"]),
                    "completedSections": sorted(progress["completedSections"]),
                    "unlockedNextSectionId": unlocked_next,
                },
            }

        code = objective["errorCode"]
        result = self.coach.generate(
            code,
            0,
            body.answer.text,
            body.answer.explanation,
            [source(s) for s in key["allowed_sources"][code] if source(s)],
            item_id,
        )
        next_row = self.transition(row, "diagnosis" if attempt_no == 1 else "retry", row["hint_level"])
        self.store.insert_coach_output(
            {
                "attempt_id": attempt["id"],
                "provider": result["provider"],
                "model": result.get("model"),
                "diagnosis_code": result["draft"]["diagnosisCode"],
                "confidence_band": result["draft"]["confidence"],
                "hint_level": result["draft"].get("hintLevel"),
                "citation_ids": result["draft"]["citationIds"],
                "fallback_reason": result.get("fallbackReason"),
            }
        )
        self.store.event(
            session_id,
            "diagnosis_returned",
            {"attempt_no": attempt_no, "diagnosis_code": code, "provider": result["provider"], "citation_ids": result["draft"]["citationIds"]},
        )
        return {
            "stateVersion": next_row["state_version"],
            "attempted": True,
            "attemptNo": attempt_no,
            "evaluation": {"status": "incorrect", "errorCode": code},
            "coach": self.coach_payload(result, "diagnosed"),
            "next": {"state": next_row["state"], "allowedAttemptsRemaining": 3 - attempt_no},
            "progress": {
                "unlockedAttempts": sorted(progress["unlockedAttempts"]),
                "unlockedSlides": sorted(progress["unlockedSlides"]),
                "completedSections": sorted(progress["completedSections"]),
                "unlockedNextSectionId": unlocked_next,
            },
        }

    def hint(self, session_id: str, body: HintBody) -> dict[str, Any]:
        row = self.require(session_id)
        if body.stateVersion != row["state_version"]:
            raise DomainError("STATE_VERSION_CONFLICT", 409)
        if row["state"] not in {"diagnosis", "retry"}:
            raise DomainError("INVALID_STATE", 409)
        attempts = self.store.attempts(session_id)
        latest = attempts[-1] if attempts else None
        code = latest["error_code"] if latest else None
        if not code:
            raise DomainError("NO_GROUNDED_DIAGNOSIS", 409)
        expected = row["hint_level"] + 1
        if body.level != expected:
            raise DomainError("HINT_SEQUENCE_INVALID", 409)
        key = answer_key_for(row["item_id"])
        result = self.coach.generate(
            code,
            body.level,
            latest["answer_text"],
            latest["explanation"],
            [source(s) for s in key["allowed_sources"][code] if source(s)],
            row["item_id"],
        )
        next_row = self.transition(row, "retry", body.level)
        self.store.insert_coach_output(
            {
                "attempt_id": latest["id"],
                "provider": result["provider"],
                "model": result.get("model"),
                "diagnosis_code": code,
                "confidence_band": result["draft"]["confidence"],
                "hint_level": body.level,
                "citation_ids": result["draft"]["citationIds"],
                "fallback_reason": result.get("fallbackReason"),
            }
        )
        self.store.event(
            session_id,
            "hint_shown",
            {"attempt_no": latest["sequence"], "hint_level": body.level, "citation_ids": result["draft"]["citationIds"], "provider": result["provider"]},
        )
        return {
            "stateVersion": next_row["state_version"],
            "coach": self.coach_payload(result, "hint"),
            "next": {"state": "retry", "allowedAttemptsRemaining": 3 - len(attempts)},
        }

    def explain(self, session_id: str, body: ExplainBody) -> dict[str, Any]:
        row = self.require(session_id)
        if body.stateVersion != row["state_version"]:
            raise DomainError("STATE_VERSION_CONFLICT", 409)
        if row["state"] != "explain_back":
            raise DomainError("INVALID_STATE", 409)
        evaluation = evaluate_explain_back(body.text, row["item_id"])
        next_state = "transfer_check" if evaluation["pass"] else "explain_back"
        next_row = self.transition(row, next_state)
        self.store.event(
            session_id,
            "explain_back_submitted",
            {
                "input_chars": len(body.text),
                "claims": evaluation["claims"],
                "missing_claim_ids": evaluation["missingClaimIds"],
                "pass": evaluation["pass"],
            },
        )
        return {
            "stateVersion": next_row["state_version"],
            "evaluation": {"status": "pass" if evaluation["pass"] else "needs_revision", **evaluation},
            "next": {"state": next_state},
        }

    def transfer(self, session_id: str, body: TransferBody) -> dict[str, Any]:
        row = self.require(session_id)
        if body.stateVersion != row["state_version"]:
            raise DomainError("STATE_VERSION_CONFLICT", 409)
        if row["state"] != "transfer_check":
            raise DomainError("INVALID_STATE", 409)
        passed = evaluate_transfer(body.answer, body.reasoning, row["item_id"])
        next_state = "completed" if passed else "transfer_check"
        next_row = self.transition(row, next_state)
        self.store.event(
            session_id,
            "transfer_submitted",
            {"input_chars": len(body.answer) + len(body.reasoning), "pass": passed},
        )
        progress = self.store.progress(self.learner_id)
        if passed:
            progress = self.store.mark_section_completed(row["section_id"], self.learner_id)
            self.store.event(session_id, "session_completed", {"mastery_status": "demonstrated_in_session", "section_id": row["section_id"]})
        return {
            "stateVersion": next_row["state_version"],
            "evaluation": {"status": "pass" if passed else "needs_revision"},
            "next": {"state": next_state},
            "progress": {
                "unlockedAttempts": sorted(progress["unlockedAttempts"]),
                "unlockedSlides": sorted(progress["unlockedSlides"]),
                "completedSections": sorted(progress["completedSections"]),
            },
        }

    def abstain(self, session_id: str, state_version: int) -> dict[str, Any]:
        row = self.require(session_id)
        if row["state_version"] != state_version:
            raise DomainError("STATE_VERSION_CONFLICT", 409)
        if row["state"] not in {"attempt_1_open", "diagnosis", "retry", "clarify", "source_review"}:
            raise DomainError("INVALID_STATE", 409)
        next_row = self.transition(row, "source_review")
        self.store.event(session_id, "fallback_used", {"fallback_reason": "user_requested_no_basis", "evidence_ids": []})
        return {"stateVersion": next_row["state_version"], "next": {"state": "source_review"}}

    def resume(self, session_id: str, state_version: int) -> dict[str, Any]:
        row = self.require(session_id)
        if row["state_version"] != state_version:
            raise DomainError("STATE_VERSION_CONFLICT", 409)
        if row["state"] not in {"source_review", "out_of_scope", "clarify"}:
            raise DomainError("INVALID_STATE", 409)
        next_state = "retry" if self.store.attempts(session_id) else "attempt_1_open"
        next_row = self.transition(row, next_state)
        return {
            "stateVersion": next_row["state_version"],
            "next": {"state": next_state},
            "session": public_session(next_row, self.store.attempts(session_id), self.store.progress(self.learner_id)),
        }
