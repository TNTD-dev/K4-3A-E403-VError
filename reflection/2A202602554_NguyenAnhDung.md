# Reflection Cá Nhân — Nguyễn Anh Dũng

- **Họ và Tên:** Nguyễn Anh Dũng
- **Mã Học Viên:** 2A202602554
- **Vai trò:** Research & Eval Lead
- **Dự án:** VError (Track D2 — Học từ lỗi trước / Productive Failure)

---

## 1. Phần việc chính đảm nhiệm trong dự án
- Thực hiện khảo sát nhu cầu người học ($n = 22$ học viên ngoài nhóm) và phân tích định lượng (72.7% học viên học thụ động chỉ nhớ lướt ý chính; 72.7% xác nhận việc biết chính xác vì sao sai giúp nhớ sâu hơn) để thiết lập Chuẩn A cho Bằng chứng (`data/survey_log.md`).
- Khai phá dữ liệu chatlog thực tế K4 ($3.097$ lượt của 448 học viên, trích xuất $819$ lượt gặp khó khăn về khái niệm và $304$ lượt tutor phải sửa trực tiếp) để thiết lập Chuẩn B.
- Cùng bạn Hoàng Anh Tài xây dựng bộ dữ liệu kiểm thử vàng (**Golden Set**) gồm 20 case bao phủ 4 tầng chỗ khó, đặc biệt là các case phát triển từ chatlog thật.
- Đồng thực hiện chạy kiểm thử tự động trên harness (`eval/run_eval.py`), đối chiếu kết quả đo lường với Quality Bar đã cam kết.

## 2. AI đã hỗ trợ như thế nào trong quá trình làm việc
- Sử dụng LLM để lọc nhanh và gán nhãn các marker hội thoại trong tập dữ liệu chatlog lớn ($3.097$ lượt), giúp tiết kiệm hàng chục giờ phân loại thủ công.
- Hỗ trợ xây dựng các biến thể câu hỏi và câu trả lời thử nghiệm trong quá trình thiết lập Golden Set.

## 3. Bài học kinh nghiệm từ một case fail của chính nhóm
- **Case fail:** Trong đợt chạy eval đầu tiên, hệ thống ghi nhận một số case fail do định nghĩa tiêu chí đánh giá chiều *Relevance* bị viết chung chung, khiến việc chấm điểm bị mơ hồ giữa hai người chấm.
- **Bài học rút ra:** Đánh giá sản phẩm AI phải tách rời cảm tính ("vibe check") và đưa về các tiêu chí nhị phân có thể kiểm chứng được độc lập. Tôi cùng nhóm đã chuẩn hóa lại `eval/evaluation_criteria.md` để đảm bảo bất kỳ ai ngoài nhóm đọc vào cũng chấm ra cùng một kết quả.
