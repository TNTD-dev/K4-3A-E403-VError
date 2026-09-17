from fastapi.testclient import TestClient
from app.main import app
from app.db import Store
from app.orchestrator import Orchestrator
from app.coach import Coach

def client():
    app.state.idempotency = {}
    app.state.test_store = Store(":memory:")
    app.state.test_api = Orchestrator(app.state.test_store, Coach("offline"), "offline")
    # Routes use the module singleton, so swap it for an isolated test database.
    import app.main as main
    main.api, main.store = app.state.test_api, app.state.test_store
    return TestClient(app)

def test_contract_keeps_answer_key_private():
    c = client()
    body = c.post("/api/v1/sessions", json={"itemId":"prompt-clarity-01"}).json()
    assert body["item"]["itemId"] == "prompt-clarity-01"
    assert "expectedChoiceId" not in body["item"]
    assert "requiredExplainClaimIds" not in body["item"]
    assert [s["sourceId"] for s in body["sources"]] == ["D04-P07", "D04-P08", "D04-P10", "D04-P20"]

def test_offline_correction_flow():
    c = client(); session = c.post("/api/v1/sessions", json={"itemId":"prompt-clarity-01"}).json(); sid = session["sessionId"]
    first = c.post(f"/api/v1/sessions/{sid}/attempts", headers={"Idempotency-Key":"attempt-001"}, json={"stateVersion":1,"kind":"attempt_1","answer":{"text":"Có, prompt càng dài thì càng tốt.","explanation":"Nhiều thông tin làm model thông minh hơn."},"basis":"Suy luận"})
    assert first.json()["next"]["state"] == "diagnosis"
    hint = c.post(f"/api/v1/sessions/{sid}/hints", json={"stateVersion":2,"level":1})
    assert hint.json()["coach"]["hint"]["citations"][0]["sourceId"] == "D04-P07"
    retry = c.post(f"/api/v1/sessions/{sid}/attempts", headers={"Idempotency-Key":"attempt-002"}, json={"stateVersion":3,"kind":"retry","answer":{"text":"Không nhất thiết, prompt rõ Task + Format tốt hơn.","explanation":"Role chỉ thêm khi cải thiện kết quả."},"basis":"Suy luận"})
    assert retry.json()["next"]["state"] == "explain_back"


def test_stale_state_and_idempotency_are_rejected():
    c = client(); session = c.post("/api/v1/sessions", json={"itemId":"prompt-clarity-01"}).json(); sid = session["sessionId"]
    payload = {"stateVersion": 1, "kind": "attempt_1", "answer": {"text": "Prompt càng dài càng tốt.", "explanation": "Nhiều role luôn tốt hơn."}}
    assert c.post(f"/api/v1/sessions/{sid}/attempts", json=payload).status_code == 400
    assert c.post(f"/api/v1/sessions/{sid}/attempts", headers={"Idempotency-Key":"attempt-003"}, json=payload).status_code == 200
    assert c.post(f"/api/v1/sessions/{sid}/hints", json={"stateVersion": 1, "level": 1}).status_code == 409
