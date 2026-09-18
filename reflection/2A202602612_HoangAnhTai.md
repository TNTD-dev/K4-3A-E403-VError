# Reflection Cá Nhân — Hoàng Anh Tài

- **Họ và Tên:** Hoàng Anh Tài
- **Mã Học Viên:** 2A202602612
- **Vai trò:** Eval / QA & Validation Lead
- **Dự án:** VError (Track D2 — Học từ lỗi trước / Productive Failure)

---

## 1. Phần việc chính đảm nhiệm trong dự án
- Thiết kế và chuẩn hóa bộ dữ liệu kiểm thử vàng (**Golden Set**) gồm 20 cases (`eval/golden_set.json`), đảm bảo độ phủ 4 lớp chỗ khó (nguồn sự thật, mơ hồ, ngoài phạm vi, đặc thù domain Prompting).
- Viết kịch bản đánh giá tự động (`eval/run_eval.py`, `eval/score_results.py`) và thực thi 2 đợt đo lường chính thức, phân tích nguyên nhân các trường hợp chưa đạt (`eval/error_analysis.md`).
- Tổ chức 2 phiên thử nghiệm thực tế với 2 willing users ngoài nhóm (Trần Hữu Đức và Bùi Gia Chính), ghi lại nhật ký 5 nhịp và tổng hợp các đề xuất cải tiến vào `validation/user_testing_log.md`.

## 2. AI đã hỗ trợ như thế nào trong quá trình làm việc
- Sử dụng AI để hỗ trợ sinh các câu trả lời giả định đa dạng từ góc nhìn học viên (paraphrase inputs), giúp bộ test không bị đơn điệu.
- Hỗ trợ viết script tính toán chỉ số thống kê và đối chiếu tự động kết quả thực chạy với Quality Bar đã cam kết.

## 3. Bài học kinh nghiệm từ một case fail của chính nhóm
- **Case fail:** Trong bộ Golden Set ban đầu, có 2 case thuộc nhóm "Mơ hồ" nhưng định nghĩa đánh giá chiều *Relevance* bị viết chung chung, dẫn đến hai thành viên trong nhóm tự chấm độc lập ra hai kết quả khác nhau (lệch inter-rater agreement).
- **Bài học rút ra:** Đánh giá AI không được dựa trên cảm tính ("vibe check"). Nhóm đã phải viết lại tiêu chí đánh giá thành dạng nhị phân có thể kiểm chứng được độc lập (người ngoài nhóm đọc vào cũng cho ra cùng kết quả đạt/không đạt), tuân thủ đúng bài giảng AI Evaluation của khóa học.
