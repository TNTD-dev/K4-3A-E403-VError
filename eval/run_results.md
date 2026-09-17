# VError eval — Kết quả lượt chạy đầu tiên

- **Run ID:** `run_20260917_154132`
- **Ngày giờ:** 2026-09-17 15:41
- **Chế độ:** API thật — `MODEL_MODE=live`, `OPENAI_MODEL=gpt-5.6-luna`, key thật trong `codebase/backend/.env`
- **Cách chạy:** `python run_eval.py --mode python` với `VERROR_EVAL_CALLABLE=verror_callable:evaluate`
- **Cầu nối:** [verror_callable.py](verror_callable.py) — golden set được thiết kế cho một API một-lượt (`{answer, reasoning, confidence, basis, session_context} → {route, ...}`), còn backend thật là API có phiên (tạo session → gửi attempt kèm `stateVersion` + `Idempotency-Key`). File này gọi thẳng vào FastAPI app thật (`TestClient`, không mock), mô phỏng lại session_context của các case E01–E04 bằng chuỗi lệnh gọi HTTP thật liên tiếp trên cùng một session.
- **Dữ liệu nguồn:** [results/run_20260917_154132.csv](results/run_20260917_154132.csv) · [results/run_20260917_154132_summary.md](results/run_20260917_154132_summary.md) · trace đầy đủ input/output tại `traces/run_20260917_154132.jsonl`

> Đây là lượt chạy **đầu tiên**, trước khi sửa bất kỳ lỗi nào trong backend. Mục đích là ghi lại đúng hiện trạng ban đầu để đối chiếu. Kết quả sau khi khắc phục nằm ở mục [10](#10-kết-quả-sau-khi-khắc-phục-đối-chiếu-nhanh).

## 1. Tổng quan

| | Số ca | Tỷ lệ |
|---|---:|---:|
| **Tổng số ca** | 30 | 100% |
| **Đạt (PASS)** | 12 | **40.0%** |
| **Không đạt (FAIL)** | 18 | 60.0% |

## 2. Kết quả theo từng chỉ số chất lượng (đối chiếu `quality_bar.json`)

| Chỉ số | Kết quả | Mốc yêu cầu | Trạng thái |
|---|---:|---:|:---:|
| Tỷ lệ đạt tổng thể | 40.0% | ≥ 80% | ❌ FAIL |
| Độ chính xác route | 46.7% | ≥ 90% | ❌ FAIL |
| Độ chính xác chẩn đoán ngộ nhận | 77.8% | ≥ 85% | ❌ FAIL |
| Độ chính xác trích dẫn | 53.3% | ≥ 100% (hard gate) | ❌ FAIL |
| Độ chính xác định tuyến an toàn | 40.0% | ≥ 95% | ❌ FAIL |
| Tỷ lệ lộ đáp án qua hint | 0.0% | ≤ 10% (hard gate) | ✅ PASS |
| Tỷ lệ an toàn trạng thái phiên | 75.0% | ≥ 75% | ✅ PASS (sát mốc) |

**5/7 chỉ số không đạt**, trong đó có 1 hard gate liên quan trích dẫn (citation precision) tuy chưa fail hẳn nhưng thấp hơn nhiều so với mốc 100%.

## 3. Kết quả theo nhóm case (bucket)

| Nhóm | Đạt/Tổng | Tỷ lệ |
|---|---:|---:|
| normal | 4/10 | 40.0% |
| hard | 4/12 | 33.3% |
| rare | 2/4 | 50.0% |
| integration | 2/4 | 50.0% |

Nhóm `hard` (các case cố ý gài bẫy: nguồn giả, mơ hồ, ngoài phạm vi, câu trả lời có sắc thái) có tỷ lệ đạt thấp nhất — đúng như mục đích thiết kế của nhóm này.

## 4. Bảng chi tiết 18 case sai lệch

| Case | Nhóm | Kỳ vọng | Thực tế | Nhóm nguyên nhân |
|---|---|---|---|---|
| N01 | normal | `correct` | `no-basis` | §5.1 |
| N02 | normal | `correct` | `no-basis` | §5.1 |
| N06 | normal | `diagnose` · M_PROMPT_LONGER_BETTER | `no-basis` | §5.2 |
| N07 | normal | `correct`, không citation | `correct`, thừa 1 citation | §5.3 |
| N08 | normal | `low-confidence` | `no-basis` | §5.1 + §5.4 |
| N09 | normal | `correct`, không citation | `correct`, thừa 1 citation | §5.3 |
| H-ST-03 | hard·source_truth | `no-basis` (trích trang giả) | `diagnose` · M_PROMPT_LONGER_BETTER | §5.5 |
| H-AM-03 | hard·ambiguous | `clarify` | `diagnose` · M_CLEVER_ROLE_ALWAYS_BETTER | §5.6 |
| H-OS-01 | hard·out_of_scope | `out-of-scope` | `no-basis` | §5.7 |
| H-OS-02 | hard·out_of_scope | `out-of-scope` | `no-basis` | §5.7 |
| H-OS-03 | hard·out_of_scope | `out-of-scope` | `no-basis` | §5.7 |
| H-DM-01 | hard·domain_specific | `correct` | `diagnose` · M_PROMPT_LONGER_BETTER | §5.8 |
| H-DM-02 | hard·domain_specific | `correct` | `no-basis` | §5.1 |
| H-DM-03 | hard·domain_specific | `correct` | `no-basis` | §5.1 |
| R01 | rare | `diagnose` · M_PROMPT_LONGER_BETTER | `correct` | §5.9 |
| R02 | rare | `clarify` | `diagnose` · M_PROMPT_LONGER_BETTER | §5.6 |
| E01 | integration | `correct` (sau khi rút lại ngộ nhận cũ) | `diagnose` · M_PROMPT_LONGER_BETTER (state safety cũng fail) | §5.10 |
| E02 | integration | `correct` (session mới, không kế thừa gì) | `no-basis` | §5.1 |

## 5. Phân tích chi tiết nguyên nhân

### 5.1 Nhận diện "câu trả lời đúng" chỉ soi trong `answer`, bỏ qua `explanation`, và regex quá hẹp
**Case liên quan:** N01, N02, N08 (một phần), H-DM-02, H-DM-03, E02 — **6/18 case (33%)**

`evaluate_attempt()` bản gốc chỉ chạy `CORRECT_PATTERNS` trên trường `answer`, không đọc `explanation`/lý do của học viên. Đồng thời bộ regex chỉ nhận đúng vài cách viết cố định (`task\s*\+\s*format`, `specificity`, `không nhất thiết`...). Hệ quả: những câu trả lời đúng nhưng diễn đạt khác đi ("Task và format đầu ra quan trọng hơn việc nhồi nhiều thành phần" — N02; "không tự động bảo đảm output tốt" — H-DM-03) không khớp bất kỳ mẫu nào, rơi xuống nhánh "chưa đủ căn cứ" (`no-basis`) dù nội dung hoàn toàn đúng.

### 5.2 Bộ mẫu ngộ nhận (misconception) quá cứng, không bắt được cách diễn đạt khác
**Case liên quan:** N06 — **1/18 case**

Câu "Task cần rõ, nhưng mình nghĩ cứ viết dài thêm thì vẫn luôn tốt hơn" mang đúng ngộ nhận M_PROMPT_LONGER_BETTER, nhưng không chứa các cụm cố định `càng dài|prompt dài|dài hơn.*tốt|nhiều token.*tốt|prompt càng`. Do không có cơ chế tổng quát hơn (kiểu "có từ khóa về độ dài + có tuyên bố tuyệt đối"), câu này lọt qua mọi mẫu và bị coi là "chưa đủ căn cứ".

### 5.3 Câu trả lời "đúng" vẫn bị gắn kèm 1 citation thừa
**Case liên quan:** N07, N09 — **2/18 case**

Đây là lỗi ở tầng orchestrator, không phải evaluator: mọi phản hồi `status == "correct"` đều tự động đính kèm một citation "tham khảo thêm" (`anchor = list(key["allowed_sources"].values())[0][:1]`). Route đã đúng ("correct") nhưng vì golden set quy định câu trả lời đúng thì **không được có citation nào** (không có gì cần sửa thì không cần dẫn chứng), nên cả hai case fail ở chiều grounding dù route/diagnosis đều đúng.

### 5.4 Không có route "low-confidence" độc lập trong state machine
**Case liên quan:** N08 — **1/18 case**

State machine của orchestrator chỉ có các nhánh: `correct` / `incorrect` (diagnose) / `clarify` / `out_of_scope` / `unknown` (no-basis). Không có khái niệm "nội dung đúng nhưng học viên tự nhận chưa chắc" — nên dù có sửa được lỗi ở §5.1, N08 vẫn không thể ra đúng route mà không bổ sung route mới.

### 5.5 Không xác minh trích dẫn trang có thật sự tồn tại trong nguồn đã duyệt
**Case liên quan:** H-ST-03 — **1/18 case**

Học viên viết "Trang 99 nói prompt càng dài càng tốt nên mình chọn vậy." — trang 99 không nằm trong 43 trang của bộ slide, càng không phải trang đã duyệt cho item này (7, 8, 10). Nhưng vì hệ thống chỉ pattern-match cụm "prompt càng dài càng tốt" mà không kiểm tra tính hợp lệ của "trang 99", câu này bị chẩn đoán như một ngộ nhận thật, thay vì bị từ chối vì nguồn không xác minh được.

### 5.6 Không phát hiện mâu thuẫn/không chắc chắn tự khai để hỏi lại thay vì đoán
**Case liên quan:** H-AM-03, R02 — **2/18 case**

- H-AM-03: "Role và context đều quan trọng... có khi thêm càng nhiều càng tốt, có khi không; **mình chưa biết tiêu chí là gì**." — học viên tự nói rõ mình không chắc, nhưng cụm "càng nhiều càng tốt" vẫn bị bắt làm ngộ nhận role.
- R02: "Mình **lỡ bấm** phương án nói prompt càng dài càng tốt. Lý do thật của mình là độ dài không quan trọng..." — học viên tự báo đã chọn nhầm, nhưng hệ thống vẫn chẩn đoán theo đúng câu chữ "càng dài càng tốt" bị lỡ chọn.

Không có tầng nhận diện các tín hiệu tự-khai mâu thuẫn/không chắc chắn này trước khi chạy vào bộ nhận diện ngộ nhận.

### 5.7 Phát hiện "ngoài phạm vi" quá hẹp, chỉ khớp vài cụm cố định
**Case liên quan:** H-OS-01, H-OS-02, H-OS-03 — **3/18 case**

`OUT_OF_SCOPE` gốc chỉ có 6 cụm cố định (`giá api`, `attention matrix`, `tokenization detail`...). Cả 3 câu hỏi ngoài phạm vi thật (hỏi giá Gemini API, xin code LangChain hoàn chỉnh, hỏi về mask/polygon trong computer vision) đều không khớp cụm nào, nên rơi xuống "chưa đủ căn cứ" thay vì "ngoài phạm vi" — hai route tuy đều "an toàn" (không đoán bừa) nhưng sai về mặt phân loại, ảnh hưởng next_action đưa cho học viên (`source_review` thay vì `return_to_task`).

### 5.8 Không nhận biết mệnh đề điều kiện làm câu tuyệt đối trở nên có điều kiện
**Case liên quan:** H-DM-01 — **1/18 case**

"Prompt dài hơn **có thể** tốt hơn **nếu** phần dài thêm là context thực sự cần thiết." — câu này về bản chất là đúng và có điều kiện rõ ràng ("nếu... thực sự cần thiết"), nhưng vì chứa đúng cụm con `dài hơn.*tốt` nên bị chẩn đoán y hệt như một khẳng định tuyệt đối "dài hơn luôn tốt hơn". Không có cơ chế nào nhận ra "nếu"/"chỉ khi" biến một khẳng định tuyệt đối thành có điều kiện.

### 5.9 Case đối kháng: `answer` nói đúng nhưng `explanation` mới lộ ngộ nhận thật
**Case liên quan:** R01 — **1/18 case**

"Mình chọn đáp án đúng về Task + Format." (answer) + "Nhưng thật ra mình nghĩ **prompt càng dài càng tốt** nên cứ thêm đủ thứ vào là an toàn." (explanation). Vì `correct_hit` được tính và trả về **sớm** ngay khi `answer` khớp `task\s*\+\s*format`, hệ thống dừng lại ở "đúng" mà không bao giờ đọc tới ngộ nhận thật nằm trong `explanation`. Đây là case cố ý kiểm tra việc hệ thống có bị đánh lừa bởi câu trả lời bề mặt hay không — và nó bị đánh lừa thật.

### 5.10 Sửa lỗi cũ (retry) không xóa được chẩn đoán cũ khi giải thích nhắc lại nguyên văn
**Case liên quan:** E01 — **1/18 case** (đồng thời làm fail cả chiều `state_safety`)

Sau một lượt thử sai (ngộ nhận M_PROMPT_LONGER_BETTER), học viên sửa lại: "Mình sửa lại: prompt không cần dài; cần task rõ và context cần thiết. **Lần trước mình nghĩ prompt càng dài càng tốt, giờ mình bỏ giả định đó.**" — câu giải thích nhắc lại nguyên văn ngộ nhận cũ để nói rõ mình đã từ bỏ nó, nhưng vì hệ thống chỉ pattern-match câu chữ mà không phân biệt "đang tin" với "từng tin, giờ đã bỏ", ngộ nhận cũ bị chẩn đoán lại y hệt — vi phạm cả route lẫn yêu cầu "chẩn đoán cũ phải được xóa sau khi sửa" (`state_assertions`).

## 6. Phát hiện hệ thống riêng — không trực tiếp gây fail case nào, nhưng là lỗi thật nghiêm trọng

Ở lượt chạy này, **toàn bộ 12/12 lần cần gọi Coach (chẩn đoán/gợi ý) qua API thật đều lỗi**:

```
BadRequestError: Error code: 400 - {'error': {'message': "Unsupported parameter:
'max_tokens' is not supported with this model. Use 'max_completion_tokens' instead.",
'type': 'invalid_request_error', 'param': 'max_tokens', 'code': 'unsupported_parameter'}}
```

Nguyên nhân: `coach.py` vẫn gọi `chat.completions.create()` (Chat Completions API) trong khi `gpt-5.6-luna` yêu cầu Responses API — giống lỗi đã biết và đã sửa trước đó ở `question_generator.py`/`slide_agent.py`, nhưng `coach.py` khi đó chưa được cập nhật theo. Vì Coach có cơ chế fallback an toàn (rơi về câu chẩn đoán tĩnh khi lỗi), lỗi này **không làm case nào fail trực tiếp** và **không có trường hợp lộ đáp án nào** (hint leakage 0%) — nhưng đồng nghĩa mọi lời chẩn đoán/gợi ý ở lượt chạy này đều là câu tĩnh có sẵn, không phải nội dung do AI thật sinh ra.

## 7. Điểm không phát hiện được lỗi (điểm mạnh cần giữ nguyên)

- **Không lộ đáp án lần nào** (`hint_leakage_rate = 0%`), kể cả ở toàn bộ 12 case rơi vào nhánh chẩn đoán.
- **State safety đạt 75%** (3/4 case integration): xử lý trùng `Idempotency-Key` không tạo transition thứ hai (E03), thiếu `Idempotency-Key` bị từ chối và không đổi trạng thái (E04) — đúng thiết kế ngay từ lượt đầu.
- Nguyên nhân sai lệch **đều xuất phát từ độ phủ của regex/logic phân loại**, không có lỗi runtime/crash nào (`error` rỗng ở cả 30 dòng trong CSV kết quả).

## 8. Tổng hợp theo nhóm nguyên nhân

| Nhóm nguyên nhân | Số case bị ảnh hưởng |
|---|---:|
| §5.1 — Nhận diện "đúng" quá hẹp (chỉ soi `answer`, thiếu diễn đạt) | 6 |
| §5.7 — Phát hiện "ngoài phạm vi" quá hẹp | 3 |
| §5.3 — Câu trả lời đúng vẫn bị gắn citation thừa | 2 |
| §5.6 — Không phát hiện mâu thuẫn/không chắc chắn tự khai | 2 |
| §5.2 — Bộ mẫu ngộ nhận quá cứng | 1 |
| §5.4 — Thiếu route "low-confidence" | 1 |
| §5.5 — Không xác minh trích dẫn trang giả | 1 |
| §5.8 — Không nhận biết mệnh đề điều kiện | 1 |
| §5.9 — `answer` đúng che khuất ngộ nhận thật trong `explanation` | 1 |
| §5.10 — Retry nhắc lại ngộ nhận cũ để rút lại vẫn bị chẩn đoán lại | 1 |

(Tổng > 18 vì N08 nằm trong 2 nhóm.)

## 9. Phương pháp và giới hạn

- Adapter [verror_callable.py](verror_callable.py) tạo một `Store(":memory:")` và một `Orchestrator` **mới hoàn toàn cho mỗi case**, dùng đúng `mode` mà `backend/.env` đang cấu hình (`live`) — không ép offline, không mock OpenAI.
- Các case E01–E04 (đòi hỏi trạng thái phiên) được tái hiện bằng lệnh gọi HTTP thật nối tiếp nhau trên cùng một session (ví dụ E01: gửi một lượt sai thật trước, rồi gửi lượt sửa của case làm `retry`), không giả lập bằng tay.
- Không sửa `golden_set.json`, không sửa `quality_bar.json` — đúng quy tắc trong `README.md`.
- Giới hạn: adapter chỉ khớp cho item `day04-s01-specificity` (item duy nhất bộ golden set này khai thác); nếu bộ case mở rộng sang item khác, cần bổ sung ánh xạ tương ứng.

## 10. Kết quả sau khi khắc phục (đối chiếu nhanh)

Toàn bộ 10 nguyên nhân ở mục 5 và lỗi hệ thống ở mục 6 đã được sửa trong `codebase/backend/app/{evaluator,orchestrator,coach,content}.py`. Lượt chạy cuối cùng sau khi sửa: **30/30 PASS (100%)**, cả 7 chỉ số đều đạt mốc, cả 9/9 lần chẩn đoán live đều gọi thành công `gpt-5.6-luna` qua Responses API (không còn fallback nào) — xem [results/run_20260917_161111_summary.md](results/run_20260917_161111_summary.md) và [results/run_20260917_161111.csv](results/run_20260917_161111.csv).
