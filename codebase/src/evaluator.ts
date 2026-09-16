import { answerKey, type MisconceptionId } from "./answer-key.js";
import { citationSupport, getSource } from "./content.js";
import { CoachDraft, type CoachDraft as CoachDraftType, type SessionState } from "./schemas.js";

export type ObjectiveResult = {
  status: "correct" | "incorrect" | "unknown" | "out_of_scope" | "clarify";
  errorCode: MisconceptionId | null;
  reason: string;
};

export function evaluateAttempt(answer: string, explanation: string, basis?: string): ObjectiveResult {
  const text = `${answer} ${explanation}`.trim();
  if (!answer.trim() || basis === "Chưa có căn cứ" || /^(asdf|abc|test|\?+|không biết gì)$/i.test(answer.trim())) {
    return { status: "unknown", errorCode: null, reason: "no_basis" };
  }
  if (/(giá|price|api|attention|code|mã tokenizer|viết chương trình|chi phí cụ thể)/i.test(text)) {
    return { status: "out_of_scope", errorCode: null, reason: "outside_tokenization_fixture" };
  }
  if (!explanation.trim()) return { status: "clarify", errorCode: null, reason: "reasoning_missing" };

  const normalized = answer.toLowerCase();
  const correct = /(không nhất thiết|không thể|không phải|không đồng ý)/i.test(normalized)
    && /(token|từ|chữ cái)/i.test(normalized)
    && !/(chắc chắn\s+(là|có)|mỗi từ\s*(=|là|tương ứng)|luôn luôn|tách theo từ)/i.test(normalized);
  if (correct) return { status: "correct", errorCode: null, reason: "matches_expected_concept" };

  const candidate = findMisconception(text);
  if (candidate) return { status: "incorrect", errorCode: candidate, reason: "mapped_misconception" };
  return { status: "unknown", errorCode: null, reason: "unmapped_or_low_signal" };
}

export function findMisconception(text: string): MisconceptionId | null {
  if (/(3\s*token|mỗi từ|một từ.*token|token.*từ|tách theo từ|số từ.*số token|luôn.*token)/i.test(text)) return "M_TOKEN_WORD_EQ";
  if (/(chỉ đúng với tiếng anh|english only|chỉ tiếng anh)/i.test(text)) return "M_ENGLISH_ONLY";
  if (/(công thức cố định|luôn là \d+|chắc chắn \d+ token|bằng \d+ token)/i.test(text)) return "M_FIXED_COUNT";
  if (/(context.*token|token.*context|context là một)/i.test(text)) return "M_CONTEXT_AS_MEANING";
  return null;
}

const offlineMessages: Record<string, Record<number, string>> = {
  M_TOKEN_WORD_EQ: {
    0: "Mình thấy bài làm của bạn đang dùng giả định: một từ luôn tương ứng với một token.",
    1: "Đừng đếm số từ vội. Hãy kiểm tra trong nguồn xem token được phân biệt với từ và chữ cái như thế nào.",
    2: "Hãy tìm một phản ví dụ trong nguồn: cách chia token có thể thay đổi theo ngôn ngữ hoặc model. Nếu chỉ biết số từ, bạn đã đủ thông tin để biết chính xác số token chưa?"
  },
  M_ENGLISH_ONLY: {
    0: "Bài làm đang giả định tokenization chỉ đúng với tiếng Anh.",
    1: "Hãy đối chiếu phần nguồn nói về cách chia token giữa các ngôn ngữ.",
    2: "Tách hai ý: token là đơn vị tính, còn cách chia có thể thay đổi theo ngôn ngữ hoặc model."
  },
  M_FIXED_COUNT: {
    0: "Bài làm đang dùng một quy đổi cố định như thể nó cho số token chính xác.",
    1: "Hãy xem nguồn phân biệt ước tính nhanh với việc đếm chính xác bằng tool.",
    2: "Nếu tokenizer hoặc phiên bản model thay đổi, một quy đổi cố định còn là answer key chắc chắn không?"
  },
  M_CONTEXT_AS_MEANING: {
    0: "Bài làm đang trộn khái niệm context với đơn vị token.",
    1: "Mở [T04-051] và tìm định nghĩa của context trong một lần model tiêu thụ thông tin.",
    2: "Hãy phân biệt đơn vị token với toàn bộ thông tin model có thể nhận trong một lần."
  }
};

export function reviewedHint(code: MisconceptionId, level: 1 | 2 | 3): { text: string; citationIds: string[] } {
  if (level === 3 && code === "M_TOKEN_WORD_EQ") {
    return {
      text: "Token là một đơn vị tính của mô hình, không phải từ hoặc chữ cái. Một từ có thể bị tách thành các token, nên không thể suy ra chính xác số token chỉ từ số từ. Muốn biết chính xác, hãy dùng công cụ tokenizer phù hợp.",
      citationIds: ["T04-049", "T04-050"]
    };
  }
  const text = offlineMessages[code]?.[level] ?? "Hãy mở nguồn đã duyệt và viết lại điều bạn đang giả định.";
  return { text, citationIds: citationSupport[code].slice(0, 2) };
}

export function verifyCoachDraft(draft: unknown, candidate: MisconceptionId[], expectedLevel: 0 | 1 | 2, revealForbidden: boolean): { ok: true; draft: CoachDraftType } | { ok: false; reason: string } {
  const parsed = CoachDraft.safeParse(draft);
  if (!parsed.success) return { ok: false, reason: "schema_invalid" };
  const value = parsed.data;
  if (value.diagnosisCode !== null && !candidate.includes(value.diagnosisCode as MisconceptionId)) return { ok: false, reason: "diagnosis_not_candidate" };
  if (value.confidence === "low") return { ok: false, reason: "low_confidence" };
  if (value.action === "diagnose_and_hint" && value.diagnosisCode === null) return { ok: false, reason: "diagnosis_missing" };
  if (expectedLevel > 0 && value.hintLevel !== expectedLevel) return { ok: false, reason: "hint_level_mismatch" };
  if (expectedLevel === 0 && value.hintLevel !== null) return { ok: false, reason: "unexpected_hint" };
  if (value.diagnosisCode) {
    const allowed = citationSupport[value.diagnosisCode as MisconceptionId] ?? [];
    if (!value.citationIds.every((id) => allowed.includes(id) && Boolean(getSource(id)))) return { ok: false, reason: "citation_not_supported" };
    if (!value.citationIds.length) return { ok: false, reason: "citation_missing" };
  }
  if (revealForbidden && expectedLevel < 3 && /(không nhất thiết|không thể suy ra|không phải từ|đáp án đúng là)/i.test(value.learnerMessage)) return { ok: false, reason: "answer_reveal" };
  return { ok: true, draft: value };
}

export function evaluateExplainBack(text: string): { pass: boolean; claims: string[]; missingClaimIds: string[] } {
  const normalized = text.toLowerCase();
  const checks: Array<[string, boolean]> = [
    ["token_is_not_word_or_letter", /(đơn vị tính|đơn vị)/i.test(normalized) && /(không phải|khác|không đồng nhất)/i.test(normalized) && /(từ|chữ cái)/i.test(normalized)],
    ["tokenizer_can_split_differently", /(thay đổi|khác|không giống|phụ thuộc)/i.test(normalized) && /(ngôn ngữ|model|mô hình|tokenizer|phiên bản)/i.test(normalized)],
    ["exact_count_needs_tool", /(chính xác|đếm|số token)/i.test(normalized) && /(tool|công cụ|tokenizer)/i.test(normalized)]
  ];
  const claims = checks.filter(([, present]) => present).map(([claim]) => claim);
  const missingClaimIds = checks.filter(([, present]) => !present).map(([claim]) => claim);
  return { pass: checks[0]?.[1] === true && claims.length >= 2, claims, missingClaimIds };
}

export function evaluateTransfer(answer: string, reasoning: string): boolean {
  const normalized = `${answer} ${reasoning}`;
  return /(không nhất thiết|không thể|không đồng ý|không cùng)/i.test(normalized)
    && /(tokenizer|model|mô hình|ngôn ngữ|phiên bản)/i.test(normalized);
}

export function validTransition(from: SessionState, to: SessionState): boolean {
  const transitions: Record<SessionState, SessionState[]> = {
    attempt_1_open: ["evaluating_attempt", "diagnosis", "retry", "source_review", "clarify", "out_of_scope", "explain_back"],
    evaluating_attempt: ["diagnosis", "retry", "explain_back", "source_review", "clarify", "out_of_scope"],
    diagnosis: ["retry", "source_review", "evaluating_attempt", "explain_back"],
    retry: ["evaluating_attempt", "retry", "source_review", "diagnosis", "explain_back"],
    explain_back: ["transfer_check", "explain_back"],
    transfer_check: ["completed", "transfer_check"],
    source_review: ["attempt_1_open", "retry"],
    clarify: ["attempt_1_open", "retry", "source_review"],
    out_of_scope: ["attempt_1_open", "retry", "source_review"],
    completed: []
  };
  return transitions[from].includes(to);
}
