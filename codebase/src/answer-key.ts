export const ITEM_ID = "tokenization-01" as const;
export const ITEM_VERSION = "2026-09-16.1" as const;
export const SOURCE_VERSION = "transcript-04-v1" as const;

export const answerKey = {
  expectedConcept: "not_necessarily",
  requiredExplainClaimIds: [
    "token_is_not_word_or_letter",
    "tokenizer_can_split_differently",
    "exact_count_needs_tool"
  ],
  transferExpected: "not_necessarily",
  wrongChoiceToMisconception: {
    always_one_word: "M_TOKEN_WORD_EQ",
    english_only: "M_ENGLISH_ONLY",
    fixed_count: "M_FIXED_COUNT",
    context_as_meaning: "M_CONTEXT_AS_MEANING"
  },
  allowedSources: {
    M_TOKEN_WORD_EQ: ["T04-049"],
    M_ENGLISH_ONLY: ["T04-049", "T04-050"],
    M_FIXED_COUNT: ["T04-049", "T04-050"],
    M_CONTEXT_AS_MEANING: ["T04-051"]
  },
  revealPolicy: {
    1: "hidden",
    2: "hidden",
    3: "reviewed_explanation_after_effort"
  }
} as const;

export type MisconceptionId = keyof typeof answerKey.allowedSources;
