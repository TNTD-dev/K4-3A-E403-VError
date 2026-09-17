from __future__ import annotations
import re
from typing import Any
from .content import ANSWER_KEY, source
from .schemas import CoachDraft

MISCONCEPTIONS = tuple(ANSWER_KEY["allowed_sources"])

def find_misconception(text: str) -> str | None:
    if re.search(r"càng dài|prompt dài|dài hơn.*tốt|nhiều token.*tốt|prompt càng", text, re.I):
        return "M_PROMPT_LONGER_BETTER"
    if re.search(r"nhiều context|càng nhiều.*context|nhét.*context|mọi context|context.*càng|thêm context.*tốt|context.*tốt hơn", text, re.I):
        return "M_MORE_CONTEXT_ALWAYS_BETTER"
    if re.search(r"role.*càng|persona.*càng|clever|thông minh hơn.*role|thêm role.*tốt hơn", text, re.I):
        return "M_CLEVER_ROLE_ALWAYS_BETTER"
    return None

def evaluate_attempt(answer: str, explanation: str, basis: str | None = None) -> dict[str, Any]:
    text = f"{answer} {explanation}".strip()
    if not answer.strip() or basis == "Chưa có căn cứ" or re.fullmatch(r"asdf|abc|test|\?+|không biết gì", answer.strip(), re.I):
        return {"status": "unknown", "errorCode": None, "reason": "no_basis"}
    if re.search(r"giá|price|attention|tokenization|viết chương trình|mã nguồn|chi phí cụ thể", text, re.I):
        return {"status": "out_of_scope", "errorCode": None, "reason": "outside_prompt_fixture"}
    if not explanation.strip():
        return {"status": "clarify", "errorCode": None, "reason": "reasoning_missing"}
    positive = bool(re.search(r"càng dài.*càng tốt|càng nhiều.*càng tốt|luôn luôn tốt|chắc chắn tốt hơn", answer, re.I))
    negated = bool(re.search(r"không|chưa|không nhất thiết|không đồng nghĩa|không đảm bảo|không tự.{0,50}(càng dài|càng nhiều|luôn luôn tốt|chắc chắn tốt hơn|prompt dài)", answer, re.I))
    rejects = positive and not negated
    correction = bool(re.search(r"không nhất thiết|không đồng nghĩa|không phải|không đảm bảo|chưa chắc|không tự|không tốt hơn|không phải cứ", answer, re.I))
    concept = bool(re.search(r"prompt|task|format|role|context|rõ|specificity|ngắn|dài", answer, re.I))
    if correction and concept and not rejects:
        return {"status": "correct", "errorCode": None, "reason": "matches_expected_concept"}
    candidate = find_misconception(text)
    if candidate:
        return {"status": "incorrect", "errorCode": candidate, "reason": "mapped_misconception"}
    return {"status": "unknown", "errorCode": None, "reason": "unmapped_or_low_signal"}

OFFLINE_MESSAGES = {
    "M_PROMPT_LONGER_BETTER": {1: "Mở slide PDF p.7 và tìm nguyên tắc phân biệt specificity với cleverness. Phần nào của prompt giúp model biết đúng việc cần làm?", 2: "Đối chiếu PDF p.10: nếu thêm token không làm thay đổi hành vi mong muốn, điều gì có thể xảy ra với chi phí, latency hoặc nhiễu?"},
    "M_MORE_CONTEXT_ALWAYS_BETTER": {1: "Mở slide PDF p.20 và tìm câu trả lời cho việc nên chọn context theo lượng hay theo mức cần thiết.", 2: "Đối chiếu PDF p.8: Task và Format đứng ở đâu, còn Context nên được thêm trong điều kiện nào?"},
    "M_CLEVER_ROLE_ALWAYS_BETTER": {1: "Mở slide PDF p.7 và tìm nguyên tắc prompt rõ nghĩa thay vì prompt clever.", 2: "Đối chiếu PDF p.8: Role và Context không phải mặc định; hãy tìm điều kiện để thêm chúng có ích."},
}

def reviewed_hint(code: str, level: int) -> tuple[str, list[str]]:
    if level == 3 and code == "M_PROMPT_LONGER_BETTER":
        return ("Prompt dài hơn không tự làm prompt tốt hơn. Bắt đầu với Task + Format; chỉ thêm Role hoặc Context khi chúng thực sự cải thiện chất lượng hoặc tính nhất quán. Nếu phần thêm không làm thay đổi hành vi mong muốn, hãy cắt bớt vì token thừa có thể tăng chi phí, latency và nhiễu.", ["D04-P07", "D04-P08", "D04-P10"])
    if level == 3:
        return ({"M_MORE_CONTEXT_ALWAYS_BETTER": "Không phải cứ nhét thêm context là prompt tốt hơn. Bắt đầu với Task + Format và chỉ thêm Context khi nó thực sự cần thiết, cải thiện chất lượng hoặc tính nhất quán.", "M_CLEVER_ROLE_ALWAYS_BETTER": "Role hoặc persona không tự làm prompt tốt hơn. Hãy ưu tiên specificity và Task + Format, rồi chỉ thêm Role khi nó thực sự cải thiện chất lượng hoặc tính nhất quán."}[code], {"M_MORE_CONTEXT_ALWAYS_BETTER": ["D04-P08", "D04-P20"], "M_CLEVER_ROLE_ALWAYS_BETTER": ["D04-P07", "D04-P08"]}[code])
    return OFFLINE_MESSAGES.get(code, {}).get(level, "Hãy mở nguồn đã duyệt và viết lại điều bạn đang giả định."), ANSWER_KEY["allowed_sources"][code][:2]

def verify_coach_draft(raw: Any, candidates: list[str], expected_level: int, reveal_forbidden: bool) -> tuple[bool, str, CoachDraft | None]:
    try:
        draft = CoachDraft.model_validate(raw)
    except Exception:
        return False, "schema_invalid", None
    if draft.diagnosisCode is not None and draft.diagnosisCode not in candidates: return False, "diagnosis_not_candidate", None
    if draft.confidence == "low": return False, "low_confidence", None
    if draft.action == "diagnose_and_hint" and draft.diagnosisCode is None: return False, "diagnosis_missing", None
    if expected_level > 0 and draft.hintLevel != expected_level: return False, "hint_level_mismatch", None
    if expected_level == 0 and draft.hintLevel is not None: return False, "unexpected_hint", None
    if draft.diagnosisCode:
        allowed = ANSWER_KEY["allowed_sources"].get(draft.diagnosisCode, [])
        if not draft.citationIds or any(item not in allowed or source(item) is None for item in draft.citationIds): return False, "citation_not_supported", None
    if reveal_forbidden and expected_level < 3 and re.search(r"prompt dài hơn không|task \+ format.*bắt đầu|không tự làm prompt tốt hơn|đáp án đúng là", draft.learnerMessage, re.I): return False, "answer_reveal", None
    return True, "", draft

def evaluate_explain_back(text: str) -> dict[str, Any]:
    normalized = text.lower()
    checks = [("specificity_beats_cleverness", bool(re.search(r"rõ|specificity|cụ thể", normalized)) and bool(re.search(r"không|hơn|thay vì", normalized)) and bool(re.search(r"dài|clever|lan man", normalized))), ("task_and_format_first", bool(re.search(r"task|nhiệm vụ", normalized)) and bool(re.search(r"format|định dạng", normalized))), ("extra_prompt_can_add_cost_or_noise", bool(re.search(r"chi phí|latency|nhiễu|token thừa|cắt bớt", normalized)))]
    return {"pass": all(ok for _, ok in checks), "claims": [key for key, ok in checks if ok], "missingClaimIds": [key for key, ok in checks if not ok]}

def evaluate_transfer(answer: str, reasoning: str) -> bool:
    text = f"{answer} {reasoning}"
    return bool(re.search(r"task|nhiệm vụ", text, re.I) and re.search(r"format|định dạng|json", text, re.I) and re.search(r"không nhất thiết|không phải|không đảm bảo|không đồng nghĩa|không tự", text, re.I) and re.search(r"dài|role|context|prompt", text, re.I))
