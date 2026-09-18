# Reflection Cá Nhân — Hoàng Anh Tài

- **Họ và Tên:** Hoàng Anh Tài
- **Mã Học Viên:** 2A202602612
- **Vai trò:** Eval, Validation & Slide Lead
- **Dự án:** VError (Track D2 — Học từ lỗi trước / Productive Failure)

---

## 1. Phần việc chính đảm nhiệm trong dự án
- Đồng thực hiện khảo sát người học và trực tiếp chủ trì 2 phiên thử nghiệm người dùng thực tế (**User Testing**) với 2 willing users ngoài nhóm (`validation/user_testing_log.md`), ghi nhận hành vi quan sát và quote nguyên văn.
- Cùng bạn Nguyễn Anh Dũng xây dựng bộ Golden Set 20 case (`eval/golden_set.json`), viết script đánh giá tự động và phân tích nguyên nhân lỗi sai (`eval/error_analysis.md`).
- Chịu trách nhiệm thiết kế toàn bộ bộ slide thuyết trình **`demo-slides.pdf`** (đúng chuẩn 6 slide theo luật *"Không có bằng chứng thì không có slide"* của Guide §5.1) phục vụ nộp CP5 và thuyết trình chung kết CP6.

## 2. AI đã hỗ trợ như thế nào trong quá trình làm việc
- AI hỗ trợ tổng hợp nhanh các biểu đồ số liệu đánh giá từ file kết quả CSV của đợt chạy eval để đưa vào Slide 4 (Kết quả đo).
- Hỗ trợ xây dựng các kịch bản phỏng vấn bán cấu trúc theo chuẩn Mom Test và script user testing 5 nhịp của Guide §4.2.

## 3. Bài học kinh nghiệm từ một case fail của chính nhóm
- **Case fail:** Trong phiên test người dùng với bạn Trần Hữu Đức, bạn ấy phản ánh rằng sau khi nhận chẩn đoán, nút bấm chuyển tiếp chưa ghi rõ sẽ dẫn tới slide nào khiến bạn ấy tưởng là chuyển sang bài học khác.
- **Bài học rút ra:** Cần gắn rõ ngữ cảnh hành động với phản hồi của AI (HAX G11). Tôi đã trao đổi với bạn Đức làm UI để cập nhật lại nhãn nút bấm thành *"Đi đến Slide 10 trọng tâm →"*, giúp người học biết chính xác mình đang được dẫn về đâu để đối chiếu kiến thức.
