from app.evaluator import evaluate_attempt, evaluate_explain_back, evaluate_transfer, merge_claim_coverage, verify_coach_draft
from app.coach import Coach
from app.sections import SECTIONS


def test_section_one_misconceptions_are_deterministic():
    item = "day04-s01-specificity"
    assert evaluate_attempt("Có, prompt càng dài và càng nhiều role thì càng tốt.", "Nhiều thông tin làm model thông minh hơn.", "Suy luận", item)["errorCode"] == "M_PROMPT_LONGER_BETTER"
    assert evaluate_attempt("Cứ thêm context thì output tốt hơn.", "Context càng nhiều càng hữu ích.", "Suy luận", item)["errorCode"] == "M_MORE_CONTEXT_ALWAYS_BETTER"
    assert evaluate_attempt("Thêm role thật ấn tượng thì tốt hơn.", "Persona làm model thông minh hơn.", "Suy luận", item)["errorCode"] == "M_CLEVER_ROLE_ALWAYS_BETTER"


def test_each_section_maps_primary_wrong_assumption():
    cases = [
        ("day04-s02-technique-order", "Luôn bật CoT cho mọi task.", "Think step by step mọi lúc.", "M_ALWAYS_USE_COT"),
        ("day04-s03-system-policy", "System prompt càng dài càng ổn định.", "Nhồi 2000 token là kiểm soát được.", "M_LONG_SYSTEM_ALWAYS_BETTER"),
        ("day04-s04-context-select", "Cứ dump toàn bộ chat history vào context.", "Nhét hết thì không sót.", "M_DUMP_ALL_CONTEXT"),
        ("day04-s05-tool-loop", "Model tự chạy tool và API.", "LLM tự execute weather service.", "M_MODEL_RUNS_TOOLS"),
        ("day04-s06-tool-granularity", "Một super-tool handle_all_customer_operations là tiện nhất.", "Ôm hết mọi việc customer.", "M_SUPER_TOOL_ALWAYS"),
        ("day04-s07-parallel-deps", "Cứ gọi mọi tool song song là luôn đúng.", "Parallel mọi thứ cho nhanh.", "M_ALWAYS_PARALLEL"),
        ("day04-s08-lab-evidence", "Lab xong khi script chạy được một lần.", "Test questions là phụ.", "M_RUN_ONCE_ENOUGH"),
    ]
    for item_id, answer, explanation, code in cases:
        result = evaluate_attempt(answer, explanation, "Suy luận", item_id)
        assert result["status"] == "incorrect"
        assert result["errorCode"] == code


def test_safe_and_learning_checks_section_one():
    item = "day04-s01-specificity"
    assert evaluate_attempt("", "", "Chưa có căn cứ", item)["status"] == "unknown"
    assert evaluate_attempt("Giá API bao nhiêu?", "Chi phí cụ thể tokenization detail", "Suy luận", item)["status"] == "out_of_scope"
    assert evaluate_attempt("Không nhất thiết, prompt rõ Task + Format có thể tốt hơn prompt dài.", "Role chỉ thêm khi cải thiện kết quả.", "Suy luận", item)["status"] == "correct"
    assert evaluate_explain_back("Prompt rõ nghĩa thay vì prompt dài lan man. Bắt đầu với Task + Format. Token thừa tăng chi phí và nhiễu.", item)["pass"]
    assert evaluate_transfer("Không nhất thiết, chọn prompt rõ Task và Format JSON.", "Chỉ thêm Context khi cần cho task, không phải lúc nào cũng thêm role.", item)["pass"]


def test_reinforce_merges_regex_hits_with_model_paraphrase():
    required = ["a", "b", "c"]
    present, missing = merge_claim_coverage(required, ["a"], ["a", "c", "invented"])
    assert present == ["a", "c"]
    assert missing == ["b"]
    review = Coach("offline").review_explain("chỉ nói task và format", "day04-s01-specificity")
    assert review["provider"] == "offline"
    assert "task_and_format_first" in review["draft"]["presentClaimIds"]
    assert review["draft"]["missingClaimIds"]
    assert "specificity_beats_cleverness" not in review["draft"]["learnerMessage"]


def test_offline_coach_is_deterministic_without_network():
    result = Coach("offline").generate("M_PROMPT_LONGER_BETTER", 1, "prompt dài", "nhiều token", [], "day04-s01-specificity")
    assert result["provider"] == "offline"
    assert result["draft"]["citationIds"] == ["D04-P07", "D04-P10"]


def test_coach_citation_is_verified():
    ok, reason, _ = verify_coach_draft(
        {
            "action": "diagnose_and_hint",
            "diagnosisCode": "M_PROMPT_LONGER_BETTER",
            "confidence": "high",
            "hintLevel": 1,
            "citationIds": ["D04-P20"],
            "learnerMessage": "Hãy kiểm tra nguồn.",
        },
        ["M_PROMPT_LONGER_BETTER"],
        1,
        True,
    )
    assert not ok and reason == "citation_not_supported"


def test_eight_public_items_exist():
    assert len(SECTIONS) == 8
    assert {item["itemId"] for item in SECTIONS} == {
        "day04-s01-specificity",
        "day04-s02-technique-order",
        "day04-s03-system-policy",
        "day04-s04-context-select",
        "day04-s05-tool-loop",
        "day04-s06-tool-granularity",
        "day04-s07-parallel-deps",
        "day04-s08-lab-evidence",
    }
