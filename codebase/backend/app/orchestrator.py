from __future__ import annotations
from datetime import datetime, timezone
from typing import Any
from .content import ANSWER_KEY, ITEM_ID, ITEM_VERSION, PUBLIC_ITEM, SOURCE_VERSION, source, source_catalog
from .db import Store
from .evaluator import evaluate_attempt, evaluate_explain_back, evaluate_transfer, reviewed_hint, verify_coach_draft
from .schemas import AttemptBody, ExplainBody, HintBody, TransferBody

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
    def __init__(self, code: str, status: int = 400, message: str | None = None): self.code, self.status, self.message = code, status, message or code

def citations(ids: list[str]) -> list[dict[str, Any]]:
    return [{"sourceId": item["sourceId"], "label": item["locator"], "locations": item["approvedLocations"]} for code in ids if (item := source(code))]

def public_session(row: Any, attempts: list[Any]) -> dict[str, Any]:
    return {"sessionId": row["id"], "stateVersion": row["state_version"], "state": row["state"], "hintLevel": row["hint_level"], "item": PUBLIC_ITEM, "sources": source_catalog(), "attempts": [{"attemptNo": a["sequence"], "kind": a["kind"], "objectiveStatus": a["objective_status"], "errorCode": a["error_code"]} for a in attempts]}

class Orchestrator:
    def __init__(self, store: Store, coach: Any, mode: str = "offline"): self.store, self.coach, self.mode = store, coach, mode
    def require(self, session_id: str) -> Any:
        row = self.store.session(session_id)
        if not row: raise DomainError("SESSION_NOT_FOUND", 404)
        if datetime.fromisoformat(row["expires_at"]) < datetime.now(timezone.utc): raise DomainError("SESSION_EXPIRED", 410)
        return row
    def transition(self, row: Any, state: str, hint: int | None = None) -> Any:
        if state not in TRANSITIONS.get(row["state"], set()): raise DomainError("INVALID_TRANSITION", 409)
        try: return self.store.update_session(row["id"], row["state_version"], state, hint)
        except ValueError as e: raise DomainError(str(e), 409)
    def create(self) -> dict[str, Any]:
        row = self.store.create_session(ITEM_ID, ITEM_VERSION); self.store.event(row["id"], "session_created", {"item_id": ITEM_ID, "item_version": ITEM_VERSION, "source_version": SOURCE_VERSION, "mode": self.mode}); return {**public_session(row, []), "expiresAt": row["expires_at"]}
    def get(self, session_id: str) -> dict[str, Any]:
        row = self.require(session_id); return public_session(row, self.store.attempts(session_id))
    def coach_payload(self, result: dict[str, Any], status: str) -> dict[str, Any]:
        draft = result["draft"]; return {"status": status, "provider": result["provider"], "model": result.get("model"), "fallback": bool(result.get("fallbackReason")), "fallbackReason": result.get("fallbackReason"), "confidence": draft["confidence"], "diagnosisCode": draft["diagnosisCode"], "message": draft["learnerMessage"], "hint": {"level": draft["hintLevel"], "text": draft["learnerMessage"], "citations": citations(draft["citationIds"])} if draft.get("hintLevel") else None, "citations": citations(draft["citationIds"])}
    def submit_attempt(self, session_id: str, body: AttemptBody) -> dict[str, Any]:
        row = self.require(session_id)
        if body.stateVersion != row["state_version"]: raise DomainError("STATE_VERSION_CONFLICT", 409)
        if row["state"] not in {"attempt_1_open", "retry", "diagnosis"}: raise DomainError("INVALID_STATE", 409)
        if body.kind == "attempt_1" and row["state"] != "attempt_1_open": raise DomainError("INVALID_ATTEMPT_KIND", 409)
        if body.kind == "retry" and row["state"] not in {"retry", "diagnosis"}: raise DomainError("INVALID_ATTEMPT_KIND", 409)
        attempt_no = len(self.store.attempts(session_id)) + 1
        if attempt_no > 3: raise DomainError("ATTEMPT_LIMIT", 409)
        objective = evaluate_attempt(body.answer.text, body.answer.explanation, body.basis)
        self.store.event(session_id, "attempt_submitted", {"attempt_no": attempt_no, "objective_status": objective["status"], "error_code": objective["errorCode"], "confidence": body.confidence, "basis": body.basis, "input_chars": len(body.answer.text) + len(body.answer.explanation)})
        if objective["status"] == "clarify":
            next_row = self.transition(row, "clarify"); self.store.event(session_id, "clarification_requested", {"attempt_no": attempt_no, "reason_code": objective["reason"]}); return {"stateVersion": next_row["state_version"], "attempted": False, "evaluation": {"status": "unknown", "errorCode": None}, "coach": {"status": "clarify", "message": "Mình đã nhận câu trả lời, nhưng chưa đủ để biết bạn đang dùng giả định nào.", "citations": []}, "next": {"state": "clarify"}}
        attempt = self.store.insert_attempt({"session_id": session_id, "sequence": attempt_no, "kind": body.kind, "answer_text": body.answer.text, "explanation": body.answer.explanation, "confidence": body.confidence, "basis": body.basis, "objective_status": objective["status"], "error_code": objective["errorCode"]})
        if objective["status"] == "out_of_scope":
            next_row = self.transition(row, "out_of_scope"); self.store.event(session_id, "out_of_scope", {"attempt_no": attempt_no, "reason": objective["reason"]}); return {"stateVersion": next_row["state_version"], "attempted": True, "attemptNo": attempt_no, "evaluation": {"status": objective["status"], "errorCode": None}, "coach": {"status": "out_of_scope", "message": "Câu hỏi này nằm ngoài lát cắt Prompt Engineering đã được duyệt; VError không đoán thay bạn.", "citations": []}, "next": {"state": "out_of_scope"}}
        if objective["status"] == "unknown":
            next_row = self.transition(row, "source_review"); self.store.event(session_id, "fallback_used", {"attempt_no": attempt_no, "fallback_reason": objective["reason"], "evidence_ids": []}); return {"stateVersion": next_row["state_version"], "attempted": True, "attemptNo": attempt_no, "evaluation": {"status": "unknown", "errorCode": None}, "coach": {"status": "abstain", "message": "Mình chưa có đủ căn cứ để kết luận bạn đang mắc lỗi nào.", "citations": []}, "next": {"state": "source_review"}}
        if objective["status"] == "correct":
            next_row = self.transition(row, "explain_back"); self.store.event(session_id, "diagnosis_returned", {"attempt_no": attempt_no, "objective_status": "correct", "provider": "deterministic", "citation_ids": ["D04-P08"]}); return {"stateVersion": next_row["state_version"], "attempted": True, "attemptNo": attempt_no, "evaluation": {"status": "correct", "errorCode": None}, "coach": {"status": "probe", "message": "Lần thử này phù hợp với answer key. Một câu đúng chưa đủ chứng minh bạn đã hiểu.", "citations": citations(["D04-P08"])}, "next": {"state": "explain_back"}}
        code = objective["errorCode"]; result = self.coach.generate(code, 0, body.answer.text, body.answer.explanation, [source(s) for s in ANSWER_KEY["allowed_sources"][code] if source(s)])
        next_row = self.transition(row, "diagnosis" if attempt_no == 1 else "retry", row["hint_level"]); self.store.insert_coach_output({"attempt_id": attempt["id"], "provider": result["provider"], "model": result.get("model"), "diagnosis_code": result["draft"]["diagnosisCode"], "confidence_band": result["draft"]["confidence"], "hint_level": result["draft"].get("hintLevel"), "citation_ids": result["draft"]["citationIds"], "fallback_reason": result.get("fallbackReason")}); self.store.event(session_id, "diagnosis_returned", {"attempt_no": attempt_no, "diagnosis_code": code, "provider": result["provider"], "citation_ids": result["draft"]["citationIds"]})
        return {"stateVersion": next_row["state_version"], "attempted": True, "attemptNo": attempt_no, "evaluation": {"status": "incorrect", "errorCode": code}, "coach": self.coach_payload(result, "diagnosed"), "next": {"state": next_row["state"], "allowedAttemptsRemaining": 3 - attempt_no}}
    def hint(self, session_id: str, body: HintBody) -> dict[str, Any]:
        row = self.require(session_id)
        if body.stateVersion != row["state_version"]: raise DomainError("STATE_VERSION_CONFLICT", 409)
        if row["state"] not in {"diagnosis", "retry"}: raise DomainError("INVALID_STATE", 409)
        attempts = self.store.attempts(session_id); latest = attempts[-1] if attempts else None; code = latest["error_code"] if latest else None
        if not code: raise DomainError("NO_GROUNDED_DIAGNOSIS", 409)
        expected = row["hint_level"] + 1
        if body.level != expected: raise DomainError("HINT_SEQUENCE_INVALID", 409)
        result = self.coach.generate(code, body.level, latest["answer_text"], latest["explanation"], [source(s) for s in ANSWER_KEY["allowed_sources"][code] if source(s)])
        next_row = self.transition(row, "retry", body.level); self.store.insert_coach_output({"attempt_id": latest["id"], "provider": result["provider"], "model": result.get("model"), "diagnosis_code": code, "confidence_band": result["draft"]["confidence"], "hint_level": body.level, "citation_ids": result["draft"]["citationIds"], "fallback_reason": result.get("fallbackReason")}); self.store.event(session_id, "hint_shown", {"attempt_no": latest["sequence"], "hint_level": body.level, "citation_ids": result["draft"]["citationIds"], "provider": result["provider"]}); return {"stateVersion": next_row["state_version"], "coach": self.coach_payload(result, "hint"), "next": {"state": "retry", "allowedAttemptsRemaining": 3 - len(attempts)}}

    def explain(self, session_id: str, body: ExplainBody) -> dict[str, Any]:
        row = self.require(session_id)
        if body.stateVersion != row["state_version"]: raise DomainError("STATE_VERSION_CONFLICT", 409)
        if row["state"] != "explain_back": raise DomainError("INVALID_STATE", 409)
        evaluation = evaluate_explain_back(body.text); next_state = "transfer_check" if evaluation["pass"] else "explain_back"; next_row = self.transition(row, next_state); self.store.event(session_id, "explain_back_submitted", {"input_chars": len(body.text), "claims": evaluation["claims"], "missing_claim_ids": evaluation["missingClaimIds"], "pass": evaluation["pass"]}); return {"stateVersion": next_row["state_version"], "evaluation": {"status": "pass" if evaluation["pass"] else "needs_revision", **evaluation}, "next": {"state": next_state}}

    def transfer(self, session_id: str, body: TransferBody) -> dict[str, Any]:
        row = self.require(session_id)
        if body.stateVersion != row["state_version"]: raise DomainError("STATE_VERSION_CONFLICT", 409)
        if row["state"] != "transfer_check": raise DomainError("INVALID_STATE", 409)
        passed = evaluate_transfer(body.answer, body.reasoning); next_state = "completed" if passed else "transfer_check"; next_row = self.transition(row, next_state); self.store.event(session_id, "transfer_submitted", {"input_chars": len(body.answer) + len(body.reasoning), "pass": passed})
        if passed: self.store.event(session_id, "session_completed", {"mastery_status": "demonstrated_in_session", "next_action": "open_source"})
        return {"stateVersion": next_row["state_version"], "evaluation": {"status": "pass" if passed else "needs_revision"}, "next": {"state": next_state}}

    def abstain(self, session_id: str, state_version: int) -> dict[str, Any]:
        row = self.require(session_id)
        if row["state_version"] != state_version: raise DomainError("STATE_VERSION_CONFLICT", 409)
        if row["state"] not in {"attempt_1_open", "diagnosis", "retry", "clarify", "source_review"}: raise DomainError("INVALID_STATE", 409)
        next_row = self.transition(row, "source_review"); self.store.event(session_id, "fallback_used", {"fallback_reason": "user_requested_no_basis", "evidence_ids": []}); return {"stateVersion": next_row["state_version"], "next": {"state": "source_review"}}

    def resume(self, session_id: str, state_version: int) -> dict[str, Any]:
        row = self.require(session_id)
        if row["state_version"] != state_version: raise DomainError("STATE_VERSION_CONFLICT", 409)
        if row["state"] not in {"source_review", "out_of_scope", "clarify"}: raise DomainError("INVALID_STATE", 409)
        next_state = "retry" if self.store.attempts(session_id) else "attempt_1_open"; next_row = self.transition(row, next_state); return {"stateVersion": next_row["state_version"], "next": {"state": next_state}, "session": public_session(next_row, self.store.attempts(session_id))}
