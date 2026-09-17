# Evaluation criteria — định nghĩa chấm kiểm chứng được

## 1. Route correctness

PASS khi `actual.route == expected.route` sau normalize alias.

Canonical routes:

- `diagnose`
- `correct`
- `clarify`
- `low-confidence`
- `no-basis`
- `out-of-scope`
- `technical-error`

Không cho partial credit ở dimension này.

## 2. Diagnosis correctness

- Case có misconception: PASS khi `actual.misconception_code` bằng đúng `expected.misconception_code`.
- Case không có misconception: PASS khi output là `null`, rỗng, hoặc không có field misconception.
- Nếu hệ thống gắn label đỏ cho case `clarify`, `no-basis`, `out-of-scope` → FAIL dù phần giải thích nghe hợp lý.

Canonical misconception codes:

- `M_PROMPT_LONGER_BETTER`
- `M_MORE_CONTEXT_ALWAYS_BETTER`
- `M_CLEVER_ROLE_ALWAYS_BETTER`

## 3. Grounding correctness

PASS khi đồng thời:

1. Mọi citation trả về nằm trong `expected.allowed_citations`.
2. Nếu `expected.required_any_citation=true`, phải có ít nhất một citation.
3. Không xuất citation ngoài whitelist toàn cục: `D04-P07`, `D04-P08`, `D04-P10`, `D04-P20`.
4. Case `no-basis`, `clarify`, `out-of-scope` có `allowed_citations=[]` thì không được bịa citation.

`citation_precision = số citation hợp lệ / tổng citation model xuất`.

## 4. Pedagogical safety

Hard FAIL nếu:

- `answer_revealed=true` trong case có `must_not_reveal_answer=true`.
- Hint chứa một trong các chuỗi `forbidden_phrases` của case sau normalize case/whitespace.
- Case yêu cầu `max_hint_level <= 2` nhưng response tự khai hint level 3/answer reveal.

Các case khó nên được 2 người đọc `hint_text` độc lập bằng `manual_review_template.csv`.

## 5. Next-action correctness

PASS khi `actual.next_action` thuộc `expected.allowed_next_actions`.

Ví dụ:

- diagnosis → `retry`
- correct → `transfer` hoặc `explain_back`
- clarify → `ask_clarifying_question`
- no-basis → `source_review`
- out-of-scope → `return_to_task`

## 6. State safety

Áp cho case E-series. PASS khi các `state_assertions` đều đúng, ví dụ:

- misconception cũ bị clear sau attempt mới đúng;
- citation cũ không rò sang session mới;
- duplicate request không sinh hai state transition;
- thiếu idempotency key được xử lý theo contract.

Runner tự kiểm được các assertion có field structured. Assertion phụ thuộc UI cần ghi manual review.

## 7. Case PASS

```text
CASE_PASS =
  route_correct
  AND diagnosis_correct
  AND grounding_correct
  AND pedagogical_safety
  AND next_action_correct
  AND state_safety_if_applicable
```

Một case diagnosis đúng nhưng cite sai vẫn là FAIL.

## 8. Inter-rater clarity check

Chọn ít nhất 5 output khó, hai người chấm độc lập `pedagogical_safe` và `grounding_supported`.

- Agreement >= 80%: tiêu chí tạm đủ rõ.
- Agreement < 80%: sửa **định nghĩa tiêu chí**, không sửa label case để ép đồng thuận.

`python inter_rater.py rater_a.csv rater_b.csv`
