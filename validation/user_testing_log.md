# Báo cáo Thử nghiệm Người dùng (User Testing Log) — VError (Track D2)

> **Mục tiêu:** Kiểm chứng trải nghiệm học theo phương pháp *Productive Failure* (Học từ lỗi trước khi xem lý thuyết) trên prototype VError, thu thập phản hồi định tính nguyên văn từ người học thực tế ngoài nhóm để hoàn thiện sản phẩm trước vòng chung kết.  
> **Căn cứ:** Quy chuẩn Khối R6 (Bonus +8 điểm) — `04-rubric.md` và Hướng dẫn §4.2 — `02-guide.md`.

---

## 1. Thông tin Đối tượng Thử nghiệm (Willing Users)

Nhóm đã mời 2 học viên ngoài nhóm thuộc danh sách **Willing Users đã đăng ký từ mốc CP1** (`spec.md`):

| STT | Họ và Tên | Mã Học Viên | Lớp | Vai trò / Bối cảnh | Thời gian test |
|:---:|---|---|:---:|---|:---:|
| 1 | **Trần Hữu Đức** | 2A202602459 | 2A | Học viên tự học VLearn, thường đọc slide từ đầu đến cuối một cách thụ động | 17:30 · 17/09/2026 |
| 2 | **Bùi Gia Chính** | 2A202602693 | 2A | Học viên hay gặp khó khăn trong việc nhớ và phân biệt các kỹ thuật Prompting | 20:00 · 17/09/2026 |

---

## 2. Quy trình Thử nghiệm 5 Nhịp (10 phút/người theo Guide §4.2)

1. **Comfort (~1 phút):** Người điều phối giải thích: *"Tụi mình đang đánh giá sản phẩm và phương pháp học, không đánh giá bạn; không có câu trả lời đúng hay sai — bạn hãy cứ thoải mái suy nghĩ thành lời (think-aloud)."*
2. **Context (~1 phút):** Khơi gợi trải nghiệm thật: *"Lần gần nhất bạn tự học một bài lý thuyết kỹ thuật mới trên VLearn, bạn thường bắt đầu như thế nào và cảm thấy hiệu quả ra sao?"*
3. **Task (~1 phút):** Giao nhiệm vụ theo outcome: *"Bạn chuẩn bị học Buổi 4: Prompt Engineering & Tool Calling. Hãy dùng VError để bắt đầu bài học, tự kiểm tra kiến thức trước khi đọc slide và xem cách hệ thống hỗ trợ bạn."*
4. **Observe (~5 phút):** Quan sát độc lập, không can thiệp, không giải thích thay giao diện; chỉ ghi lại hành vi thao tác, chỗ ngập ngừng, phản ứng khi gặp slide mờ và nhận chẩn đoán AI.
5. **Post-test Q&A (~2 phút):** Phỏng vấn 4 câu hỏi định chuẩn (kèm câu hỏi Disappointment của Sean Ellis).

---

## 3. Bảng Nhật ký Thử nghiệm Chi tiết (Observation & Quotes)

| Người thử | Task được giao | Quan sát hành vi (Behavior) | Trích dẫn nguyên văn (Verbatim Quotes) | Mức độ nghiêm trọng |
|---|---|---|---|:---:|
| **Trần Hữu Đức**<br>(`2A202602459`) | Bắt đầu học Day 04, làm Pre-quiz Phần 1 về Độ dài và Context trong Prompting. | - Mở bài học, thấy slide bài 4 bị làm mờ và khung Pre-quiz nổi lên.<br>- Đọc đề bài, chọn đáp án *"Prompt càng dài và càng chi tiết thì kết quả luôn càng tốt"*, gõ giải thích: *"Cần nhồi hết ngữ cảnh vào để model không bị thiếu thông tin"*.<br>- Bấm gửi $\rightarrow$ AI chẩn đoán phát hiện giả định sai `M_PROMPT_LONGER_BETTER` và đưa Hint 1 có dẫn nguồn Slide p.7 & p.10.<br>- Ban đầu hơi lúng túng tìm nút xem lại slide, sau đó bấm nút *"Đi đến kiến thức trọng tâm"* $\rightarrow$ PDF tự động cuộn đến trang 10 và mở khóa nội dung.<br>- Thử làm lại (Retry) với giải thích mới dựa trên context dilution. | *"Trước giờ mình toàn viết prompt dài ngoằng rồi nghĩ thế mới chuẩn. Lúc AI chỉ ra trang 7 và trang 10 nói về chi phí token với loãng ngữ cảnh, mình mới giật mình."*<br><br>*"Cái hay là nó không cho đáp án ngay mà bắt mình đọc chỗ trang 10 rồi tự sửa lại. Nhưng lúc vừa gửi xong, nút 'Đi đến kiến thức trọng tâm' lúc đầu mình không rõ nó sẽ dẫn đi đâu, tưởng là chuyển sang bài khác."*<br><br>*(Câu hỏi Disappointment)*: **Rất tiếc (Very Disappointed)** — *"Nếu có tính năng này cho các bài học nhiều khái niệm trừu tượng thì học đỡ buồn ngủ hơn nhiều."* | **Trung bình**<br>(Cần làm rõ đích đến của nút dẫn nguồn slide) |
| **Bùi Gia Chính**<br>(`2A202602693`) | Bắt đầu học Day 04, thử tương tác với các tình huống khó / cố tình nhập mơ hồ. | - Mở bài học, thấy slide bị mờ (veil), do dự khoảng 5 giây vì tưởng mạng bị chậm hoặc file PDF chưa tải xong.<br>- Nhìn thấy form câu hỏi pre-quiz mới hiểu là cần trả lời.<br>- Cố tình gõ thử một câu cộc lốc: *"Không biết, chưa học sao biết"* để xem AI xử lý thế nào.<br>- Hệ thống không phán đoán lỗi bừa (tuân thủ HAX G10) mà chuyển sang trạng thái `clarify / no-basis`, đưa gợi ý cấp 1 hướng dẫn học viên đọc slide dẫn nhập trang 6.<br>- Sau đó Chính làm lại nghiêm túc, chọn thử giả định thêm Role siêu nhân (`M_CLEVER_ROLE_ALWAYS_BETTER`), nhận chẩn đoán và trích dẫn trang 8. | *"Lúc đầu thấy slide mờ tịt mình cứ tưởng máy bị đơ hay mạng lag, mãi sau mới để ý cái bảng trắc nghiệm ở giữa."*<br><br>*"Bất ngờ nhất là lúc mình gõ bừa 'không biết', bot nó không mắng hay phán bừa mà nó bảo nhận thấy mình chưa có căn cứ và chỉ mình đọc lướt trang 6 trước. Rất tôn trọng người học."*<br><br>*"Gợi ý chia 3 cấp độ (Hint 1, 2, 3) rất hợp lý, không bị cảm giác bị mớm tận miệng."*<br><br>*(Câu hỏi Disappointment)*: **Rất tiếc (Very Disappointed)** — *"Học kiểu bị 'bắt bài' trước thế này nhớ dai hơn hẳn đọc slide chay."* | **Cao**<br>(Trải nghiệm nhận diện trạng thái mờ slide cần trực quan hơn) |

---

## 4. Bốn Dòng Tổng Hợp Đúc Rút (Synthesis)

1. **Chủ đề lặp lại nhiều nhất (Most common theme):**
   - Cả 2 học viên đều hào hứng với việc *“được thử đoán và bị chỉ ra chỗ sai trong tư duy”* thay vì đọc slide một chiều. Việc AI trích dẫn chính xác số trang slide (`D04-P07`, `D04-P10`) tạo độ tin cậy rất cao (HAX G2, G11).
   - Tuy nhiên, trạng thái ban đầu khi slide bị làm mờ (gated veil) cần có chỉ dẫn rõ ràng để tránh hiểu nhầm là lỗi kết nối mạng.
2. **Thay đổi đã đưa vào sản phẩm trước buổi Demo (Đã cập nhật vào `spec.md` §9 Changelog):**
   - **Thay đổi 1 (Visual Gating Clarification):** Bổ sung huy hiệu (Badge) và thông điệp giải thích nổi bật trên overlay Pre-quiz: *"Chế độ Productive Failure: Slide tạm thời làm mờ để bạn thử cược nhận thức trước, tự động mở nét ngay sau khi gửi câu trả lời"*.
   - **Thay đổi 2 (Explicit Slide Anchor Navigation):** Đổi nhãn nút hành động sau chẩn đoán từ *"Đi đến kiến thức trọng tâm"* thành *"Đi đến Slide [Số trang] trọng tâm →"* và giữ nguyên khung Retry ngay dưới gợi ý để học viên làm lại tức thì mà không bị mất dấu vết tư duy.
3. **Điểm giữ nguyên có lý do căn cứ (Deliberately retained):**
   - **Không cung cấp đáp án đúng ở lần thử đầu tiên:** Mặc dù người học có tâm lý muốn biết ngay đáp án đúng, nhóm kiên quyết giữ luồng Socratic Hint (Gợi ý $\rightarrow$ Tự làm lại $\rightarrow$ Explain-back) theo đúng nguyên lý sư phạm của Track D2 (*Productive Failure*).
4. **Đưa vào Backlog phát triển tiếp theo (Slide 6 roadmap):**
   - Thêm biểu đồ radar hiển thị các misconception phổ biến trong toàn lớp để học viên biết mình đang sai giống bao nhiêu % bạn học khác.
   - Mở rộng hỗ trợ video timestamp khi học liệu Day 04 bổ sung video bài giảng chính thức.

---

## 5. Kết luận Xác minh cho Rubric R6 (+8 Điểm Thưởng)

- [x] Có feedback log đầy đủ từ **2 người ngoài nhóm** (thuộc danh sách willing users khai tại CP1).
- [x] Ghi nhận đầy đủ: Tên, Mã SV, Task giao, Hành vi quan sát, Quote nguyên văn, Mức độ nghiêm trọng.
- [x] Có $\ge 1$ thay đổi thiết kế cụ thể xuất phát từ phản hồi người dùng đã được hiện thực hóa và ghi nhận trong Changelog của `spec.md`.
