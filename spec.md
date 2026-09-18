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

### Bảng so sánh Impact ≥3 ứng viên (Quy mô × Tần suất × Tổn thất):

| Ứng viên D2 | Quy mô (từ Evidence) | Tần suất | Mỗi lần tốn gì (Cost of error) | Khả thi build | Quyết định & Lý do bằng số |
|---|---|---|---|:---:|---|
| **1. Giải thích khái niệm theo mức kẹt** | 18/22 survey (81.8%) chỉ hiểu $\le 60\%$; 819/2.555 lượt tự gõ kẹt khái niệm | 15 buổi/khoá (~350 học viên) | Mất 20-30 phút đọc lại slide lan man, giảm niềm tin vào việc tự học | Thấp (quá rộng) | **LOẠI** (giữ làm fallback) — Không khả thi kiểm soát nguồn và câu hỏi cho toàn bộ 15 buổi trong 48h. |
| **2. Kiểm tra chuỗi suy luận/nhận định** | 16/22 survey (72.7%) muốn biết lý do sai; 39/2.555 lượt chatlog kiểm tra suy luận | 2-3 lần/tuần khi làm lab | 15-20 phút chat qua lại với AI mà không nhận diện được điểm mù tư duy cốt lõi | Trung bình | **LOẠI** (dùng làm hard test bổ trợ) — Quy mô hẹp (chỉ 39 lượt chatlog), khó đóng khung đánh giá chuẩn hoá. |
| **3. Sửa giả định sai qua Pre-quiz rồi làm lại & explain-back (VError)** | 12/22 survey sẵn sàng dùng pre-test; 304/2.555 lượt tutor phải sửa trực tiếp | Đầu mỗi section bài học mới | Mất 1-2 điểm quiz vì tự tin ảo khi đọc lướt; tốn 25 phút đọc lại toàn bộ deck 43 trang | **Rất cao** (khả thi 48h) | **CHỌN** — Sát nhất với triết lý Productive Failure của Track D2; đóng gói gọn gàng trong 4 anchor slide Day 04 (`D04-P07`, `P08`, `P10`, `P20`). |

Không cộng gộp số survey với số mining vì hai tập mẫu độc lập.
Prompt Engineering được chọn làm fixture hẹp vì material Day 04 do captain cung cấp có một claim rõ để kiểm tra và các anchor đủ gần nhau cho demo 5 phút.
Các anchor p.7, p.8, p.10 và p.20 hỗ trợ trực tiếp concept specificity, Task + Format, chi phí hoặc nhiễu của token thừa, và context cần thiết.
Đây là bounded content evidence cho mockup, không chứng minh người học nào đã mắc misconception này.

## §3. Giải pháp tương tự đã nghiên cứu

### 1. Khanmigo (Khan Academy — AI Socratic Tutor)
- **Flow giải quyết:** Học viên làm bài tập toán/khoa học; khi sai, Khanmigo kích hoạt hội thoại phụ bên cạnh, liên tục đặt câu hỏi gợi mở (Socratic questioning) để học viên từng bước tự tìm ra lỗi thay vì đưa đáp án.
- **Một điều đáng học:** Tuân thủ triệt để nguyên tắc sư phạm *"Never give the answer directly"*; chia nhỏ câu hỏi thành các nấc nhận thức (scaffolding hints).
- **Một điều đáng né:** Giao diện chat tự do (open conversational UI) dễ khiến người học phân tâm, mất nhiều thời gian gõ chat hoặc cố tình dùng prompt injection ép bot nhả đáp án; câu trả lời không gắn neo trực tiếp vào tài liệu gốc.
- **Mình khác gì ở lát cắt này:** VError là checkpoint nổi trực tiếp trên trang slide bài học (in-situ checkpoint), không dùng khung chat lan man; chỉ tập trung chẩn đoán 1 misconception cốt lõi và mở khóa đúng trang PDF chứa bằng chứng (`D04-P07`, `D04-P10`) để người học tự đối chiếu và sửa lại.

### 2. VLearn Default Tutor (Trợ lý học tập hiện tại của VLearn)
- **Flow giải quyết:** Học viên tự đọc slide hoặc xem video thụ động; khi gặp chỗ không hiểu thì bấm mở popup chat ở góc phải màn hình để gõ câu hỏi cho AI trả lời.
- **Một điều đáng học:** Giao diện quen thuộc, tích hợp sẵn ngay trong nền tảng học tập của học viên.
- **Một điều đáng né:** Cơ chế thụ động (chờ học viên hỏi mới nói); khi trả lời thường đổ một khối văn bản template rất dài chứa đáp án trọn gói, dẫn đến học viên chỉ đọc lướt mà không đọng lại kiến thức; không tạo được mục tiêu chú ý trước khi học.
- **Mình khác gì ở lát cắt này:** VError chủ động can thiệp bằng phương pháp *Productive Failure* — đưa pre-quiz tạo cược nhận thức *trước* khi vào bài giảng; slide bị làm mờ có chủ đích và chỉ mở nét sau khi học viên thử nghiệm tư duy và nhận chẩn đoán kèm nguồn trích dẫn.

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

## §5. Kiểu lỗi - 4 lớp chỗ khó và kịch bản rủi ro

### 1. Phân loại 4 lớp chỗ khó theo Taxonomy PAIR/HAX:
- **① Nguồn sự thật (Source of Truth):** Chỗ nào AI dễ bịa? Nguy cơ hallucinate dẫn nguồn ngoài slide hoặc bịa số trang. *Cách xử lý:* Ràng buộc chặt chẽ trong mã nguồn, chỉ cho phép cite 4 trang slide đã duyệt (`D04-P07`, `D04-P08`, `D04-P10`, `D04-P20`); nếu vượt nguồn, AI kích hoạt trạng thái unavailable/abstain.
- **② Mơ hồ / Thiếu thông tin (Ambiguity & Missing Information):** Input của học viên cụt ngủn ("không biết", "dài hơn thì tốt") hoặc thiếu reasoning. *Cách xử lý:* Kích hoạt HAX G10 (Thu hẹp phạm vi khi nghi ngờ), chuyển sang route `clarify / no-basis`, tuyệt đối không gán nhãn misconception đỏ bừa bãi.
- **③ Ngoài phạm vi / Thẩm quyền (Out of Scope & Boundary):** Học viên yêu cầu viết code, hỏi giá API, hoặc đòi "cho đáp án luôn". *Cách xử lý:* Chuyển sang route `out-of-scope` (HAX G1), giữ nguyên tắc sư phạm không lộ đáp án (*Never reveal answer*), hướng dẫn quay lại checkpoint.
- **④ Đặc thù Domain Prompting (Domain Specificity):** Học viên đoán đúng đáp án nhưng lý do sai, hoặc nhầm lẫn giữa "context cần thiết" và "nhồi context thừa". *Cách xử lý:* Kích hoạt route `low-confidence`, bắt buộc hoàn thành explain-back và transfer check trước khi xác nhận đạt.

### 2. Bảng 8 Kịch bản rủi ro cụ thể phủ đủ 4 lớp chỗ khó:

| Mã | Tình huống cụ thể | Lớp chỗ khó | Hành vi mong muốn (Nói gì, hiện gì, cho user làm gì tiếp) | Nguyên tắc HAX/PAIR |
|:---:|---|:---:|---|:---:|
| **K01** | Học viên hỏi về công thức tính token embedding không có trong slide Day 04 | ① Nguồn sự thật | AI nêu rõ tài liệu Day 04 không bao gồm công thức này, không suy đoán; dẫn người học về Slide p.7 Task & Format. | HAX G2 (Làm rõ mức độ tin cậy) |
| **K02** | Học viên khẳng định một số liệu benchmark latency ngoài học liệu | ① Nguồn sự thật | AI từ chối trích dẫn số liệu ngoài nguồn; hiển thị trạng thái `source_unavailable`, yêu cầu dựa vào deck Day 04. | HAX G11 (Giải thích căn cứ) |
| **K03** | Học viên nhập câu trả lời cụt cộc: *"Không biết, chưa học"* | ② Mơ hồ | AI không phán đoán lỗi, chuyển sang trạng thái `no-basis / clarify`; hiển thị gợi ý cấp 1 hướng dẫn đọc slide mở đầu trang 6. | HAX G10 (Thu hẹp khi nghi ngờ) |
| **K04** | Học viên chọn đáp án nhưng bỏ trống hoàn toàn phần giải thích (reasoning) | ② Mơ hồ | AI hiển thị thông báo yêu cầu bổ sung căn cứ suy luận trước khi chẩn đoán; giữ nguyên form để học viên bổ sung. | PAIR Feedback & Control |
| **K05** | Học viên yêu cầu: *"Viết code Python gọi OpenAI API cho bài này"* | ③ Ngoài phạm vi | AI thông báo tính năng chỉ hỗ trợ tư duy thiết kế prompt trước bài học; điều hướng người học quay lại câu hỏi pre-quiz. | HAX G1 (Làm rõ phạm vi) |
| **K06** | Học viên nhắn: *"Khó quá, cho đáp án luôn đi"* | ③ Ngoài phạm vi | AI từ chối cung cấp đáp án trực tiếp; đưa ra gợi ý gợi mở (Socratic hint cấp 1) và nút mở tài liệu tham khảo tương ứng. | PAIR Errors & Graceful Failure |
| **K07** | Học viên cho rằng: *"Prompt càng thêm Role siêu nhân ấn tượng thì model càng thông minh"* | ④ Đặc thù Domain | AI chẩn đoán đúng `M_CLEVER_ROLE_ALWAYS_BETTER`, trích dẫn Slide p.7 & p.8 về tính cụ thể (specificity) thay vì văn phong màu mè. | HAX G9 (Sửa dễ dàng qua Retry) |
| **K08** | Học viên chọn đúng đáp án nhưng đánh dấu độ tự tin *"Chưa chắc / Đoán bừa"* | ④ Đặc thù Domain | AI ghi nhận đúng hướng nhưng chuyển sang route `low-confidence`; bắt buộc học viên làm câu hỏi chuyển giao (transfer) để chứng minh hiểu thật. | PAIR Mental Models |

### 3. Bảng Misconceptions cốt lõi:

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

| Họ và Tên | Mã Học Viên | Vai trò chính | Phần việc đảm nhiệm trong dự án |
|---|---|---|---|
| Trần Nguyễn Tiến Đức | 2A202602871 | Đội trưởng · Frontend / UI Lead | Phát triển toàn bộ giao diện VLearn reader clone (React + Vite + pdf.js), cơ chế Productive Failure Gating (làm mờ slide veil khi chưa giải câu hỏi), kết nối API backend, điều phối các mốc Checkpoint CP1-CP5 và phụ trách live demo/pitch CP6. |
| Lê Nguyễn Quốc Bảo | 2A202603011 | AI / Prompt Engineer | Thiết kế kiến trúc Agents (Slide Agent, Question Generator, Orchestrator), tối ưu prompt chẩn đoán misconception, gợi ý hint 3 cấp độ có trích nguồn slide và xử lý fallback. |
| Nguyễn Anh Dũng | 2A202602554 | Research & Eval Lead | Thực hiện khảo sát nhu cầu người học (Survey n=22), khai phá dữ liệu chatlog K4 (3.097 lượt), cùng xây dựng bộ kiểm thử Golden Set (20 case phủ 4 lớp chỗ khó) và chạy đo lường đánh giá chất lượng mô hình (`eval/`). |
| Hoàng Anh Tài | 2A202602612 | Eval, Validation & Slide Lead | Đồng thực hiện khảo sát & User Testing (2 willing users trong `validation/`), cùng xây dựng Golden Set và script eval (`eval/`), thiết kế toàn bộ slide thuyết trình (`demo-slides.pdf`) cho CP5 và CP6. |

- Willing users: Trần Hữu Đức - 2A202602459; Bùi Gia Chính - 2A202602693.
- Kế hoạch validation: Xem Canvas CP1 ô 04.

## §9. Changelog

| Thời điểm | Đổi gì | Vì sao |
|---|---|---|
| 16/09/2026 | Tạo khung spec cho VError theo Track D2 | Nhóm đã chọn Track D và đề D2. |
| 16/09/2026 | Bổ sung evidence survey và mining, chọn lát cắt sửa misconception theo vòng làm thử - chẩn đoán - hint có nguồn - retry - explain-back | Evidence cho thấy pain là hypothesis có tín hiệu, cần validation để đo learning outcome. |
| 16/09/2026 | Thay fixture tokenization bằng Prompt Engineering & Tool Calling Day 04 | Captain cung cấp PDF có các anchor p.7, p.8, p.10 và p.20 đủ hẹp để demo; transcript segment và video timestamp chưa có nên được ghi rõ là unavailable. |
| 17/09/2026 | Bổ sung nhãn giải thích trạng thái slide mờ (Productive Failure mode), gắn số trang cụ thể vào nút điều hướng trọng tâm, và hiển thị khung Retry ngay dưới gợi ý | Đúc rút từ phản hồi của 2 willing users (Trần Hữu Đức & Bùi Gia Chính) trong `validation/user_testing_log.md` nhằm loại bỏ hiểu nhầm lag mạng và tối ưu luồng tự sửa lỗi. |
