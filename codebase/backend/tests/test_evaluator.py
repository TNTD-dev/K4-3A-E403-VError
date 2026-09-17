from app.evaluator import evaluate_attempt, evaluate_explain_back, evaluate_transfer, verify_coach_draft
from app.coach import Coach

def test_misconceptions_are_deterministic():
    assert evaluate_attempt("Có, prompt càng dài và càng nhiều role thì càng tốt.", "Nhiều thông tin làm model thông minh hơn.", "Suy luận")["errorCode"] == "M_PROMPT_LONGER_BETTER"
    assert evaluate_attempt("Cứ thêm context thì output tốt hơn.", "Context càng nhiều càng hữu ích.", "Suy luận")["errorCode"] == "M_MORE_CONTEXT_ALWAYS_BETTER"
    assert evaluate_attempt("Thêm role thật ấn tượng thì tốt hơn.", "Persona làm model thông minh hơn.", "Suy luận")["errorCode"] == "M_CLEVER_ROLE_ALWAYS_BETTER"

def test_safe_and_learning_checks():
    assert evaluate_attempt("", "", "Chưa có căn cứ")["status"] == "unknown"
    assert evaluate_attempt("Giá API bao nhiêu?", "Chi phí cụ thể", "Suy luận")["status"] == "out_of_scope"
    assert evaluate_attempt("Không nhất thiết, prompt rõ Task + Format có thể tốt hơn prompt dài.", "Role chỉ thêm khi cải thiện kết quả.", "Suy luận")["status"] == "correct"
    assert evaluate_explain_back("Prompt rõ nghĩa thay vì prompt dài lan man. Bắt đầu với Task + Format. Token thừa tăng chi phí và nhiễu.")["pass"]
    assert evaluate_transfer("Không nhất thiết, chọn prompt rõ Task và Format.", "Chỉ thêm Context khi cần cho task.")

def test_offline_coach_is_deterministic_without_network():
    result = Coach("offline").generate("M_PROMPT_LONGER_BETTER", 1, "prompt dài", "nhiều token", [])
    assert result["provider"] == "offline"
    assert result["draft"]["citationIds"] == ["D04-P07", "D04-P10"]


def test_coach_citation_is_verified():
    ok, reason, _ = verify_coach_draft({"action":"diagnose_and_hint","diagnosisCode":"M_PROMPT_LONGER_BETTER","confidence":"high","hintLevel":1,"citationIds":["D04-P20"],"learnerMessage":"Hãy kiểm tra nguồn."}, ["M_PROMPT_LONGER_BETTER"], 1, True)
    assert not ok and reason == "citation_not_supported"
