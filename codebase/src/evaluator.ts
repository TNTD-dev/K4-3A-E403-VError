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
  if (/(giá|price|attention|tokenization|viết chương trình|mã nguồn|chi phí cụ thể)/i.test(text)) {
    return { status: "out_of_scope", errorCode: null, reason: "outside_prompt_fixture" };
  }
  if (!explanation.trim()) return { status: "clarify", errorCode: null, reason: "reasoning_missing" };

  const normalized = answer.toLowerCase();
  const positiveAbsolute = /(càng dài.*càng tốt|càng nhiều.*càng tốt|luôn luôn tốt|chắc chắn tốt hơn)/i.test(normalized);
  const negatedAbsolute = /(không|chưa|không nhất thiết|không đồng nghĩa|không đảm bảo|không tự).{0,50}(càng dài|càng nhiều|luôn luôn tốt|chắc chắn tốt hơn|prompt dài)/i.test(normalized);
  const rejectsAbsolute = positiveAbsolute && !negatedAbsolute;
  const hasCorrection = /(không nhất thiết|không đồng nghĩa|không phải|không đảm bảo|chưa chắc|không tự|không tốt hơn|không phải cứ)/i.test(normalized);
  const hasPromptConcept = /(prompt|task|format|role|context|rõ|specificity|ngắn|dài)/i.test(normalized);
  if (hasCorrection && hasPromptConcept && !rejectsAbsolute) return { status: "correct", errorCode: null, reason: "matches_expected_concept" };

  const candidate = findMisconception(text);
  if (candidate) return { status: "incorrect", errorCode: candidate, reason: "mapped_misconception" };
  return { status: "unknown", errorCode: null, reason: "unmapped_or_low_signal" };
}

export function findMisconception(text: string): MisconceptionId | null {
  if (/(càng dài|prompt dài|dài hơn.*tốt|nhiều token.*tốt|prompt càng)/i.test(text)) return "M_PROMPT_LONGER_BETTER";
  if (/(nhiều context|càng nhiều.*context|nhét.*context|mọi context|context.*càng|thêm context.*tốt|context.*tốt hơn)/i.test(text)) return "M_MORE_CONTEXT_ALWAYS_BETTER";
  if (/(role.*càng|persona.*càng|clever|thông minh hơn.*role|thêm role.*tốt hơn)/i.test(text)) return "M_CLEVER_ROLE_ALWAYS_BETTER";
  return null;
}

const offlineMessages: Record<string, Record<number, string>> = {
  M_PROMPT_LONGER_BETTER: {
    0: "Mình thấy bài làm đang dùng giả định: prompt càng dài thì càng tốt.",
    1: "Mở slide PDF p.7 và tìm nguyên tắc phân biệt specificity với cleverness. Phần nào của prompt giúp model biết đúng việc cần làm?",
    2: "Đối chiếu PDF p.10: nếu thêm token không làm thay đổi hành vi mong muốn, điều gì có thể xảy ra với chi phí, latency hoặc nhiễu?"
  },
  M_MORE_CONTEXT_ALWAYS_BETTER: {
    0: "Bài làm đang giả định cứ thêm context là output sẽ tốt hơn.",
    1: "Mở slide PDF p.20 và tìm câu trả lời cho việc nên chọn context theo lượng hay theo mức cần thiết.",
    2: "Đối chiếu PDF p.8: Task và Format đứng ở đâu, còn Context nên được thêm trong điều kiện nào?",
    3: "Không phải cứ nhét thêm context là prompt tốt hơn. Bắt đầu với Task + Format và chỉ thêm Context khi nó thực sự cần thiết, cải thiện chất lượng hoặc tính nhất quán."
  },
  M_CLEVER_ROLE_ALWAYS_BETTER: {
    0: "Bài làm đang giả định thêm một role thật ấn tượng luôn làm prompt tốt hơn.",
    1: "Mở slide PDF p.7 và tìm nguyên tắc prompt rõ nghĩa thay vì prompt clever.",
    2: "Đối chiếu PDF p.8: Role và Context không phải mặc định; hãy tìm điều kiện để thêm chúng có ích.",
    3: "Role hoặc persona không tự làm prompt tốt hơn. Hãy ưu tiên specificity và Task + Format, rồi chỉ thêm Role khi nó thực sự cải thiện chất lượng hoặc tính nhất quán."
  }
};

export function reviewedHint(code: MisconceptionId, level: 1 | 2 | 3): { text: string; citationIds: string[] } {
  if (level === 3 && code === "M_PROMPT_LONGER_BETTER") {
    return {
      text: "Prompt dài hơn không tự làm prompt tốt hơn. Bắt đầu với Task + Format; chỉ thêm Role hoặc Context khi chúng thực sự cải thiện chất lượng hoặc tính nhất quán. Nếu phần thêm không làm thay đổi hành vi mong muốn, hãy cắt bớt vì token thừa có thể tăng chi phí, latency và nhiễu.",
      citationIds: ["D04-P07", "D04-P08", "D04-P10"]
    };
  }
  if (level === 3 && code === "M_MORE_CONTEXT_ALWAYS_BETTER") {
    return { text: offlineMessages[code]?.[3] ?? "Hãy mở nguồn đã duyệt và viết lại điều bạn đang giả định.", citationIds: ["D04-P08", "D04-P20"] };
  }
  if (level === 3 && code === "M_CLEVER_ROLE_ALWAYS_BETTER") {
    return { text: offlineMessages[code]?.[3] ?? "Hãy mở nguồn đã duyệt và viết lại điều bạn đang giả định.", citationIds: ["D04-P07", "D04-P08"] };
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
  if (revealForbidden && expectedLevel < 3 && /(prompt dài hơn không|task \+ format.*bắt đầu|không tự làm prompt tốt hơn|đáp án đúng là)/i.test(value.learnerMessage)) return { ok: false, reason: "answer_reveal" };
  return { ok: true, draft: value };
}

export function evaluateExplainBack(text: string): { pass: boolean; claims: string[]; missingClaimIds: string[] } {
  const normalized = text.toLowerCase();
  const checks: Array<[string, boolean]> = [
    ["specificity_beats_cleverness", /(rõ|specificity|cụ thể)/i.test(normalized) && /(không|hơn|thay vì)/i.test(normalized) && /(dài|clever|lan man)/i.test(normalized)],
    ["task_and_format_first", /(task|nhiệm vụ)/i.test(normalized) && /(format|định dạng)/i.test(normalized)],
    ["extra_prompt_can_add_cost_or_noise", /(chi phí|latency|nhiễu|token thừa|cắt bớt)/i.test(normalized)]
  ];
  const claims = checks.filter(([, present]) => present).map(([claim]) => claim);
  const missingClaimIds = checks.filter(([, present]) => !present).map(([claim]) => claim);
  return { pass: checks.every(([, present]) => present), claims, missingClaimIds };
}

export function evaluateTransfer(answer: string, reasoning: string): boolean {
  const normalized = `${answer} ${reasoning}`;
  const choosesClearPrompt = /(task|nhiệm vụ)/i.test(normalized) && /(format|định dạng|json)/i.test(normalized);
  const rejectsLength = /(không nhất thiết|không phải|không đảm bảo|không đồng nghĩa|không tự)/i.test(normalized) && /(dài|role|context|prompt)/i.test(normalized);
  return choosesClearPrompt && rejectsLength;
}

export function validTransition(from: SessionState, to: SessionState): boolean {
  const transitions: Record<SessionState, SessionState[]> = {
    attempt_1_open: ["evaluating_attempt", "diagnosis", "retry", "source_review", "clarify", "out_of_scope", "explain_back"],
    evaluating_attempt: ["diagnosis", "retry", "explain_back", "source_review", "clarify", "out_of_scope"],
    diagnosis: ["retry", "source_review", "evaluating_attempt", "explain_back"],
    retry: ["evaluating_attempt", "retry", "source_review", "diagnosis", "explain_back"],
    explain_back: ["transfer_check", "explain_back"],
    transfer_check: ["completed", "transfer_check"],
    source_review: ["attempt_1_open", "retry", "source_review"],
    clarify: ["attempt_1_open", "retry", "source_review"],
    out_of_scope: ["attempt_1_open", "retry", "source_review"],
    completed: []
  };
  return transitions[from].includes(to);
}
