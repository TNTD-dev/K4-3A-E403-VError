export const ITEM_ID = "prompt-clarity-01" as const;
export const ITEM_VERSION = "2026-09-16.2" as const;
export const SOURCE_VERSION = "day04-prompt-v1" as const;

export const answerKey = {
  expectedConcept: "specificity_over_length",
  requiredExplainClaimIds: [
    "specificity_beats_cleverness",
    "task_and_format_first",
    "extra_prompt_can_add_cost_or_noise"
  ],
  transferExpected: "clear_task_and_format",
  wrongChoiceToMisconception: {
    longer_is_better: "M_PROMPT_LONGER_BETTER",
    more_context_is_better: "M_MORE_CONTEXT_ALWAYS_BETTER",
    clever_role_is_better: "M_CLEVER_ROLE_ALWAYS_BETTER"
  },
  allowedSources: {
    M_PROMPT_LONGER_BETTER: ["D04-P07", "D04-P10"],
    M_MORE_CONTEXT_ALWAYS_BETTER: ["D04-P08", "D04-P20"],
    M_CLEVER_ROLE_ALWAYS_BETTER: ["D04-P07", "D04-P08"]
  },
  revealPolicy: {
    1: "hidden",
    2: "hidden",
    3: "reviewed_explanation_after_effort"
  }
} as const;

export type MisconceptionId = keyof typeof answerKey.allowedSources;
