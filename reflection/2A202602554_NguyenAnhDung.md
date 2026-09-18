# Reflection Cá Nhân — Nguyễn Anh Dũng

- **Họ và Tên:** Nguyễn Anh Dũng
- **Mã Học Viên:** 2A202602554
- **Vai trò:** Fullstack / Frontend Lead
- **Dự án:** VError (Track D2 — Học từ lỗi trước / Productive Failure)

---

## 1. Phần việc chính đảm nhiệm trong dự án
- Xây dựng giao diện VLearn reader mô phỏng chuẩn xác nền tảng VLearn gốc (React + Vite + Tailwind CSS + pdf.js).
- Hiện thực hóa cơ chế *Productive Failure Gating*: Xử lý lớp phủ làm mờ slide (veil) khi chưa vượt qua pre-quiz, tối ưu hiệu năng không render PDF độ phân giải cao khi đang bị khóa để tránh lag giật máy.
- Kết nối API FastAPI backend, quản lý session state, idempotency key khi submit attempt và chuyển tiếp mượt mà đến đúng trang slide trọng tâm.

## 2. AI đã hỗ trợ như thế nào trong quá trình làm việc
- Sử dụng công cụ AI hỗ trợ dựng nhanh khung layout giao diện tương thích với ảnh thiết kế của VLearn (toolbar, thumbnail strip, sidebar navigation).
- Hỗ trợ viết các hàm canvas rendering và tính toán tọa độ cuộn tự động của pdf.js khi người học bấm nút chuyển đến slide bằng chứng.

## 3. Bài học kinh nghiệm từ một case fail của chính nhóm
- **Case fail:** Trong phiên test người dùng đầu tiên với bạn Bùi Gia Chính, khi slide bị làm mờ nền, bạn ấy đứng hình mất 5 giây vì tưởng mạng bị lag hoặc trình duyệt bị treo.
- **Bài học rút ra:** Trải nghiệm AI phải luôn minh bạch và đặt đúng kỳ vọng tâm lý (Mental Model - PAIR). Tôi đã lập tức bổ sung một huy hiệu giải thích rõ ràng: *"Chế độ Productive Failure: Slide tạm thời làm mờ để bạn thử cược nhận thức..."* giúp người dùng hiểu ngay mục đích và không cảm thấy ức chế.
