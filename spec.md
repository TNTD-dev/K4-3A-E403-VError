# AI SPEC - VError · Nhóm VError · Phòng E403

Hướng: [ ] A - VLearn  [ ] B - Trợ lý Học viên  [ ] C - Lesson Studio  [x] D - Học tập thích ứng & tương tác  [ ] E - Làn mở
Loại: [ ] Tối ưu tính năng có sẵn  [x] Tính năng mới
Đề: D2 - Học từ lỗi trước

## Canvas CP1 - 4 ô

### 01. Người dùng và nỗi đau

**Người dùng cụ thể:** Học viên đang tự học một bài VLearn có khái niệm kỹ thuật mới và cần tự kiểm tra cách hiểu trước khi xem lý thuyết.

**Job và workflow hiện tại:** Người học thường lướt nhanh slide để xem ý chính hoặc đọc slide từ đầu.
16/22 phản hồi khảo sát thuộc hai cách này, trong khi chỉ 1/22 bắt đầu bằng câu hỏi hoặc bài tập.

**Nỗi đau:** Sau khi học theo workflow đọc trước, 18/22 người tự đánh giá chỉ hiểu tối đa 60% nội dung.
16/22 chỉ tập trung được ở mức một phần hoặc ít khi, và 19/22 chỉ nhớ ở mức chủ đề chung hoặc một số ý chính trở xuống.

**Giả thuyết cần kiểm chứng:** Khi người học tự trả lời trước và biết chính xác giả định nào sai, họ sẽ dễ quay lại đúng nguồn, tự làm lại, và giải thích lại hơn so với chỉ đọc hoặc nhận đáp án.

### 02. Bằng chứng ban đầu

**Survey evidence, n=22:**

- 16/22 đồng ý ở mức 4-5 rằng biết chính xác vì sao sai giúp hiểu và nhớ tốt hơn.
- 12/22 trả lời `Có lẽ muốn` hoặc `Chắc chắn muốn` dùng 3-5 câu hỏi không tính điểm, nhưng chỉ 5/22 `Chắc chắn muốn`.
- Captain xác nhận cả 22 người trả lời đều ngoài nhóm, nên khảo sát đáp ứng quy mô tối thiểu của chuẩn A.
- Survey vẫn là self-report và câu hỏi về pre-test là một tình huống giả định.

**Mining evidence, mẫu số tách biệt:**

- Trong K4 có 3.097 lượt của 448 học viên.
- Trong 2.555 lượt tự gõ, có 819 lượt (32,1%) mang marker cần làm rõ khái niệm.
- Có 304 lượt tutor reply (11,9% trên 2.555 lượt tự gõ) mang marker sửa trực tiếp.
- K4 có 2.767 lượt `review_concept`, 11 lượt `validate_understanding`, và 6 lượt `ask_probing_question`.
- Các số mining là lượt hoặc lexical proxy, không phải số người bị pain hay số lỗi độc lập.

**Ví dụ ngắn đã ẩn danh từ mining:**

| Mã lượt | Trích ngắn | Tín hiệu |
|---|---|---|
| `T10320` | “Bốn làn sóng là gì” | Cần giải thích khái niệm |
| `T10350` | “mask và polygon là gì” | Cần phân biệt khái niệm |
| `T10417` | “LLM có phải là một dạng của Machine Learning không?” | Đưa nhận định để kiểm tra |
| `T11382` | “vậy IoU đó có phải threshold không?” | Đưa nhận định để kiểm tra |
| `T10765` | “deep learning đưa dữ liệu để ai tự suy luận” | Tutor cần điều chỉnh cách hiểu |

**Giới hạn:** Hai nguồn có mẫu số riêng và không được cộng thành một tỷ lệ.
Chưa có quan sát workflow sau lỗi, retry, explain-back, thời gian bị kẹt, hay kết quả học.

### 03. Lát cắt và automation

**Lát cắt một câu:** Một học viên làm một checkpoint Prompt Engineering ngắn trước khi xem slide hoặc video Day 04; nếu sai, VError chỉ ra giả định “prompt càng dài hoặc càng nhiều thành phần thì luôn tốt hơn”, đưa gợi ý có trích nguồn, yêu cầu làm lại và explain-back; nếu đúng, VError hỏi ngược một tình huống viết prompt cho task mới thay vì chỉ chúc mừng.

**Nguồn nội dung:** `Prompt Engineering & Tool Calling.pdf` do captain cung cấp, giới hạn ở PDF p.7, p.8, p.10 và p.20.
Transcript segment và video timestamp chưa có trong material được cung cấp, nên UI/API hiển thị rõ trạng thái unavailable thay vì bịa vị trí.

**Automation:** Conditional augment.
AI chỉ chẩn đoán khi có misconception và nguồn học liệu đã duyệt.
Khi không đủ căn cứ, AI phải nêu rõ không chắc và dẫn người học về nguồn thay vì kết luận.
VError là active-learning layer gắn vào một Day đã có slide và video, không thay thế việc học thụ động.

**Cost-of-error:** Chẩn đoán sai một misconception có thể dạy người học sai lần thứ hai.
Answer key và citation phải được kiểm soát trước.

**Non-goals:**

- Không cá nhân hóa toàn bộ khóa học.
- Không mở rộng sang mọi chủ đề.
- Không đưa đáp án ngay làm đường mặc định.
- Không tuyên bố người học đã hiểu chỉ vì trả lời đúng một lần.

### 04. Người thử và cách xác nhận

**Willing users đã xác nhận:**

- Trần Hữu Đức - 2A202602459 - học viên ngoài nhóm.
- Bùi Gia Chính - 2A202602693 - học viên ngoài nhóm.

Cột liên hệ tự nguyện trong survey không được dùng thay cho sự đồng ý cụ thể này.

**Validation Track D:** Nhóm sẽ thử ít nhất 5 người ngoài nhóm.
Mỗi người làm cùng một fixture Prompt Engineering với `attempt_1`, chẩn đoán, hint, `attempt_2`, explain-back và transfer check.

**Log bắt buộc:** Task, lỗi quan sát được, chẩn đoán, citation, hint, số lần retry, kết quả `attempt_2`, explain-back, quote ngắn tại lúc bị kẹt, và thay đổi thiết kế.

**Chỉ số cần đo:** Tỷ lệ chẩn đoán đúng, citation hỗ trợ đúng chẩn đoán, làm đúng sau hint, explain-back đúng, số hint trước khi tự sửa, thời gian đến lần làm đúng, và abstain đúng khi không đủ căn cứ.

## §1. User & Job

- Job executor + workflow: Học viên tự học khái niệm kỹ thuật mới trên VLearn và tự kiểm tra cách hiểu trước lý thuyết.
- Core JTBD: Khi chưa chắc mình hiểu một khái niệm mới, tôi muốn thử trả lời trước, biết chính xác giả định nào sai, rồi tự làm lại với nguồn học liệu, để có thể giải thích lại.
- Problem statement: Học viên thường đọc hoặc lướt học liệu trước, nhưng tự báo hiểu và nhớ chưa đầy đủ; workflow hiện tại chưa cho thấy một vòng sửa và làm lại có cấu trúc.
- Evidence: Xem Canvas CP1 ô 02.

## §2. Impact và quyết định chọn

| Candidate D2 | Survey evidence | Mining evidence | Quyết định |
|---|---|---|---|
| Giải thích khái niệm theo mức kẹt | 18/22 tự báo hiểu không quá 60%; 19/22 tự báo nhớ và giải thích lại ở mức 1-3 | 819/2.555 lượt tự gõ có marker cần làm rõ khái niệm | Giữ làm fallback vì quá rộng |
| Kiểm tra nhận định hoặc chuỗi suy luận | 16/22 đồng ý với giá trị của việc biết vì sao sai | 39/2.555 lượt tự gõ có marker kiểm tra nhận định | Dùng làm hard test bổ trợ |
| Sửa một giả định rồi làm lại và explain-back | 12/22 có ý định dùng pre-test, nhưng chỉ 5/22 chắc chắn muốn | 304/2.555 reply có marker tutor sửa | Chọn vì sát D2 nhất |

Không cộng số survey với số mining.
Prompt Engineering được chọn làm fixture hẹp vì material Day 04 do captain cung cấp có một claim rõ để kiểm tra và các anchor đủ gần nhau cho demo 5 phút.
Các anchor p.7, p.8, p.10 và p.20 hỗ trợ trực tiếp concept specificity, Task + Format, chi phí hoặc nhiễu của token thừa, và context cần thiết.
Đây là bounded content evidence cho mockup, không chứng minh người học nào đã mắc misconception này.

## §3. Giải pháp tương tự đã nghiên cứu

- Chưa thực hiện.

## §4. Thiết kế

- Lát cắt, non-goals, automation và cost-of-error: Xem Canvas CP1 ô 03.
- Mức prototype nhắm tới: [x] Mock.
- AI thật ở bước chẩn đoán, gợi ý và phản hồi làm lại.
- Data bài tập và misconception là fixture nhỏ do nhóm duyệt.

| Nguyên tắc | Áp cụ thể vào đâu trong prototype |
|---|---|
| G1 - Làm rõ hệ thống làm được gì | Màn hình nêu rõ VError chỉ hỗ trợ một checkpoint Prompt Engineering của Day 04 và không thay thế slide hoặc video. |
| G2 - Làm rõ hệ thống làm tốt đến đâu | Mỗi gợi ý hiển thị citation PDF page và trạng thái transcript/video unavailable khi không có anchor tương ứng. |
| G10 - Thu hẹp phạm vi khi nghi ngờ | Input mơ hồ hoặc không khớp misconception sẽ dẫn đến câu hỏi làm rõ, không kết luận lỗi. |
| G9 - Sửa dễ dàng | Học viên có ô trả lời lại và explain-back ngay sau gợi ý. |

## §5. Kiểu lỗi - 4 lớp chỗ khó và kịch bản

| Mã | Giả định cần kiểm tra | Nguồn hỗ trợ | Hành vi UI/API |
|---|---|---|---|
| `M_PROMPT_LONGER_BETTER` | Prompt càng dài hoặc càng nhiều thành phần thì luôn tốt hơn. | D04-P07, D04-P10 | Chẩn đoán có điều kiện, hint theo 3 mức, retry không auto-fill. |
| `M_MORE_CONTEXT_ALWAYS_BETTER` | Cứ thêm context thì output sẽ tốt hơn. | D04-P08, D04-P20 | Dẫn về Task + Format và context cần thiết, không kết luận ngoài nguồn. |
| `M_CLEVER_ROLE_ALWAYS_BETTER` | Thêm Role hoặc persona ấn tượng luôn làm prompt tốt hơn. | D04-P07, D04-P08 | Dẫn về specificity và điều kiện để thêm Role, không chấm văn phong. |

Các trạng thái an toàn là `clarify` khi thiếu reasoning, `low-confidence` khi tín hiệu không đủ, `no-basis` khi người học chọn abstain, và `out-of-scope` khi câu hỏi vượt lát cắt.
Các trạng thái này không nhận misconception label màu đỏ và không mở answer reveal.

## §6. Bốn đường đi của trải nghiệm

- Happy path: Entry từ Day 04 -> pre-test gồm answer, reasoning, confidence và basis -> diagnosis có source -> hint 1/2/3 theo yêu cầu -> retry tự viết -> explain-back -> transfer case về prompt JSON -> mastery result và next action mở lại PDF p.7-p.10.
- Low-confidence: Câu trả lời đúng nhưng người học chọn `Chưa chắc` hoặc `Đoán` -> UI nói đúng hướng nhưng chưa đủ bằng chứng -> bắt buộc explain-back và transfer -> chỉ kết luận `demonstrated_in_session` sau hai kiểm tra.
- Failure/không căn cứ: Blank, gibberish hoặc `Chưa có căn cứ` -> `source_review` -> mở anchor PDF p.7 hoặc quay lại retry -> có thể lưu câu hỏi cho người dạy.
- Correction: Misconception có source -> chẩn đoán giả định, không đưa đáp án -> hint tăng dần và mở citation -> người học tự viết lại -> evaluator kiểm tra attempt mới trước khi cho explain-back.
- Clarify: Có answer nhưng thiếu reasoning -> hỏi đang dựa vào độ dài, Role, Context, Task hay Format -> quay lại draft hoặc abstain.
- Out-of-scope: Về giá API, code hoặc kiến thức ngoài source -> nói rõ giới hạn -> quay lại task hoặc lưu câu hỏi, không suy đoán.

## §7. Kiểm thử

- Golden set: Có 3 misconception Prompt Engineering, case đúng, case không đủ căn cứ, case clarify và case ngoài phạm vi.
- Quality bar: Mỗi diagnosis phải có misconception nằm trong answer key và mọi citation phải nằm trong citation-support tương ứng.
- Hint level 1 và 2 không được chứa conclusion cuối, còn level 3 chỉ dùng reviewed explanation sau nỗ lực.
- Public session không chứa expected concept hoặc required explain claims.
- Luồng correction phải đi được từ attempt đến diagnosis, citation hint, retry, explain-back, transfer và completed.
- Luồng no-basis, clarify, out-of-scope, stale state và thiếu idempotency key phải có test riêng.
- Các số liệu learning outcome vẫn là giả thuyết cần validation với ít nhất 5 người ngoài nhóm, không phải benchmark đã có.

## §8. Phân công và kế hoạch

| Thành viên | Mã học viên | Vai trò | Phần việc |
|---|---|---|---|
| Lê Nguyễn Quốc Bảo | 2A202603011 | Chưa phân công | Chưa phân công |
| Hoàng Anh Tài | 2A202602612 | Chưa phân công | Chưa phân công |
| Nguyễn Anh Dũng | 2A202602554 | Chưa phân công | Chưa phân công |
| Trần Nguyễn Tiến Đức | 2A202602871 | Chưa phân công | Chưa phân công |

- Willing users: Trần Hữu Đức - 2A202602459; Bùi Gia Chính - 2A202602693.
- Kế hoạch validation: Xem Canvas CP1 ô 04.

## §9. Changelog

| Thời điểm | Đổi gì | Vì sao |
|---|---|---|
| 16/09/2026 | Tạo khung spec cho VError theo Track D2 | Nhóm đã chọn Track D và đề D2. |
| 16/09/2026 | Bổ sung evidence survey và mining, chọn lát cắt sửa misconception theo vòng làm thử - chẩn đoán - hint có nguồn - retry - explain-back | Evidence cho thấy pain là hypothesis có tín hiệu, cần validation để đo learning outcome. |
| 16/09/2026 | Thay fixture tokenization bằng Prompt Engineering & Tool Calling Day 04 | Captain cung cấp PDF có các anchor p.7, p.8, p.10 và p.20 đủ hẹp để demo; transcript segment và video timestamp chưa có nên được ghi rõ là unavailable. |
