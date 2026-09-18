# Reflection Cá Nhân — Trần Nguyễn Tiến Đức

- **Họ và Tên:** Trần Nguyễn Tiến Đức
- **Mã Học Viên:** 2A202602871
- **Vai trò:** Đội trưởng · Frontend / UI Lead
- **Dự án:** VError (Track D2 — Học từ lỗi trước / Productive Failure)

---

## 1. Phần việc chính đảm nhiệm trong dự án
- Phát triển toàn bộ giao diện VLearn reader clone (React + Vite + Tailwind CSS + pdf.js) bám sát trải nghiệm học tập thực tế của VLearn.
- Hiện thực hóa cơ chế sư phạm *Productive Failure Gating*: Xây dựng lớp phủ làm mờ slide (veil) khi người học chưa hoàn thành pre-quiz, đảm bảo học viên phải đưa ra cược nhận thức trước khi xem lý thuyết; tối ưu hóa chỉ render preview nhẹ để không giật lag máy.
- Tích hợp API FastAPI backend (phiên học, nộp attempt, gợi ý hint 3 cấp độ, điều hướng slide bằng chứng) và quản lý session state mượt mà.
- Điều phối tiến độ cả nhóm qua các mốc Checkpoint CP1 đến CP5 và phụ trách phần live demo/pitch chính tại CP6.

## 2. AI đã hỗ trợ như thế nào trong quá trình làm việc
- Hỗ trợ dựng nhanh các component giao diện React mô phỏng chuẩn xác các thành phần của VLearn (toolbar, PDF canvas, dải thumbnail, pre-quiz card nổi).
- Hỗ trợ viết các thuật toán tính toán tọa độ cuộn mượt mà của pdf.js để tự động đưa người học đến đúng trang slide bằng chứng khi nhận chẩn đoán từ AI.

## 3. Bài học kinh nghiệm từ một case fail của chính nhóm
- **Case fail:** Khi đưa prototype cho bạn Bùi Gia Chính test thử lần đầu, bạn ấy đứng hình mất 5 giây vì thấy slide bị làm mờ nền và tưởng mạng lag hoặc trình duyệt bị lỗi.
- **Bài học rút ra:** Trải nghiệm AI phải luôn minh bạch và đặt đúng kỳ vọng tâm lý (Mental Model - PAIR). Tôi đã lập tức bổ sung huy hiệu và dòng thông báo rõ ràng trên card câu hỏi: *"Chế độ Productive Failure: Slide tạm thời làm mờ để bạn thử cược nhận thức trước, tự động mở nét ngay sau khi gửi"*, giúp người dùng hiểu ngay mục đích và không cảm thấy ức chế.
