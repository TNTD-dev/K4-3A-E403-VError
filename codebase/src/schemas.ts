import { z } from "zod";

export const SessionState = z.enum([
  "attempt_1_open",
  "evaluating_attempt",
  "diagnosis",
  "retry",
  "explain_back",
  "transfer_check",
  "source_review",
  "clarify",
  "out_of_scope",
  "completed"
]);
export type SessionState = z.infer<typeof SessionState>;

export const Confidence = z.enum(["Chắc", "Khá chắc", "Chưa chắc"]);
export const Basis = z.enum(["Đã học trước đó", "Suy luận", "Đoán", "Chưa có căn cứ"]);

export const CreateSessionBody = z.object({
  itemId: z.literal("tokenization-01"),
  itemVersion: z.literal("2026-09-16.1").optional(),
  mode: z.literal("demo").optional()
}).strict();
export type CreateSessionBody = z.infer<typeof CreateSessionBody>;

export const AttemptBody = z.object({
  stateVersion: z.number().int().positive(),
  kind: z.enum(["attempt_1", "retry"]),
  answer: z.object({
    text: z.string().max(500),
    explanation: z.string().max(500)
  }).strict(),
  confidence: Confidence.optional(),
  basis: Basis.optional()
}).strict();
export type AttemptBody = z.infer<typeof AttemptBody>;

export const HintBody = z.object({
  stateVersion: z.number().int().positive(),
  level: z.union([z.literal(1), z.literal(2), z.literal(3)])
}).strict();
export type HintBody = z.infer<typeof HintBody>;

export const ExplainBody = z.object({
  stateVersion: z.number().int().positive(),
  text: z.string().min(1).max(500)
}).strict();
export type ExplainBody = z.infer<typeof ExplainBody>;

export const TransferBody = z.object({
  stateVersion: z.number().int().positive(),
  answer: z.string().max(500),
  reasoning: z.string().max(500)
}).strict();
export type TransferBody = z.infer<typeof TransferBody>;

export const StateVersionBody = z.object({
  stateVersion: z.number().int().positive()
}).strict();

export const CoachDraft = z.object({
  action: z.enum(["diagnose_and_hint", "ask_clarification", "abstain"]),
  diagnosisCode: z.string().nullable(),
  confidence: z.enum(["high", "medium", "low"]),
  hintLevel: z.union([z.literal(1), z.literal(2), z.literal(3)]).nullable(),
  citationIds: z.array(z.string()).max(2),
  learnerMessage: z.string().min(1).max(500)
}).strict();
export type CoachDraft = z.infer<typeof CoachDraft>;

export const ExplainClaims = z.object({
  tokenIsNotWordOrLetter: z.boolean(),
  tokenizerCanSplitDifferently: z.boolean(),
  exactCountNeedsTool: z.boolean()
});
