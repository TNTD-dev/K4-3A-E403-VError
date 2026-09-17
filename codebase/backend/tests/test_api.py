import json

from fastapi.testclient import TestClient
from app.main import app
from app.db import Store
from app.orchestrator import Orchestrator
from app.coach import Coach
from app.question_generator import QuestionDraft
from app.sections import SECTIONS
from app.slide_agent import SlideAgent


def client():
    app.state.idempotency = {}
    app.state.test_store = Store(":memory:")
    app.state.test_api = Orchestrator(app.state.test_store, Coach("offline"), "offline")
    import app.main as main
    main.api, main.store = app.state.test_api, app.state.test_store
    # Tests must never call a paid provider: pin the Slide Agent to its deterministic reader.
    main.slide_agent = SlideAgent(main.PDF_PATH, "offline")
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


def test_question_generator_endpoint_keeps_private_key_and_sources_bounded():
    c = client()
    body = c.post("/api/v1/sections/prompt-fundamentals/item/generate").json()
    assert body["item"]["itemId"] == "day04-s01-specificity"
    assert body["item"]["sources"] == ["D04-P07", "D04-P08", "D04-P10"]
    assert "expectedConcept" not in body["item"]
    assert "misconceptions" not in body["item"]
    assert body["generation"]["provider"] in {"reviewed", "openai"}
    assert isinstance(body["generation"]["generated"], bool)


def test_question_generator_schema_forbids_unspecified_fields_for_structured_outputs():
    assert QuestionDraft.model_json_schema()["additionalProperties"] is False


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


def test_first_attempt_submit_requires_json_content_type_and_succeeds_with_both_headers():
    """Regression: Idempotency-Key alone without Content-Type yields 422; both headers yield diagnosis."""
    c = client()
    session = c.post("/api/v1/sessions", json={"sectionId": "prompt-fundamentals"}).json()
    sid = session["sessionId"]
    payload = {
        "stateVersion": 1,
        "kind": "attempt_1",
        "answer": {
            "text": "Tôi đồng ý",
            "explanation": "Tôi nghĩ prompt càng dài thì càng chi tiết",
        },
        "confidence": "Khá chắc",
        "basis": "Suy luận",
    }
    missing_ct = c.post(
        f"/api/v1/sessions/{sid}/attempts",
        headers={
            "Idempotency-Key": "attempt-no-ct",
            "Content-Type": "text/plain",
        },
        content=json.dumps(payload),
    )
    assert missing_ct.status_code == 422
    assert missing_ct.json().get("detail")

    ok = c.post(
        f"/api/v1/sessions/{sid}/attempts",
        headers={"Idempotency-Key": "attempt-with-ct"},
        json=payload,
    )
    assert ok.status_code == 200
    assert ok.json()["next"]["state"] == "diagnosis"


def test_slide_agent_detects_title_slides_and_grounds_key_slides_in_section():
    c = client()
    outline = c.get("/api/v1/deck/outline").json()
    assert outline["totalPages"] == 43
    assert [s["titlePage"] for s in outline["sections"]] == [6, 11, 16, 20, 24, 28, 31, 35]
    assert outline["agent"]["provider"] == "deterministic"
    for entry in outline["sections"]:
        assert entry["quizPage"] == entry["titlePage"] + 1
        assert entry["keySlides"], entry["sectionId"]
        for slide in entry["keySlides"]:
            assert entry["startPage"] <= slide["page"] <= entry["endPage"]
            assert slide["grounded"] is True
    # The reviewed excerpt for D04-P15 (system prompt anatomy) lives on PDF p.17 of this deck.
    system = next(s for s in outline["sections"] if s["sectionId"] == "system-prompts")
    assert any("D04-P15" in slide["sourceIds"] and slide["page"] == 17 for slide in system["keySlides"])


def test_key_insight_opens_only_after_attempt_and_stays_on_reviewed_pages():
    c = client()
    locked = c.post("/api/v1/sections/prompt-fundamentals/key-insight", json={})
    assert locked.status_code == 403
    assert locked.json()["error"] == "SLIDES_LOCKED"

    session = c.post("/api/v1/sessions", json={"sectionId": "prompt-fundamentals"}).json()
    attempt = c.post(
        f"/api/v1/sessions/{session['sessionId']}/attempts",
        headers={"Idempotency-Key": "insight-attempt-01"},
        json={
            "stateVersion": 1,
            "kind": "attempt_1",
            "answer": {"text": "Đồng ý, prompt càng dài càng tốt.", "explanation": "Nhiều context giúp model hiểu hơn."},
        },
    )
    assert attempt.status_code == 200

    body = c.post("/api/v1/sections/prompt-fundamentals/key-insight", json={"sessionId": session["sessionId"]}).json()
    pages = [slide["page"] for slide in body["keySlides"]]
    assert pages == [7, 8, 10]
    assert body["insight"]["focusPage"] in pages
    assert body["insight"]["keyPoints"]
    assert body["generation"]["provider"] == "reviewed"

    mismatch = c.post("/api/v1/sections/advanced-prompting/key-insight", json={"sessionId": session["sessionId"]})
    assert mismatch.status_code in {403, 409}


def test_progress_reset_relocks_sections_for_demo():
    c = client()
    session = c.post("/api/v1/sessions", json={"sectionId": "prompt-fundamentals"}).json()
    c.post(
        f"/api/v1/sessions/{session['sessionId']}/attempts",
        headers={"Idempotency-Key": "reset-attempt-01"},
        json={"stateVersion": 1, "kind": "attempt_1", "answer": {"text": "Có", "explanation": "prompt càng dài càng tốt"}},
    )
    assert c.get("/api/v1/sections").json()["sections"][0]["slidesLocked"] is False
    reset = c.post("/api/v1/progress/reset").json()
    assert reset["sections"][0]["slidesLocked"] is True
    assert reset["sections"][0]["attemptLocked"] is False
    assert all(item["attemptLocked"] for item in reset["sections"][1:])
