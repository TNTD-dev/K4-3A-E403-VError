# Reflection Cá Nhân — Lê Nguyễn Quốc Bảo

- **Họ và Tên:** Lê Nguyễn Quốc Bảo
- **Mã Học Viên:** 2A202603011
- **Vai trò:** AI / Prompt Engineer
- **Dự án:** VError (Track D2 — Học từ lỗi trước / Productive Failure)

---

## 1. Phần việc chính đảm nhiệm trong dự án
- Thiết kế kiến trúc Prompt và hệ thống Agent: Slide Agent (đọc và phân tích slide PDF), Question Generator (rephrase câu hỏi), và Orchestrator điều phối trạng thái học.
- Xây dựng prompt chẩn đoán lỗi (Diagnosis Prompt) dựa trên Answer Key đã duyệt, đảm bảo AI không bao giờ trực tiếp đưa ra đáp án đúng ở lần thử đầu tiên.
- Thiết lập hệ thống Socratic Hint 3 cấp độ (Hint 1 định hướng $\rightarrow$ Hint 2 trích nguồn $\rightarrow$ Hint 3 giải thích sâu) kèm fallback dự phòng an toàn.

## 2. AI đã hỗ trợ như thế nào trong quá trình làm việc
- Sử dụng LLM để sinh các biến thể câu chữ trong quá trình thử nghiệm prompt, giúp đánh giá độ nhạy (sensitivity) của model trước các câu trả lời ngắn hoặc mơ hồ của người học.
- Hỗ trợ viết regex và format JSON Schema cho output đầu ra của các Agent để backend dễ dàng parse mà không bị vỡ định dạng.

## 3. Bài học kinh nghiệm từ một case fail của chính nhóm
- **Case fail:** Trong lượt chạy thử eval đầu tiên (`run_20260917_154132`), có case học viên nhập câu trả lời ngắn: *"Không biết, chưa học"* thì model lại cố gắng suy diễn đó là lỗi nhận thức về Role (`M_CLEVER_ROLE_ALWAYS_BETTER`).
- **Bài học rút ra:** Không ép AI phải luôn kết luận (Over-confidence). Nhóm đã bổ sung cơ chế HAX G10: khi input thiếu dữ kiện suy luận hoặc người học chọn abstain, AI phải chuyển sang trạng thái `clarify / no-basis` để hướng dẫn người học đọc slide dẫn nhập trang 6 thay vì gán nhãn lỗi sai bừa bãi.
