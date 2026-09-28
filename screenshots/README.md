# Bằng chứng CP5 — Render

Chỉ lưu ảnh chụp thật sau khi deploy thành công. Không dùng ảnh minh họa
hoặc đánh dấu hoàn tất khi service chưa chạy.

- `dashboard.png`: trang web service trên Render, thể hiện tên service,
  trạng thái deploy và URL công khai. Không chụp giá trị secret trong Environment.
- `health.png`: trình duyệt hoặc terminal gọi URL HTTPS thật của service
  với đường dẫn `/health`, thấy response `status: ok`. Hiển thị URL để
  liên hệ ảnh với service đã nộp.
- Có thể bổ sung `logs.png`: log runtime thật, có request `/health` trả 200.
- Có thể bổ sung `ready.png`: `/ready` trả `status: ready` và `redis: true`.

Trước khi lưu ảnh, kiểm tra không lộ API key, token, Redis URL có mật khẩu
hoặc thông tin tài khoản nhạy cảm. Ghi kết quả chạy thật vào `DEPLOYMENT.md`;
ảnh không thay thế kiểm tra endpoint bằng `pytest tests/test_cp5.py -v`.

## Bộ ảnh đã lưu

- [Dashboard Render](dashboard.png): service `day12-agent` Live, URL công khai và commit `2def526`.
- [Health qua HTTPS](health.png): URL `/health`, `status: ok`, service và version.
- [Runtime logs](logs.png): các request `/health` trả `200 OK`.

Ảnh được sao chép nguyên vẹn từ file gốc học viên cung cấp trong Downloads,
không chỉnh sửa nội dung. Kết quả test CP5 nằm trong [DEPLOYMENT.md](../DEPLOYMENT.md).
