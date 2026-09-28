# Bằng chứng CP5 — Render

Chỉ lưu ảnh chụp thật sau khi deploy thành công. Không dùng ảnh minh họa
hoặc đánh dấu hoàn tất khi service chưa chạy.

- `dashboard.png`: trang web service trên Render, thể hiện tên service,
  trạng thái deploy và URL công khai. Không chụp giá trị secret trong Environment.
- `health.png`: trình duyệt hoặc terminal gọi URL HTTPS thật của service
  với đường dẫn `/health`, thấy response `status: ok`. Hiển thị URL để
  liên hệ ảnh với service đã nộp.
- Có thể bổ sung `ready.png`: `/ready` trả `status: ready` và `redis: true`.

Trước khi lưu ảnh, kiểm tra không lộ API key, token, Redis URL có mật khẩu
hoặc thông tin tài khoản nhạy cảm. Ghi kết quả chạy thật vào `DEPLOYMENT.md`;
ảnh không thay thế kiểm tra endpoint bằng `pytest tests/test_cp5.py -v`.
