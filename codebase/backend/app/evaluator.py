from __future__ import annotations
import re
from typing import Any
from .content import ANSWER_KEYS, CITATION_SUPPORT, approved_pages, source
from .schemas import CoachDraft, ReinforceDraft

LOW_SIGNAL = re.compile(r"asdf|abc|test|\?+|không biết gì", re.I)

# Fixed off-topic phrases we already knew about, plus concept-only markers
# (a specific provider name, an unrelated framework/domain) that generalize better than
# one exact sentence each. A pricing question only counts as out-of-scope when it names an
# actual provider/model — "chi phí" in the abstract can still be legitimate Day 04 content
# (token budget, latency) so it is deliberately not treated as a price marker on its own.
OUT_OF_SCOPE_PHRASES = re.compile(
    r"giá api|price of|attention matrix|tokenization detail|viết chương trình c\+\+|mã nguồn kernel|"
    r"langchain|computer vision|polygon|object detection",
    re.I,
)
PRICE_MARKERS = re.compile(r"giá|price", re.I)
PROVIDER_MARKERS = re.compile(r"gemini|gpt|claude|openai|anthropic", re.I)

# A learner citing a specific page ("trang 99 nói...") reads as grounded, but the claim is
# only as good as the page actually existing among this item's approved sources — see
# `_cites_unapproved_page`.
PAGE_MENTION = re.compile(r"trang\s+(\d+)", re.I)

# The learner's own words say the input is contradictory or that they genuinely don't know
# the criterion — ask, don't guess a diagnosis either way.
CONTRADICTION_MARKERS = re.compile(
    r"lỡ (bấm|chọn|click|nhấn)|bấm nhầm|chọn nhầm|nhấn nhầm|"
    r"chưa biết (tiêu chí|criterion)|có khi.*có khi (không|chưa)|"
    r"tùy (trường hợp|lúc|tình huống)|không chắc (tiêu chí|khi nào|lúc nào)",
    re.I,
)

# A conditional/qualifying clause turns an absolute-sounding claim ("dài hơn thì tốt hơn")
# into a defensible, correct one ("dài hơn có thể tốt hơn NẾU ... thực sự cần thiết"). Only
# used for item day04-s01-specificity, where the misconceptions are specifically about
# treating length/context/role as unconditionally better.
HEDGE_MARKERS = re.compile(
    r"nếu|chỉ khi|miễn là|với điều kiện|"
    r"không phải|không nhất thiết|không đồng nghĩa|không cần|không quan trọng|"
    r"không tự động|không coi|không tối đa",
    re.I,
)
# A misconception phrase quoted only to say "I used to believe that, not anymore" must not
# re-trigger the same diagnosis on the corrected retry.
RETRACTION_MARKERS = re.compile(
    r"trước đây|lần trước|hồi trước|từng nghĩ|đã từng (nghĩ|tin)|"
    r"giờ (mình )?(đã )?bỏ|không còn (nghĩ|tin)|đổi ý|thay đổi (suy nghĩ|giả định)|bỏ giả định (đó|này)",
    re.I,
)

# Generalized length/context/role check for day04-s01-specificity: a concept term plus an
# unconditional-superiority claim, used only when the exact SECTION_PATTERNS phrase list
# below doesn't already match a paraphrase (e.g. "viết dài thêm thì vẫn luôn tốt hơn").
_AXIS_TERMS = {
    "M_PROMPT_LONGER_BETTER": r"(dài|nhiều token|nhiều.{0,8}chữ|viết dài|thêm.*dài)",
    "M_MORE_CONTEXT_ALWAYS_BETTER": r"(context|bối cảnh)",
    "M_CLEVER_ROLE_ALWAYS_BETTER": r"(role|persona|vai trò)",
}
_UNCONDITIONAL_SUPERIORITY = re.compile(
    r"luôn|chắc chắn|càng.*càng tốt|tốt hơn|giúp (model|kết quả)|thông minh hơn|an toàn hơn",
    re.I,
)


def _text(answer: str, explanation: str) -> str:
    return f"{answer} {explanation}".strip()


def _has_negation(answer: str) -> bool:
    return bool(re.search(r"không|chưa|không nhất thiết|không đồng nghĩa|không đảm bảo|không phải|sai|không nên|đừng", answer, re.I))


def _find_code(patterns: list[tuple[str, str]], text: str) -> str | None:
    for code, pattern in patterns:
        if re.search(pattern, text, re.I):
            return code
    return None


def _axis_violation(item_id: str, text: str) -> str | None:
    if item_id != "day04-s01-specificity" or not _UNCONDITIONAL_SUPERIORITY.search(text):
        return None
    for code, term_pattern in _AXIS_TERMS.items():
        if re.search(term_pattern, text, re.I):
            return code
    return None


def _looks_out_of_scope(text: str) -> bool:
    if OUT_OF_SCOPE_PHRASES.search(text):
        return True
    return bool(PRICE_MARKERS.search(text) and PROVIDER_MARKERS.search(text))


def _cites_unapproved_page(text: str, item_id: str) -> bool:
    mentioned = {int(page) for page in PAGE_MENTION.findall(text)}
    if not mentioned:
        return False
    allowed = approved_pages(item_id)
    return not allowed or not mentioned.issubset(allowed)


SECTION_PATTERNS: dict[str, list[tuple[str, str]]] = {
    "day04-s01-specificity": [
        ("M_PROMPT_LONGER_BETTER", r"càng dài|prompt dài|dài hơn.*tốt|nhiều token.*tốt|prompt càng"),
        ("M_MORE_CONTEXT_ALWAYS_BETTER", r"nhiều context|càng nhiều.*context|nhét.*context|mọi context|thêm context.*tốt"),
        ("M_CLEVER_ROLE_ALWAYS_BETTER", r"role.*càng|persona.*càng|clever|thêm role.*tốt|role.*tốt hơn"),
    ],
    "day04-s02-technique-order": [
        ("M_ALWAYS_USE_COT", r"luôn.*cot|luôn.*chain.?of.?thought|think step by step.*mọi|cot.*mọi task|luôn bật cot"),
        ("M_ALWAYS_FEW_SHOT", r"luôn.*few.?shot|luôn.*5 ví dụ|few.?shot.*mọi|luôn dán.*ví dụ"),
    ],
    "day04-s03-system-policy": [
        ("M_LONG_SYSTEM_ALWAYS_BETTER", r"system prompt càng dài|càng dài.*ổn định|nhồi.*2000|prompt dài.*kiểm soát"),
        ("M_VAGUE_PERSONA_ENOUGH", r"hãy thông minh|hãy chuyên nghiệp|persona là đủ|chỉ cần persona"),
    ],
    "day04-s04-context-select": [
        ("M_DUMP_ALL_CONTEXT", r"dump.*history|nhét hết|toàn bộ chat|toàn bộ history|đưa hết.*context|càng nhiều history"),
        ("M_IGNORE_TOKEN_BUDGET", r"không cần.*budget|token budget.*không|cứ để history|không sao.*output buffer"),
    ],
    "day04-s05-tool-loop": [
        ("M_MODEL_RUNS_TOOLS", r"model tự chạy|tự gọi api|llm tự execute|model tự execute|tự chạy tool"),
        ("M_TOOL_CALL_IS_FINAL", r"tool_call.*trả lời luôn|emit.*xong|không cần.*app|không cần gửi.*lại"),
    ],
    "day04-s06-tool-granularity": [
        ("M_SUPER_TOOL_ALWAYS", r"handle_all|super.?tool|một tool ôm|gộp mọi|ôm hết|một tool.*mọi việc"),
        ("M_TINY_TOOLS_ALWAYS", r"càng nhỏ càng tốt|tách cực nhỏ|mỗi field một tool|get_customer_name.*get_customer_email"),
    ],
    "day04-s07-parallel-deps": [
        ("M_ALWAYS_PARALLEL", r"luôn parallel|cứ parallel|song song.*luôn|mọi tool song song|parallel.*luôn đúng"),
        ("M_SPEED_OVER_CONTROL", r"nhanh hơn.*luôn đúng|tốc độ hơn control|không cần.*phụ thuộc|bỏ qua.*dependency"),
    ],
    "day04-s08-lab-evidence": [
        ("M_RUN_ONCE_ENOUGH", r"chạy được một lần|chạy demo là đủ|script chạy.*đủ|lab xong khi chạy"),
        ("M_TESTS_OPTIONAL", r"test.*phụ|không cần test|bỏ test|test questions.*không cần|note lỗi.*không cần"),
    ],
}

CORRECT_PATTERNS: dict[str, list[str]] = {
    "day04-s01-specificity": [
        r"không nhất thiết|không đồng nghĩa|task\s*\+\s*format|specificity|rõ.*hơn.*dài|không phải cứ dài|"
        r"task.{0,15}format|format.{0,15}task"
    ],
    "day04-s02-technique-order": [r"zero-?shot.*trước|thử zero-?shot|không phải mặc định|cot.*overkill|thứ tự.*zero"],
    "day04-s03-system-policy": [r"policy|boundary|constraint|output (format|contract)|không mâu thuẫn|rules"],
    "day04-s04-context-select": [r"chọn.*context|không nhét hết|summarize|drop|archive|token budget|cần thiết"],
    "day04-s05-tool-loop": [r"app (nhận|chạy|execute)|gửi kết quả.*lại|tool result|không tự chạy|vòng lặp"],
    "day04-s06-tool-granularity": [r"single responsibility|một việc|granularity|lookup_order|hành động nghiệp vụ|không ôm hết"],
    "day04-s07-parallel-deps": [r"phụ thuộc|sequential|không parallel|độc lập.*parallel|control flow|merge"],
    "day04-s08-lab-evidence": [r"5 test|system prompt|2 tool|note lỗi|deliverable|phân loại lỗi|prompt/tool/control"],
}

EXPLAIN_CHECKS: dict[str, list[tuple[str, Any]]] = {
    "day04-s01-specificity": [
        ("specificity_beats_cleverness", lambda t: bool(re.search(r"rõ|specificity|cụ thể", t)) and bool(re.search(r"dài|clever|lan man", t))),
        ("task_and_format_first", lambda t: bool(re.search(r"task|nhiệm vụ", t)) and bool(re.search(r"format|định dạng", t))),
        ("extra_prompt_can_add_cost_or_noise", lambda t: bool(re.search(r"chi phí|latency|nhiễu|token|cắt bớt", t))),
    ],
    "day04-s02-technique-order": [
        ("try_simple_first", lambda t: bool(re.search(r"zero-?shot|đơn giản trước|thử trước", t))),
        ("cot_not_magic", lambda t: bool(re.search(r"cot|chain|reasoning|không phải phép|overkill", t))),
        ("advanced_is_conditional", lambda t: bool(re.search(r"khi|điều kiện|không mặc định|nếu", t))),
    ],
    "day04-s03-system-policy": [
        ("system_is_policy", lambda t: bool(re.search(r"policy|system prompt|policy layer", t))),
        ("clear_boundaries", lambda t: bool(re.search(r"boundary|constraint|giới hạn|rules", t))),
        ("avoid_vague_system", lambda t: bool(re.search(r"mơ hồ|mâu thuẫn|output|không nhồi|rõ", t))),
    ],
    "day04-s04-context-select": [
        ("context_should_be_selected", lambda t: bool(re.search(r"chọn|cần thiết|không nhét|select", t))),
        ("compress_or_drop", lambda t: bool(re.search(r"summarize|drop|archive|nén|bỏ", t))),
        ("token_budget_active", lambda t: bool(re.search(r"token|budget|output buffer|phân bổ", t))),
    ],
    "day04-s05-tool-loop": [
        ("app_executes_tool", lambda t: bool(re.search(r"app|ứng dụng|execute|chạy tool", t))),
        ("tool_loop", lambda t: bool(re.search(r"kết quả|result|quay lại|gửi lại|final", t))),
        ("schema_guides_choice", lambda t: bool(re.search(r"schema|description|mô tả|arguments", t))),
    ],
    "day04-s06-tool-granularity": [
        ("single_responsibility", lambda t: bool(re.search(r"single|một việc|trách nhiệm|boundary", t))),
        ("sensible_granularity", lambda t: bool(re.search(r"granularity|quá nhỏ|quá to|hợp lý|ôm", t))),
        ("test_tools_independently", lambda t: bool(re.search(r"test|unit|độc lập", t))),
    ],
    "day04-s07-parallel-deps": [
        ("parallel_needs_independence", lambda t: bool(re.search(r"độc lập|phụ thuộc|independent|dependency", t))),
        ("control_flow_first", lambda t: bool(re.search(r"control flow|thứ tự|khi nào|sequential|chaining", t))),
        ("merge_or_verify", lambda t: bool(re.search(r"merge|verify|tổng hợp|kiểm tra", t))),
    ],
    "day04-s08-lab-evidence": [
        ("lab_needs_tests", lambda t: bool(re.search(r"5 test|test question|câu test", t))),
        ("deliverable_bundle", lambda t: bool(re.search(r"system prompt|2 tool|agent|deliverable", t))),
        ("classify_failure_type", lambda t: bool(re.search(r"prompt|tool|control flow|phân loại|note lỗi", t))),
    ],
}

TRANSFER_PATTERNS: dict[str, list[str]] = {
    "day04-s01-specificity": [r"task|nhiệm vụ", r"format|định dạng|json", r"không nhất thiết|không phải|không đảm bảo|role|context"],
    "day04-s02-technique-order": [r"zero-?shot", r"format|extract|chuẩn hóa|e\.?164", r"few-?shot|cot|khi|nếu"],
    "day04-s03-system-policy": [r"rule|rules", r"constraint|never|không", r"json|output|format|contract"],
    "day04-s04-context-select": [r"chọn|3 file|relevant|cần", r"summarize|drop|archive|bỏ", r"không.*40|không dump|không nhét hết"],
    "day04-s05-tool-loop": [r"model|llm|tool_call", r"app|execute|chạy", r"result|kết quả|final"],
    "day04-s06-tool-granularity": [r"lookup|order|weather|refund|email|query", r"tool", r"không ôm|tách|hai|2"],
    "day04-s07-parallel-deps": [r"parallel|song song", r"độc lập|weather|tỷ giá|lịch", r"merge|verify|tổng hợp"],
    "day04-s08-lab-evidence": [r"trực tiếp|direct|không cần tool", r"gọi tool|tool", r"test"],
}

TRANSFER_CLAIM_IDS: dict[str, list[str]] = {
    "day04-s01-specificity": ["transfer_task", "transfer_format", "transfer_condition"],
    "day04-s02-technique-order": ["transfer_zero_shot", "transfer_format_task", "transfer_when_advanced"],
    "day04-s03-system-policy": ["transfer_rule", "transfer_constraint", "transfer_output_contract"],
    "day04-s04-context-select": ["transfer_select", "transfer_compress", "transfer_no_dump"],
    "day04-s05-tool-loop": ["transfer_model_decides", "transfer_app_runs", "transfer_result_back"],
    "day04-s06-tool-granularity": ["transfer_named_action", "transfer_tool", "transfer_split"],
    "day04-s07-parallel-deps": ["transfer_parallel", "transfer_independent", "transfer_merge"],
    "day04-s08-lab-evidence": ["transfer_direct", "transfer_tool_path", "transfer_tests"],
}

CLAIM_LABELS: dict[str, str] = {
    "specificity_beats_cleverness": "Prompt rõ/cụ thể thắng prompt dài hay khéo chữ",
    "task_and_format_first": "Bắt đầu từ Task và Format, không nhồi cho đủ thành phần",
    "extra_prompt_can_add_cost_or_noise": "Token/thành phần thừa tốn chi phí hoặc gây nhiễu",
    "try_simple_first": "Thử cách đơn giản / zero-shot trước",
    "cot_not_magic": "CoT không phải phép màu cho mọi task",
    "advanced_is_conditional": "Few-shot/CoT chỉ dùng khi có điều kiện",
    "system_is_policy": "System prompt là lớp policy, không phải đoạn văn cho dài",
    "clear_boundaries": "Cần rules / constraint / giới hạn rõ",
    "avoid_vague_system": "Tránh persona mơ hồ; output phải kiểm được",
    "context_should_be_selected": "Chỉ chọn context cần cho task",
    "compress_or_drop": "Nén, bỏ, hoặc archive phần không dùng",
    "token_budget_active": "Chủ động giữ chỗ token cho output",
    "app_executes_tool": "App mới chạy tool — model không tự execute",
    "tool_loop": "Gửi result về model rồi mới có câu trả lời cuối",
    "schema_guides_choice": "Schema / mô tả tool giúp model chọn đúng",
    "single_responsibility": "Một tool một việc, ranh giới rõ",
    "sensible_granularity": "Không quá to cũng không tách quá nhỏ",
    "test_tools_independently": "Tool phải test được độc lập",
    "parallel_needs_independence": "Chỉ song song khi không phụ thuộc dữ liệu",
    "control_flow_first": "Control flow (khi nào/thứ tự) quan trọng hơn tốc độ",
    "merge_or_verify": "Phải gộp hoặc kiểm tra kết quả sau khi gọi tool",
    "lab_needs_tests": "Lab cần bộ test, không chỉ chạy demo một lần",
    "deliverable_bundle": "Đủ system prompt, tool và agent",
    "classify_failure_type": "Phân loại lỗi prompt / tool / control flow",
    "transfer_task": "Chọn theo Task / nhiệm vụ cụ thể",
    "transfer_format": "Nêu Format / JSON (đầu ra cần ra sao)",
    "transfer_condition": "Nêu điều kiện: không phải lúc nào cũng thêm role/context",
    "transfer_zero_shot": "Bắt đầu zero-shot / cách đơn giản",
    "transfer_format_task": "Task format/extract thì không nhảy kỹ thuật nặng",
    "transfer_when_advanced": "Few-shot/CoT chỉ khi có lý do",
    "transfer_rule": "Có 1 rule / quy tắc",
    "transfer_constraint": "Có 1 constraint / điều không được làm",
    "transfer_output_contract": "Có output contract (JSON/format)",
    "transfer_select": "Chọn đúng file/context cần",
    "transfer_compress": "Summarize / drop / archive phần còn lại",
    "transfer_no_dump": "Không nhét hết repo/history",
    "transfer_model_decides": "Model chỉ quyết định tool_call",
    "transfer_app_runs": "App execute tool",
    "transfer_result_back": "Result quay lại model rồi mới final",
    "transfer_named_action": "Tên tool là hành động nghiệp vụ rõ",
    "transfer_tool": "Có tool, không gộp siêu tool",
    "transfer_split": "Tách thành hơn một việc khi ôm quá nhiều",
    "transfer_parallel": "Biết khi nào được gọi song song",
    "transfer_independent": "Song song chỉ khi độc lập dữ liệu",
    "transfer_merge": "Phải merge/verify sau parallel",
    "transfer_direct": "Có câu trả lời trực tiếp, không cần tool",
    "transfer_tool_path": "Có câu phải gọi tool",
    "transfer_tests": "Cần test để phân biệt hai nhánh đó",
}


def _transfer_checks(item_id: str) -> list[tuple[str, Any]]:
    ids = TRANSFER_CLAIM_IDS.get(item_id, TRANSFER_CLAIM_IDS["day04-s01-specificity"])
    patterns = TRANSFER_PATTERNS.get(item_id, TRANSFER_PATTERNS["day04-s01-specificity"])
    return [(claim_id, lambda t, p=pattern: bool(re.search(p, t, re.I))) for claim_id, pattern in zip(ids, patterns)]


def claim_ids_for(item_id: str, kind: str) -> list[str]:
    if kind == "transfer":
        return list(TRANSFER_CLAIM_IDS.get(item_id, TRANSFER_CLAIM_IDS["day04-s01-specificity"]))
    checks = EXPLAIN_CHECKS.get(item_id, EXPLAIN_CHECKS["day04-s01-specificity"])
    return [key for key, _ in checks]


def public_checklist(item_id: str, kind: str, present_ids: list[str] | None = None, missing_ids: list[str] | None = None) -> list[dict[str, Any]]:
    required = claim_ids_for(item_id, kind)
    present = set(present_ids or [])
    missing = set(missing_ids or [])
    rows = []
    for key in required:
        state = None
        if present_ids is not None or missing_ids is not None:
            state = key not in missing and (key in present or present_ids is None)
        rows.append({"label": CLAIM_LABELS.get(key, key), "present": state})
    return rows


def reinforce_message(kind: str, present_ids: list[str], missing_ids: list[str]) -> str:
    present_labels = [CLAIM_LABELS.get(key, key) for key in present_ids]
    missing_labels = [CLAIM_LABELS.get(key, key) for key in missing_ids]
    if not missing_ids:
        if kind == "explain":
            return "Đủ ý chính rồi. Bước tiếp theo: áp dụng vào một case ngắn — nói hướng xử lý và điều kiện, không chép lại lý thuyết."
        return "Case này bám đúng phần. Bạn đã chứng minh là hiểu, không chỉ trả lời đúng một lần."
    bits = []
    if present_labels:
        bits.append("Bạn đã chạm được: " + "; ".join(present_labels) + ".")
    bits.append("Còn thiếu: " + "; ".join(missing_labels) + ".")
    bits.append("Mở lại slide trọng tâm, viết thêm những ý còn thiếu bằng lời của bạn — không cần dùng đúng từng chữ trên slide.")
    return " ".join(bits)

OFFLINE_HINTS: dict[str, dict[int, tuple[str, list[str]]]] = {
    "M_PROMPT_LONGER_BETTER": {
        1: ("Mở PDF p.7: tìm nguyên tắc phân biệt specificity với cleverness. Phần nào giúp model biết đúng việc?", ["D04-P07", "D04-P10"]),
        2: ("Đối chiếu PDF p.10: nếu thêm token không đổi hành vi mong muốn, điều gì xảy ra với chi phí/latency/nhiễu?", ["D04-P10", "D04-P07"]),
        3: ("Prompt dài hơn không tự làm prompt tốt hơn. Bắt đầu Task + Format; chỉ thêm Role/Context khi cải thiện thật sự.", ["D04-P07", "D04-P08"]),
    },
    "M_MORE_CONTEXT_ALWAYS_BETTER": {
        1: ("Mở PDF p.8: Task và Format đứng đâu, Context thêm khi nào?", ["D04-P08", "D04-P10"]),
        2: ("PDF p.10 nhắc token thừa có thể tạo nhiễu. Context thừa có khác gì không?", ["D04-P10", "D04-P08"]),
        3: ("Không phải cứ nhét context là tốt hơn. Bắt đầu Task + Format; Context chỉ khi cần thiết.", ["D04-P08", "D04-P10"]),
    },
    "M_CLEVER_ROLE_ALWAYS_BETTER": {
        1: ("PDF p.7: specificity beats cleverness. Role ấn tượng có thay task rõ không?", ["D04-P07", "D04-P08"]),
        2: ("PDF p.8: Role không mặc định. Điều kiện nào Role mới có ích?", ["D04-P08", "D04-P07"]),
        3: ("Role/persona không tự làm prompt tốt hơn. Ưu tiên Task + Format trước.", ["D04-P07", "D04-P08"]),
    },
    "M_ALWAYS_USE_COT": {
        1: ("PDF p.11: thứ tự thử thực dụng bắt đầu từ đâu trước CoT?", ["D04-P11", "D04-P14"]),
        2: ("PDF p.14: task format/extraction đơn giản dùng CoT thì sao?", ["D04-P14", "D04-P11"]),
        3: ("CoT không phải phép màu. Thử zero-shot trước; CoT khi cần reasoning nhiều bước.", ["D04-P11", "D04-P14"]),
    },
    "M_ALWAYS_FEW_SHOT": {
        1: ("PDF p.11: few-shot nằm ở đâu trong thứ tự zero-shot → few-shot → CoT?", ["D04-P11", "D04-P14"]),
        2: ("Few-shot hữu ích khi format/consistency kém, không phải mặc định mọi task.", ["D04-P11", "D04-P14"]),
        3: ("Đừng nhảy few-shot ngay. Zero-shot trước; few-shot khi cần pattern/format ổn định.", ["D04-P11", "D04-P14"]),
    },
    "M_LONG_SYSTEM_ALWAYS_BETTER": {
        1: ("PDF p.17: anti-pattern nào liên quan system prompt quá dài?", ["D04-P17", "D04-P15"]),
        2: ("PDF p.15: system prompt production gồm những khối policy nào?", ["D04-P15", "D04-P17"]),
        3: ("System prompt là policy layer. Rõ rules/constraints/output contract quan trọng hơn nhồi 2000 token.", ["D04-P15", "D04-P17"]),
    },
    "M_VAGUE_PERSONA_ENOUGH": {
        1: ("PDF p.17: 'hãy thông minh/chuyên nghiệp' thuộc anti-pattern nào?", ["D04-P17", "D04-P15"]),
        2: ("PDF p.15: ngoài persona còn thiếu rules, constraints, output format.", ["D04-P15", "D04-P17"]),
        3: ("Persona mơ hồ không đủ. Cần boundary rõ và output contract có thể test.", ["D04-P15", "D04-P17"]),
    },
    "M_DUMP_ALL_CONTEXT": {
        1: ("PDF p.18: điều quan trọng là nhét bao nhiêu hay chọn đúng context?", ["D04-P18", "D04-P19"]),
        2: ("PDF p.19: memory injection và compression gợi ý làm gì với history cũ?", ["D04-P19", "D04-P18"]),
        3: ("Đừng dump toàn bộ history. Chỉ đưa facts cần cho task; summarize/drop/archive phần còn lại.", ["D04-P18", "D04-P19"]),
    },
    "M_IGNORE_TOKEN_BUDGET": {
        1: ("PDF p.20: nếu history/tools ăn hết chỗ, output buffer gặp rủi ro gì?", ["D04-P20", "D04-P19"]),
        2: ("Token budget cần phân bổ chủ động giữa system, history, tools, output.", ["D04-P20", "D04-P18"]),
        3: ("Chủ động cấp token cho output. History/tools không được nuốt hết budget.", ["D04-P20", "D04-P19"]),
    },
    "M_MODEL_RUNS_TOOLS": {
        1: ("PDF p.22: sau tool_call JSON, ai execute tool?", ["D04-P22", "D04-P23"]),
        2: ("Model chỉ quyết định gọi; app chạy tool rồi gửi result lại model.", ["D04-P22", "D04-P23"]),
        3: ("Model không tự chạy API. App nhận tool request, execute, trả result, model mới final.", ["D04-P22", "D04-P23"]),
    },
    "M_TOOL_CALL_IS_FINAL": {
        1: ("PDF p.22: tool_call có phải câu trả lời cuối cho user không?", ["D04-P22", "D04-P23"]),
        2: ("Thiếu nhịp gửi tool result lại model thì chưa có final response đúng.", ["D04-P22", "D04-P23"]),
        3: ("tool_call mới là request. Cần app execute + result + model final mới xong vòng.", ["D04-P22", "D04-P23"]),
    },
    "M_SUPER_TOOL_ALWAYS": {
        1: ("PDF p.27: Single Responsibility nói gì về một tool ôm mọi việc?", ["D04-P27", "D04-P28"]),
        2: ("PDF p.28: super-tool làm model khó hiểu boundary và khó debug.", ["D04-P28", "D04-P27"]),
        3: ("Thiết kế quanh một hành động nghiệp vụ rõ (lookup_order, get_weather), không handle_all.", ["D04-P27", "D04-P28"]),
    },
    "M_TINY_TOOLS_ALWAYS": {
        1: ("PDF p.28: tool quá nhỏ tạo overhead và flow rối thế nào?", ["D04-P28", "D04-P27"]),
        2: ("Granularity hợp lý: không quá nhỏ cũng không ôm quá nhiều.", ["D04-P27", "D04-P28"]),
        3: ("Gom theo hành động nghiệp vụ rõ, tránh tách từng field thành tool riêng.", ["D04-P28", "D04-P27"]),
    },
    "M_ALWAYS_PARALLEL": {
        1: ("PDF p.32: khi Tool B cần output Tool A thì parallel được không?", ["D04-P32", "D04-P33"]),
        2: ("Chỉ parallel khi không phụ thuộc dữ liệu; có dependency thì sequential/chaining.", ["D04-P32", "D04-P33"]),
        3: ("Parallel không luôn đúng. Phụ thuộc dữ liệu → sequential; độc lập mới song song + merge.", ["D04-P32", "D04-P33"]),
    },
    "M_SPEED_OVER_CONTROL": {
        1: ("PDF p.33: tool calling trước hết là bài toán control flow nào?", ["D04-P33", "D04-P32"]),
        2: ("Nhanh hơn không đủ nếu merge/verify và failure handling mù.", ["D04-P33", "D04-P32"]),
        3: ("Ưu tiên control flow rõ: khi nào gọi, thứ tự, merge/verify, xử lý fail.", ["D04-P33", "D04-P32"]),
    },
    "M_RUN_ONCE_ENOUGH": {
        1: ("PDF p.36: lab checklist còn bước nào sau khi script chạy?", ["D04-P36", "D04-P38"]),
        2: ("PDF p.38: deliverable bundle gồm những gì ngoài agent script?", ["D04-P38", "D04-P36"]),
        3: ("Chạy demo chưa đủ. Cần system prompt + 2 tools + 5 test + note lỗi prompt/tool/control flow.", ["D04-P36", "D04-P38"]),
    },
    "M_TESTS_OPTIONAL": {
        1: ("PDF p.36: 5 câu test chứng minh điều gì về agent?", ["D04-P36", "D04-P38"]),
        2: ("Test giúp biết khi nào trả lời trực tiếp, khi nào gọi tool, và lỗi thuộc lớp nào.", ["D04-P36", "D04-P38"]),
        3: ("Test và note lỗi là deliverable bắt buộc, không phải phần phụ.", ["D04-P38", "D04-P36"]),
    },
}


def find_misconception(item_id: str, text: str) -> str | None:
    code = _find_code(SECTION_PATTERNS.get(item_id, []), text)
    return code or _axis_violation(item_id, text)


def evaluate_attempt(
    answer: str,
    explanation: str,
    basis: str | None = None,
    item_id: str = "day04-s01-specificity",
    *,
    confidence: str | None = None,
) -> dict[str, Any]:
    text = _text(answer, explanation)
    if not answer.strip() or basis == "Chưa có căn cứ" or LOW_SIGNAL.fullmatch(answer.strip() or ""):
        return {"status": "unknown", "errorCode": None, "reason": "no_basis"}
    # A claim anchored to a specific page is only as good as that page actually existing
    # among this item's approved sources — a fabricated citation should read as unverifiable,
    # not as evidence of a real misconception.
    if _cites_unapproved_page(text, item_id):
        return {"status": "unknown", "errorCode": None, "reason": "unverifiable_source_page"}
    if _looks_out_of_scope(text):
        return {"status": "out_of_scope", "errorCode": None, "reason": "outside_day04_fixture"}
    if not explanation.strip():
        return {"status": "clarify", "errorCode": None, "reason": "reasoning_missing"}
    if CONTRADICTION_MARKERS.search(text):
        return {"status": "clarify", "errorCode": None, "reason": "contradictory_or_ambiguous_signal"}

    # Misconception check runs over the FULL text (answer + reasoning) and before the
    # "matches expected concept" check: a correct-sounding answer must not mask a
    # misconception stated in the reasoning, and vice versa. A hedge/conditional clause or
    # an explicit retraction of an old belief overrides a raw phrase match.
    candidate = find_misconception(item_id, text)
    hedged_or_retracted = item_id == "day04-s01-specificity" and bool(
        HEDGE_MARKERS.search(text) or RETRACTION_MARKERS.search(text)
    )
    if candidate and hedged_or_retracted:
        candidate = None
    if candidate:
        return {"status": "incorrect", "errorCode": candidate, "reason": "mapped_misconception"}

    correct_hit = any(re.search(pattern, text, re.I) for pattern in CORRECT_PATTERNS.get(item_id, []))
    if correct_hit or hedged_or_retracted:
        status = "low_confidence" if confidence == "Chưa chắc" else "correct"
        return {"status": status, "errorCode": None, "reason": "matches_expected_concept"}

    endorses_wrong = bool(re.search(r"đồng ý|đúng vậy|luôn luôn|chắc chắn tốt|càng .* càng tốt", text, re.I)) and not _has_negation(text)
    if endorses_wrong:
        # Fall back to the first misconception for the item when the learner clearly agrees with the bad claim.
        codes = list(ANSWER_KEYS[item_id]["misconceptions"])
        return {"status": "incorrect", "errorCode": codes[0], "reason": "mapped_misconception"}
    return {"status": "unknown", "errorCode": None, "reason": "unmapped_or_low_signal"}


def reviewed_hint(code: str, level: int) -> tuple[str, list[str]]:
    pack = OFFLINE_HINTS.get(code, {})
    if level in pack:
        return pack[level]
    allowed = CITATION_SUPPORT.get(code, [])[:2]
    return "Hãy mở đúng trang PDF đã duyệt và viết lại giả định của bạn.", allowed


def verify_coach_draft(raw: Any, candidates: list[str], expected_level: int, reveal_forbidden: bool, allowed_sources: dict[str, list[str]] | None = None) -> tuple[bool, str, CoachDraft | None]:
    allowed_sources = allowed_sources or CITATION_SUPPORT
    try:
        draft = CoachDraft.model_validate(raw)
    except Exception:
        return False, "schema_invalid", None
    if draft.diagnosisCode is not None and draft.diagnosisCode not in candidates:
        return False, "diagnosis_not_candidate", None
    if draft.confidence == "low":
        return False, "low_confidence", None
    if draft.action == "diagnose_and_hint" and draft.diagnosisCode is None:
        return False, "diagnosis_missing", None
    if expected_level > 0 and draft.hintLevel != expected_level:
        return False, "hint_level_mismatch", None
    if expected_level == 0 and draft.hintLevel is not None:
        return False, "unexpected_hint", None
    if draft.diagnosisCode:
        allowed = allowed_sources.get(draft.diagnosisCode, [])
        if not draft.citationIds or any(item not in allowed or source(item) is None for item in draft.citationIds):
            return False, "citation_not_supported", None
    if reveal_forbidden and expected_level < 3 and re.search(r"đáp án đúng là|answer key|không tự làm prompt tốt hơn\. Bắt đầu Task", draft.learnerMessage, re.I):
        return False, "answer_reveal", None
    return True, "", draft


def evaluate_explain_back(text: str, item_id: str = "day04-s01-specificity") -> dict[str, Any]:
    normalized = text.lower()
    checks = EXPLAIN_CHECKS.get(item_id, EXPLAIN_CHECKS["day04-s01-specificity"])
    results = [(key, bool(fn(normalized))) for key, fn in checks]
    return {
        "pass": all(ok for _, ok in results),
        "claims": [key for key, ok in results if ok],
        "missingClaimIds": [key for key, ok in results if not ok],
    }


def evaluate_transfer(answer: str, reasoning: str, item_id: str = "day04-s01-specificity") -> dict[str, Any]:
    text = f"{answer} {reasoning}".lower()
    results = [(key, bool(fn(text))) for key, fn in _transfer_checks(item_id)]
    return {
        "pass": all(ok for _, ok in results),
        "claims": [key for key, ok in results if ok],
        "missingClaimIds": [key for key, ok in results if not ok],
    }


def merge_claim_coverage(required: list[str], regex_present: list[str], model_present: list[str] | None) -> tuple[list[str], list[str]]:
    """Regex hits always count; a verified model may add paraphrases. Model cannot drop a regex hit."""
    allowed = set(required)
    present = set(regex_present) & allowed
    if model_present:
        present |= set(model_present) & allowed
    missing = [key for key in required if key not in present]
    return [key for key in required if key in present], missing


def verify_reinforce_draft(raw: Any, required: list[str], allowed_source_ids: list[str]) -> tuple[bool, str, ReinforceDraft | None]:
    try:
        draft = ReinforceDraft.model_validate(raw)
    except Exception:
        return False, "schema_invalid", None
    allowed = set(required)
    if any(item not in allowed for item in draft.presentClaimIds):
        return False, "unknown_present_claim", None
    if any(item not in allowed for item in draft.missingClaimIds):
        return False, "unknown_missing_claim", None
    allowed_sources = set(allowed_source_ids)
    if any(item not in allowed_sources for item in draft.citationIds):
        return False, "citation_not_supported", None
    return True, "", draft
