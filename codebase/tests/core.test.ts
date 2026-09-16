import { describe, expect, it } from "vitest";
import { evaluateAttempt, evaluateExplainBack, evaluateTransfer, verifyCoachDraft } from "../src/evaluator.js";

describe("deterministic evaluator", () => {
  it("maps the prompt-length misconception without treating it as a generic wrong", () => {
    expect(evaluateAttempt("Có, prompt càng dài và càng nhiều role thì càng tốt.", "Nhiều thông tin làm model thông minh hơn.", "Suy luận")).toMatchObject({ status: "incorrect", errorCode: "M_PROMPT_LONGER_BETTER" });
  });

  it("maps the context and role variants to their own reviewed misconceptions", () => {
    expect(evaluateAttempt("Cứ thêm context thì output tốt hơn.", "Context càng nhiều càng hữu ích.", "Suy luận")).toMatchObject({ status: "incorrect", errorCode: "M_MORE_CONTEXT_ALWAYS_BETTER" });
    expect(evaluateAttempt("Thêm role thật ấn tượng thì tốt hơn.", "Persona làm model thông minh hơn.", "Suy luận")).toMatchObject({ status: "incorrect", errorCode: "M_CLEVER_ROLE_ALWAYS_BETTER" });
  });

  it("passes the corrected answer", () => {
    expect(evaluateAttempt("Không nhất thiết, prompt rõ Task + Format có thể tốt hơn prompt dài.", "Role hoặc Context chỉ thêm khi chúng thực sự cải thiện kết quả.", "Suy luận").status).toBe("correct");
  });

  it("abstains for blank, no-basis and out-of-scope inputs", () => {
    expect(evaluateAttempt("", "", "Chưa có căn cứ").status).toBe("unknown");
    expect(evaluateAttempt("Giá API bao nhiêu?", "Mình muốn biết chi phí cụ thể.", "Suy luận").status).toBe("out_of_scope");
  });

  it("requires evidence-bearing explain-back claims", () => {
    expect(evaluateExplainBack("Prompt rõ nghĩa thay vì prompt dài lan man. Bắt đầu với Task + Format. Token thừa có thể tăng chi phí và nhiễu.")).toMatchObject({ pass: true });
    expect(evaluateExplainBack("Prompt càng dài càng tốt.").pass).toBe(false);
  });

  it("checks transfer independently", () => {
    expect(evaluateTransfer("Không nhất thiết, chọn prompt rõ Task và Format thay vì prompt dài.", "Chỉ thêm Context khi cần thiết và có ích cho task.")).toBe(true);
    expect(evaluateTransfer("Có.", "Vì prompt càng dài và nhiều role thì luôn tốt hơn.")).toBe(false);
  });

  it("rejects ungrounded coach output", () => {
    const result = verifyCoachDraft({
      action: "diagnose_and_hint",
      diagnosisCode: "M_PROMPT_LONGER_BETTER",
      confidence: "high",
      hintLevel: 1,
      citationIds: ["D04-P20"],
      learnerMessage: "Hãy kiểm tra nguồn."
    }, ["M_PROMPT_LONGER_BETTER"], 1, true);
    expect(result).toMatchObject({ ok: false, reason: "citation_not_supported" });
  });
});
