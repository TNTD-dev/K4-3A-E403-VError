# Reflection Cá Nhân — Trần Nguyễn Tiến Đức

- **Họ và Tên:** Trần Nguyễn Tiến Đức
- **Mã Học Viên:** 2A202602871
- **Vai trò:** Đội trưởng · Product Lead
- **Dự án:** VError (Track D2 — Học từ lỗi trước / Productive Failure)

---

## 1. Phần việc chính đảm nhiệm trong dự án
- Thiết kế khung AI Spec (`spec.md`) và JTBD (Job-to-be-done) định hướng cho phương pháp *Productive Failure* trên VLearn.
- Khai thác và xử lý bằng chứng (Evidence): Phân tích khảo sát người học ($n = 22$) và khai phá dữ liệu chatlog K4 ($3.097$ lượt hội thoại) để chứng minh tính xác thực của nỗi đau.
- Định nghĩa lát cắt sản phẩm 1 câu, lựa chọn mức automation *Conditional Augment* dựa trên phân tích chi phí sai số (*cost-of-error*).
- Điều phối tiến độ 6 Checkpoint (CP1 đến CP6) và chuẩn bị cấu trúc bài thuyết trình 5 phút.

## 2. AI đã hỗ trợ như thế nào trong quá trình làm việc
- AI hỗ trợ nhanh trong việc phân loại sơ bộ các mẫu câu hỏi thường gặp trong chatlog K4 để nhận diện cụm vấn đề về khái niệm.
- Hỗ trợ xây dựng các kịch bản đối sánh rủi ro (Risk scenarios) theo taxonomy 4 lớp lỗi của PAIR/HAX.
- Tuy nhiên, toàn bộ quyết định chọn lát cắt, đặt ranh giới non-goals và thẩm định chất lượng học tập đều do người chịu trách nhiệm và duyệt qua dữ liệu thực tế.

## 3. Bài học kinh nghiệm từ một case fail của chính nhóm
- **Case fail:** Ở giai đoạn đầu, nhóm dự định giải quyết toàn bộ các chủ đề trong khóa học và tự động sinh câu hỏi mở hoàn toàn bằng LLM. Khi chạy thử, LLM thường xuyên bịa ra các khái niệm nằm ngoài slide bài giảng hoặc đưa ra các câu hỏi quá mơ hồ khiến người học hoang mang.
- **Bài học rút ra:** Học cách thu hẹp lát cắt (Scope down) triệt để. Thay vì làm rộng, nhóm tập trung sâu vào một chủ đề duy nhất (Prompt Engineering Day 04) với answer-key và citation đã được duyệt chặt chẽ, kiểm soát hallucination bằng cơ chế Gating và Fallback rõ ràng.
