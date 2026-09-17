# Error analysis log

Không xoá failure. Sau mỗi full run, chọn **một failure đau nhất** để sửa rồi chạy lại toàn bộ.

| Run | Case | Failure type | Trigger | Actual behavior | Why harmful | Root-cause hypothesis | Change made | Regression risk | Next full run |
|---|---|---|---|---|---|---|---|---|---|
| run_01 (`154132`, 12/30) | N01, N02, H-DM-02, H-DM-03, E02 | `false_positive_misconception`-adjacent / missed correct | Correct answer phrased differently than the fixed regex list | Routed to `no-basis` instead of `correct` | Learner told "not enough basis" despite a correct answer — erodes trust | `CORRECT_PATTERNS` only scanned `answer`, ignored `explanation`; phrase list too narrow | Widened `CORRECT_PATTERNS` for day04-s01 (`task.{0,15}format`), evaluator now scans full `answer+explanation` text | Low — new phrases verified against all 30 cases before/after, no diagnose case regressed | run_08 (`161111`) |
| run_01 | N06 | `missed_misconception` | Paraphrase of the length myth without the exact trigger phrase | Routed to `no-basis` instead of `diagnose` | Real misconception never surfaced to the learner | `SECTION_PATTERNS` exact-phrase only | Added `_axis_violation`: generic "length/context/role term + unconditional-superiority claim" fallback, used only when the exact patterns miss | Low — fallback only fires without an existing exact match | run_08 |
| run_01 | N07, N09 | `hallucinated_citation`-adjacent | Any `correct` verdict | A "further reading" anchor citation was attached even though nothing needed correcting | Golden set (rightly) treats any citation on a correct answer as fabricated evidence | Orchestrator always attached `citations(anchor)` on the `correct` branch | Removed the anchor; `correct`/`low_confidence` responses now always return `citations: []` | None — no consumer of this field on the correct path | run_08 |
| run_01 | N08 | `wrong_next_action` (no matching route) | Correct content + `confidence="guess"` | Routed to `no-basis`; no "low-confidence" concept existed at all | Learner's own uncertainty signal was discarded | State machine had no distinct low-confidence outcome | Added `low_confidence` objective status (same `explain_back` transition as `correct`, distinct `evaluation.status`) | Low — additive status, existing `correct` path untouched | run_08 |
| run_01 | H-ST-03 | `hallucinated_citation` (inverse: trusted a fake one) | "Trang 99 nói..." — a page that doesn't exist in this item's approved sources | Diagnosed as if the misconception were real | No check that a claimed page number is actually approved | Added `_cites_unapproved_page()` using new `content.approved_pages()`; short-circuits to `no-basis` before misconception matching | Low — only fires when a "trang N" mention exists and N isn't approved | run_08 |
| run_01 | H-AM-03, R02 | `failed_to_clarify` | Learner explicitly signals a mis-click or "I don't know the criterion" | Diagnosed the literal (contradicted) wording instead of asking | No detection of self-declared contradiction/ambiguity | Added `CONTRADICTION_MARKERS`, checked before misconception matching, routes to `clarify` | Low — narrow marker list, verified no false hits across all 30 cases | run_08 |
| run_01 | H-OS-01/02/03 | `scope_violation` | Off-topic question (other provider's pricing, unrelated framework code, unrelated domain) | Routed to `no-basis` instead of `out-of-scope` | Wrong next_action sent the learner to re-read slides instead of back to the task | `OUT_OF_SCOPE` regex was a short fixed-phrase list | Added concept markers (`langchain`, `computer vision`, `polygon`, ...) plus a price+provider-name combination check | Low — provider names never appear in legitimate Day04 answers | run_08 |
| run_01 | H-DM-01 | `wrong_primary_misconception` | Absolute-looking substring inside an explicitly conditional sentence ("...nếu ... thực sự cần thiết") | Diagnosed a misconception the learner didn't actually hold | No hedge/conditional-clause awareness | Added `HEDGE_MARKERS` (nếu/chỉ khi/không cần/...); suppresses a raw phrase match when present | Medium — broad enough hedge list could theoretically mask a real misconception; mitigated by keeping it scoped to day04-s01-specificity only and verifying against all diagnose-expected cases | run_08 |
| run_01 | R01 | `missed_misconception` (masked by a correct-looking answer) | `answer` quotes the correct concept, `explanation` reveals the real (wrong) belief | Returned `correct`, missing the real misconception entirely | `correct_hit` was checked (and returned early) on `answer` alone, before reasoning was ever read | Reordered pipeline: misconception check over full text now runs **before** the correct-concept check | Low — verified R03 (a similar adversarial case) still resolves correctly | run_08 |
| run_01 | E01 | `stale_state` | Retry explanation quotes the old (now-retracted) belief for context | Stale misconception + stale citation (`D04-P10`) leaked into the "corrected" response | No distinction between "I believe X" and "I used to believe X, not anymore" | Added `RETRACTION_MARKERS` (trước đây/lần trước/giờ đã bỏ/...), suppresses the stale phrase match | Low — same scoping/verification as hedge markers | run_08 |
| run_01 | (systemic, no case failed directly on this) | `schema_or_runtime_error` | Every live Coach call (12/12) | `BadRequestError: max_tokens is not supported, use max_completion_tokens` — always fell back to the static message | Live coaching was completely non-functional, even though the fallback kept it pedagogically safe | `coach.py` still called Chat Completions (`chat.completions.create` + `max_tokens` + `response_format`) instead of the Responses API this model requires | Rewrote `Coach.generate()` to use `client.responses.create()` with the existing `CoachDraft` JSON schema (same pattern as `question_generator.py`/`slide_agent.py`); also raised `max_output_tokens` 260→600 and `timeout` 8s→20s after two more real timeout/truncation failures surfaced live, and made the server (not the model) authoritative on `hintLevel` | Low — verified via `test_offline_coach_is_deterministic_without_network` (offline path untouched) plus live traces showing `provider: openai, model: gpt-5.6-luna` on all 9 diagnose cases in run_08 | run_08 |

## Failure taxonomy gợi ý

- `false_positive_misconception`
- `missed_misconception`
- `wrong_primary_misconception`
- `hallucinated_citation`
- `unsupported_citation`
- `failed_to_clarify`
- `scope_violation`
- `answer_leakage`
- `wrong_next_action`
- `stale_state`
- `non_idempotent_transition`
- `schema_or_runtime_error`

## Sau mỗi run ghi 4 dòng

1. Failure gây hại nhất là gì?
2. Nó thuộc lớp chỗ khó nào?
3. Sửa prompt/routing/data/state ở đâu?
4. Full rerun có làm regress case nào trước đó đang pass không?

### run_01 → run_08 (12/30 → 30/30)

1. **Failure gây hại nhất:** lỗi hệ thống ở Coach — `coach.py` gọi sai API cho `gpt-5.6-luna` khiến **100% lượt chẩn đoán live đều lỗi** và âm thầm rơi về câu tĩnh. Không case nào fail trực tiếp vì nó (có fallback an toàn), nhưng nó vô hiệu hóa hoàn toàn phần "AI thật" của tính năng cốt lõi.
2. **Lớp chỗ khó:** `schema_or_runtime_error` (Coach) là nghiêm trọng nhất vì phạm vi ảnh hưởng (mọi lượt chẩn đoán); còn lại chủ yếu là `missed_misconception`/`false_positive_misconception` do bộ regex quá cứng, tập trung ở nhóm `hard` (đúng mục đích thiết kế của nhóm này).
3. **Đã sửa ở:** `app/coach.py` (chuyển Responses API, tăng `max_output_tokens`/`timeout`, server tự quyết `hintLevel`), `app/evaluator.py` (thứ tự kiểm tra, hedge/retraction/contradiction markers, kiểm tra trang giả, mở rộng out-of-scope và correct-pattern), `app/orchestrator.py` (bỏ citation thừa ở nhánh đúng, thêm route `low_confidence`), `app/content.py` (thêm `approved_pages()`). Không sửa `golden_set.json`/`quality_bar.json`.
4. **Regress sau rerun:** không — `python -m pytest -q` tại `codebase/backend` vẫn **18/18 passed** sau mỗi lần sửa, và 30/30 case golden set giữ nguyên PASS qua các lần rerun cuối liên tiếp (`160100` → `160307` → `160711` → `161111`) trong lúc vá thêm 2 lỗi live mới lộ ra (JSON bị cắt cụt, rồi timeout) mà không làm case nào đã pass trước đó fail lại.
