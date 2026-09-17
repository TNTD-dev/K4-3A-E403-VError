from fastapi.testclient import TestClient
from app.main import app
from app.db import Store
from app.orchestrator import Orchestrator
from app.coach import Coach
from app.sections import SECTIONS


def client():
    app.state.idempotency = {}
    app.state.test_store = Store(":memory:")
    app.state.test_api = Orchestrator(app.state.test_store, Coach("offline"), "offline")
    import app.main as main
    main.api, main.store = app.state.test_api, app.state.test_store
    return TestClient(app)


def test_section_toc_starts_locked_and_unlocks_after_attempt():
    c = client()
    toc = c.get("/api/v1/sections").json()
    sections = toc["sections"]
    assert len(sections) == 8
    assert toc["day"]["label"] == "Bài 4 · DAY04"
    assert sections[0]["attemptLocked"] is False
    assert sections[0]["slidesLocked"] is True
    assert all(item["attemptLocked"] is True for item in sections[1:])

    locked = c.post("/api/v1/sessions", json={"sectionId": "tool-calling"})
    assert locked.status_code == 403

    session = c.post("/api/v1/sessions", json={"sectionId": "prompt-fundamentals"}).json()
    assert session["sectionId"] == "prompt-fundamentals"
    assert session["item"]["itemId"] == SECTIONS[0]["itemId"]
    assert "expectedConcept" not in session["item"]
    assert "requiredExplainClaimIds" not in session["item"]

    first = c.post(
        f"/api/v1/sessions/{session['sessionId']}/attempts",
        headers={"Idempotency-Key": "attempt-lock-001"},
        json={
            "stateVersion": 1,
            "kind": "attempt_1",
            "answer": {"text": "Có, prompt càng dài thì càng tốt.", "explanation": "Nhiều thông tin làm model thông minh hơn."},
            "basis": "Suy luận",
        },
    )
    assert first.status_code == 200
    progress = first.json()["progress"]
    assert "prompt-fundamentals" in progress["unlockedSlides"]
    assert "advanced-prompting" in progress["unlockedAttempts"]

    refreshed = c.get("/api/v1/sections").json()["sections"]
    assert refreshed[0]["slidesLocked"] is False
    assert refreshed[1]["attemptLocked"] is False
    assert refreshed[2]["attemptLocked"] is True


def test_contract_keeps_answer_key_private_for_each_section_item():
    c = client()
    for meta in SECTIONS:
        body = c.get(f"/api/v1/sections/{meta['sectionId']}/item").json()
        assert body["item"]["itemId"] == meta["itemId"]
        assert body["item"]["statement"]
        assert "expectedConcept" not in body["item"]
        assert "misconceptions" not in body["item"]
        assert body["sources"]
        assert all("excerpt" in source for source in body["sources"])


def test_offline_correction_flow_section_one():
    c = client()
    session = c.post("/api/v1/sessions", json={"sectionId": "prompt-fundamentals"}).json()
    sid = session["sessionId"]
    first = c.post(
        f"/api/v1/sessions/{sid}/attempts",
        headers={"Idempotency-Key": "attempt-001"},
        json={
            "stateVersion": 1,
            "kind": "attempt_1",
            "answer": {"text": "Có, prompt càng dài thì càng tốt.", "explanation": "Nhiều thông tin làm model thông minh hơn."},
            "basis": "Suy luận",
        },
    )
    body = first.json()
    assert body["next"]["state"] == "diagnosis"
    assert body["coach"]["highlight"]["pages"]
    hint = c.post(f"/api/v1/sessions/{sid}/hints", json={"stateVersion": 2, "level": 1})
    assert hint.json()["coach"]["hint"]["citations"][0]["sourceId"] == "D04-P07"
    retry = c.post(
        f"/api/v1/sessions/{sid}/attempts",
        headers={"Idempotency-Key": "attempt-002"},
        json={
            "stateVersion": 3,
            "kind": "retry",
            "answer": {"text": "Không nhất thiết, prompt rõ Task + Format tốt hơn.", "explanation": "Role chỉ thêm khi cải thiện kết quả."},
            "basis": "Suy luận",
        },
    )
    assert retry.json()["next"]["state"] == "explain_back"


def test_legacy_item_alias_still_opens_section_one():
    c = client()
    body = c.post("/api/v1/sessions", json={"itemId": "prompt-clarity-01"}).json()
    assert body["sectionId"] == "prompt-fundamentals"
    item = c.get("/api/v1/items/prompt-clarity-01").json()
    assert item["item"]["sectionId"] == "prompt-fundamentals"


def test_stale_state_and_idempotency_are_rejected():
    c = client()
    session = c.post("/api/v1/sessions", json={"sectionId": "prompt-fundamentals"}).json()
    sid = session["sessionId"]
    payload = {
        "stateVersion": 1,
        "kind": "attempt_1",
        "answer": {"text": "Prompt càng dài càng tốt.", "explanation": "Nhiều role luôn tốt hơn."},
    }
    assert c.post(f"/api/v1/sessions/{sid}/attempts", json=payload).status_code == 400
    assert c.post(f"/api/v1/sessions/{sid}/attempts", headers={"Idempotency-Key": "attempt-003"}, json=payload).status_code == 200
    assert c.post(f"/api/v1/sessions/{sid}/hints", json={"stateVersion": 1, "level": 1}).status_code == 409


def test_tool_loop_section_diagnoses_model_runs_tools_myth():
    c = client()
    # Unlock through section 5 by simulating prior attempts' unlock chain via store helpers.
    store = app.state.test_store
    for section_id in [
        "prompt-fundamentals",
        "advanced-prompting",
        "system-prompts",
        "context-engineering",
        "tool-calling",
    ][:-1]:
        store.unlock_after_attempt(section_id)

    session = c.post("/api/v1/sessions", json={"sectionId": "tool-calling"}).json()
    result = c.post(
        f"/api/v1/sessions/{session['sessionId']}/attempts",
        headers={"Idempotency-Key": "tool-loop-001"},
        json={
            "stateVersion": 1,
            "kind": "attempt_1",
            "answer": {"text": "Đúng, model tự chạy API rồi trả lời user luôn.", "explanation": "tool_call nghĩa là model tự execute."},
            "basis": "Suy luận",
        },
    ).json()
    assert result["evaluation"]["errorCode"] == "M_MODEL_RUNS_TOOLS"
    assert any(page == 22 for page in result["coach"]["highlight"]["pages"])
