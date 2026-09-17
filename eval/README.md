# VError Evaluation Suite

Bộ eval này được thiết kế cho lát cắt **D2 – học từ lỗi trước** của VError, tập trung vào checkpoint Prompt Engineering Day 04.

## Mục tiêu

Bộ test không chỉ đo "đoán đúng misconception" mà đo 6 chiều độc lập:

1. **Route correctness** — hệ thống chọn đúng đường đi (`diagnose`, `correct`, `clarify`, `low-confidence`, `no-basis`, `out-of-scope`).
2. **Diagnosis correctness** — misconception code đúng và không false-positive.
3. **Grounding correctness** — citation chỉ dùng anchor đã duyệt và thực sự thuộc support set của case.
4. **Pedagogical safety** — hint không reveal đáp án/kết luận trước khi learner retry.
5. **Next-action correctness** — learner được đưa đúng bước tiếp theo.
6. **State safety** — không carry stale diagnosis/citation qua attempt/session; xử lý idempotency an toàn.

Một case chỉ PASS khi tất cả hard-check bắt buộc của case cùng PASS.

## Cấu trúc

```text
eval/
├── README.md
├── golden_set.json
├── golden_set.schema.json
├── evaluation_criteria.md
├── quality_bar.json
├── validate_golden_set.py
├── adapter.py
├── run_eval.py
├── score_results.py
├── inter_rater.py
├── manual_review_template.csv
├── error_analysis.md
├── results/
│   └── run_00_TEMPLATE.csv
└── traces/
    └── .gitkeep
```

## Coverage hiện tại

- **30 cases** tổng cộng.
- **10 normal**.
- **12 hard cases**: 3 case cho mỗi lớp `source_truth`, `ambiguous`, `out_of_scope`, `domain_specific`.
- **4 rare/adversarial**.
- **4 integration/state cases**.
- 10 case được đánh dấu `chatlog_pattern_derived`: phát triển **pattern ngôn ngữ/hành vi** từ 5 turn đã được ghi trong `spec.md`, không coi nội dung Prompt Engineering là trích nguyên văn chatlog.

> Nếu TA hiểu yêu cầu "≥10 case từ chatlog thật" là **10 turn nguồn khác nhau**, hãy thay các provenance đang lặp bằng 10 `source_ref` duy nhất trước bản nộp cuối. Không bịa mã turn.

## Chạy kiểm tra coverage trước

```bash
cd eval
python validate_golden_set.py
```

## Contract output tối thiểu

Eval runner kỳ vọng prototype trả về object chuẩn hoá như sau:

```json
{
  "route": "diagnose",
  "misconception_code": "M_PROMPT_LONGER_BETTER",
  "citations": ["D04-P07", "D04-P10"],
  "hint_text": "...",
  "next_action": "retry",
  "answer_revealed": false,
  "session_id": "optional",
  "attempt_id": "optional"
}
```

Nếu API/codebase của nhóm dùng field khác, chỉ sửa `normalize_response()` trong `adapter.py`. **Không sửa golden set để khớp output của model.**

## Cách chạy

### A. Prototype có HTTP endpoint

```bash
export VERROR_EVAL_URL="http://localhost:8000/api/diagnose"
python run_eval.py --mode http
```

Runner POST nguyên `input` của từng case tới endpoint. Có thể set timeout:

```bash
export VERROR_EVAL_TIMEOUT=30
```

### B. Prototype có Python callable

Ví dụ callable `evaluate(payload: dict) -> dict`:

```bash
export VERROR_EVAL_CALLABLE="codebase.backend.evaluator:evaluate"
python run_eval.py --mode python
```

### C. Chạy từ output đã record

```bash
python run_eval.py --mode replay --responses path/to/responses.jsonl
```

Mỗi dòng JSONL:

```json
{"case_id":"N01","response":{"route":"correct", ...}}
```

## Output

Mỗi lượt chạy tạo:

- `results/run_<timestamp>.csv`: đủ 30 case, kể cả fail/error.
- `results/run_<timestamp>_summary.md`: % từng dimension + đối chiếu quality bar.
- `traces/run_<timestamp>.jsonl`: raw input/output để audit AI call.

Không xoá case fail. Không sửa bar sau khi đã freeze ở CP4.

## Quy tắc provenance

`provenance.type` có 3 giá trị:

- `synthetic`: nhóm tự viết.
- `chatlog_pattern_derived`: chỉ dùng pattern từ turn thật; câu Prompt Engineering là biến thể mới.
- `fixture`: case kỹ thuật/state do nhóm dựng.

Không commit data pack hoặc đoạn chat dài vào repo public.
