# Validation — VError (Track D2)

Thư mục này chứa toàn bộ bằng chứng thử nghiệm người dùng thực tế (*User Validation*) phục vụ đánh giá theo **Rubric R6 (Bonus tối đa +8 điểm)** và tiêu chuẩn nghiệm thu của Track D.

## 1. Cấu trúc thư mục

- `user_testing_log.md`: Nhật ký chi tiết 2 phiên thử nghiệm với 2 willing users ngoài nhóm theo quy trình 5 nhịp (Comfort, Context, Task, Observe, Post-test Q&A), ghi nhận hành vi quan sát và quote nguyên văn.

## 2. Tóm tắt kết quả kiểm chứng

- **Đối tượng:** 2 học viên ngoài nhóm đã đăng ký từ CP1:
  - Trần Hữu Đức (`2A202602459`)
  - Bùi Gia Chính (`2A202602693`)
- **Tỷ lệ thất vọng nếu thiếu sản phẩm (Sean Ellis Disappointment):** 2/2 (100%) trả lời *“Rất tiếc (Very Disappointed)”*.
- **Tác động thiết kế:** Đã trích xuất 2 điểm nghẽn UX chính và đưa trực tiếp vào sản phẩm (cập nhật tại `spec.md` §9 Changelog):
  1. Thêm nhãn giải thích trạng thái slide mờ (Productive Failure mode) để tránh người học tưởng mạng lag.
  2. Nâng cấp nút chuyển tiếp gắn trực tiếp số trang slide trọng tâm (`Đi đến Slide 10 trọng tâm →`) và đặt khung Retry làm lại ngay dưới phản hồi chẩn đoán.
