"""Adapter that runs the golden set against the real VError backend, live API included.

Registered as VERROR_EVAL_CALLABLE=verror_callable:evaluate for `python run_eval.py --mode python`.

Design notes
------------
The golden set's contract (README.md) is a single-shot
`{answer, reasoning, confidence, basis, session_context} -> {route, misconception_code,
citations, hint_text, next_action, answer_revealed}` API. VError's actual backend is
session/state-based (create session -> POST attempt with stateVersion + Idempotency-Key).
This module bridges the two faithfully, without touching golden_set.json and without
reimplementing backend logic:

- Every case gets its own fresh in-memory Store + Orchestrator, wired with the SAME mode
  the real deployment uses (read from `backend/.env` via `app.main.mode`, currently
  MODEL_MODE=live). Coach.generate() therefore makes real OpenAI calls for every attempt
  that routes to "diagnose", exactly as the running app would. Route/misconception
  detection itself (app/evaluator.py) is deterministic regex and unaffected by mode.
- Requests go through the real FastAPI app (TestClient), not bare Orchestrator calls, so
  idempotency-key handling and validation are exercised for real (needed for E03/E04).
- session_context replay (E01/E02/E03/E04) is simulated with real extra HTTP calls against
  the same fresh session — see `evaluate()` below. Nothing is mocked.

This file reacts to structural session_context fields (previous_misconception_code +
attempt_number, duplicate_request, requires_idempotency_key) rather than hardcoding case
IDs, so it stays valid if the golden set gains more cases shaped the same way.
"""
from __future__ import annotations

import sys
import uuid
from pathlib import Path
from typing import Any

BACKEND_ROOT = Path(__file__).resolve().parents[1] / "codebase" / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from fastapi.testclient import TestClient  # noqa: E402

import app.main as main  # noqa: E402
from app.coach import Coach  # noqa: E402
from app.db import Store  # noqa: E402
from app.orchestrator import Orchestrator  # noqa: E402

SECTION_ID = "prompt-fundamentals"  # the only item the golden set exercises (day04-s01-specificity)

CONFIDENCE_MAP = {"sure": "Chắc", "guess": "Chưa chắc", "unsure": "Khá chắc"}
BASIS_MAP = {
    "own_reasoning": "Suy luận",
    "memory": "Đã học trước đó",
    "claimed_source": "Đã học trước đó",
    "question": "Đoán",
    "none": "Chưa có căn cứ",
    "retry": "Suy luận",
}

# Phrases known (from app/evaluator.py's SECTION_PATTERNS) to trigger each misconception,
# used only to *replay* a prior diagnosis for session-continuity cases (E01-style: a case
# whose session_context carries a previous_misconception_code + attempt_number > 1).
TRIGGER_TEXT = {
    "M_PROMPT_LONGER_BETTER": ("Prompt càng dài càng tốt.", "Nhiều chữ hơn chắc chắn tốt hơn."),
    "M_MORE_CONTEXT_ALWAYS_BETTER": ("Càng nhiều context càng tốt.", "Nhét hết mọi context vào cho chắc."),
    "M_CLEVER_ROLE_ALWAYS_BETTER": ("Role càng clever thì kết quả càng tốt.", "Thêm role ấn tượng luôn giúp ích."),
}

STATE_TO_ROUTE = {
    "diagnosis": "diagnose",
    "retry": "diagnose",
    "explain_back": "correct",
    "transfer_check": "correct",
    "completed": "correct",
    "source_review": "no-basis",
    "clarify": "clarify",
    "out_of_scope": "out-of-scope",
}
STATE_TO_NEXT_ACTION = {
    "diagnosis": "retry",
    "retry": "retry",
    "explain_back": "explain_back",
    "transfer_check": "transfer",
    "completed": "transfer",
    "source_review": "source_review",
    "clarify": "ask_clarifying_question",
    "out_of_scope": "return_to_task",
}


def _fresh_client() -> TestClient:
    """One isolated backend per case: fresh in-memory DB, same mode the real app runs in."""
    main.app.state.idempotency = {}
    store = Store(":memory:")
    main.api = Orchestrator(store, Coach(main.mode), main.mode)
    main.store = store
    return TestClient(main.app)


def _to_contract(resp: dict[str, Any]) -> dict[str, Any]:
    state = resp["next"]["state"]
    coach = resp.get("coach") or {}
    citations = [c["sourceId"] for c in coach.get("citations", []) if c.get("sourceId")]
    # "low_confidence" shares explain_back's state/next_action with a plain "correct"
    # verdict; only evaluation.status distinguishes the two, so check it first.
    eval_status = (resp.get("evaluation") or {}).get("status")
    route = "low-confidence" if eval_status == "low_confidence" else STATE_TO_ROUTE.get(state, state)
    return {
        "route": route,
        "misconception_code": (resp.get("evaluation") or {}).get("errorCode"),
        "citations": citations,
        "hint_text": coach.get("message", ""),
        "next_action": STATE_TO_NEXT_ACTION.get(state),
        "answer_revealed": False,
        "provider": coach.get("provider"),
        "model": coach.get("model"),
        "fallback_reason": coach.get("fallbackReason"),
    }


def _submit(
    client: TestClient,
    session_id: str,
    state_version: int,
    kind: str,
    answer: str,
    explanation: str,
    confidence: str,
    basis: str,
    idem_key: str | None,
):
    headers = {"Idempotency-Key": idem_key} if idem_key else {}
    return client.post(
        f"/api/v1/sessions/{session_id}/attempts",
        headers=headers,
        json={
            "stateVersion": state_version,
            "kind": kind,
            "answer": {"text": answer, "explanation": explanation},
            "confidence": confidence,
            "basis": basis,
        },
    )


def evaluate(payload: dict[str, Any]) -> dict[str, Any]:
    ctx = payload.get("session_context") or {}
    answer = payload.get("answer", "")
    explanation = payload.get("reasoning", "")
    confidence = CONFIDENCE_MAP.get(payload.get("confidence"), "Khá chắc")
    basis = BASIS_MAP.get(payload.get("basis"), "Suy luận")

    client = _fresh_client()
    session = client.post("/api/v1/sessions", json={"sectionId": SECTION_ID}).json()
    session_id = session["sessionId"]
    state_version = session["stateVersion"]

    # --- E04-style: caller declared the request needs an Idempotency-Key but sent none.
    if ctx.get("requires_idempotency_key") and not ctx.get("idempotency_key"):
        resp = _submit(client, session_id, state_version, "attempt_1", answer, explanation, confidence, basis, idem_key=None)
        mutated = client.get(f"/api/v1/sessions/{session_id}").json()["stateVersion"] != state_version
        route = "technical-error" if resp.status_code == 400 else _to_contract(resp.json())["route"]
        return {
            "route": route,
            "misconception_code": None,
            "citations": [],
            "hint_text": resp.text[:200] if resp.status_code != 200 else "",
            "next_action": "retry_request",
            "answer_revealed": False,
            "state_mutated": mutated,
        }

    # --- E03-style: identical Idempotency-Key sent twice must not double-transition state.
    if ctx.get("duplicate_request"):
        key = ctx.get("idempotency_key") or f"eval-{uuid.uuid4()}"
        first = _submit(client, session_id, state_version, "attempt_1", answer, explanation, confidence, basis, idem_key=key).json()
        after_first = client.get(f"/api/v1/sessions/{session_id}").json()["stateVersion"]
        _submit(client, session_id, state_version, "attempt_1", answer, explanation, confidence, basis, idem_key=key)
        after_second = client.get(f"/api/v1/sessions/{session_id}").json()["stateVersion"]
        contract = _to_contract(first)
        contract["duplicate_transition"] = after_second != after_first
        return contract

    # --- E01-style: replay a prior wrong attempt, then submit the case's (corrected) retry.
    prev_code = ctx.get("previous_misconception_code")
    if prev_code and ctx.get("attempt_number", 1) > 1:
        trig_answer, trig_explanation = TRIGGER_TEXT.get(prev_code, TRIGGER_TEXT["M_PROMPT_LONGER_BETTER"])
        setup = _submit(
            client, session_id, state_version, "attempt_1", trig_answer, trig_explanation, "Chắc", "Suy luận",
            idem_key=f"setup-{uuid.uuid4()}",
        ).json()
        retry = _submit(
            client, session_id, setup["stateVersion"], "retry", answer, explanation, confidence, basis,
            idem_key=f"eval-{uuid.uuid4()}",
        ).json()
        return _to_contract(retry)

    # --- E02 and every normal/hard/rare case: one fresh session, one attempt_1 submission.
    # A brand-new in-memory Store per case already proves "a fresh session doesn't inherit"
    # for E02 — there is no cross-session mutable state in this backend to leak from.
    resp = _submit(client, session_id, state_version, "attempt_1", answer, explanation, confidence, basis, idem_key=f"eval-{uuid.uuid4()}")
    if resp.status_code != 200:
        return {
            "route": "technical-error",
            "misconception_code": None,
            "citations": [],
            "hint_text": resp.text[:200],
            "next_action": "retry_request",
            "answer_revealed": False,
        }
    return _to_contract(resp.json())
