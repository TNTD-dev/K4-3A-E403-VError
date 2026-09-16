import { describe, expect, it } from "vitest";
import { evaluateAttempt, evaluateExplainBack, evaluateTransfer, verifyCoachDraft } from "../src/evaluator.js";

describe("deterministic evaluator", () => {
  it("maps the token=word misconception without treating it as a generic wrong", () => {
    expect(evaluateAttempt("Có, 3 token vì có 3 từ.", "Mỗi từ là một token.", "Suy luận")).toMatchObject({ status: "incorrect", errorCode: "M_TOKEN_WORD_EQ" });
  });

  it("passes the corrected answer", () => {
    expect(evaluateAttempt("Không nhất thiết vì token không phải từ và có thể được tách khác.", "Tokenizer có thể khác theo ngôn ngữ.", "Suy luận").status).toBe("correct");
  });

  it("abstains for blank, no-basis and out-of-scope inputs", () => {
    expect(evaluateAttempt("", "", "Chưa có căn cứ").status).toBe("unknown");
    expect(evaluateAttempt("Giá API bao nhiêu?", "Mình muốn biết giá.", "Suy luận").status).toBe("out_of_scope");
  });

  it("requires evidence-bearing explain-back claims", () => {
    expect(evaluateExplainBack("Token là đơn vị tính, không phải từ hay chữ cái. Tokenizer khác nhau có thể chia khác nhau.")).toMatchObject({ pass: true });
    expect(evaluateExplainBack("Token là một từ.").pass).toBe(false);
  });

  it("checks transfer independently", () => {
    expect(evaluateTransfer("Không nhất thiết.", "Tokenizer hoặc model khác nhau có thể chia khác nhau.")).toBe(true);
    expect(evaluateTransfer("Có.", "Vì câu có cùng số từ.")).toBe(false);
  });

  it("rejects ungrounded coach output", () => {
    const result = verifyCoachDraft({
      action: "diagnose_and_hint",
      diagnosisCode: "M_TOKEN_WORD_EQ",
      confidence: "high",
      hintLevel: 1,
      citationIds: ["T04-050"],
      learnerMessage: "Hãy kiểm tra nguồn."
    }, ["M_TOKEN_WORD_EQ"], 1, true);
    expect(result).toMatchObject({ ok: false, reason: "citation_not_supported" });
  });
});
