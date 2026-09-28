# Thông Tin Deploy — Checkpoint 5

## Thông Tin Học Viên

| Mục | Nội dung |
|-----|----------|
| Họ và tên (theo tên repository) | Bui Dinh De |
| Mã học viên | 2A202602818 |
| Repo | https://github.com/buide03/K4-L3A-DAY12-BuiDinhDe-2A202602818-Cloud-Service-And-Deployment |

Giữ nguyên tên repository theo lựa chọn của học viên.

## Service

| Mục | Nội dung |
|-----|----------|
| Public URL | https://day12-agent-x6ug.onrender.com |
| Platform | Render — web service Docker Free và Key Value Free |
| Ngày deploy | 28/09/2026, 17:43 GMT+7 (dashboard Render) |
| Commit triển khai | `2def526` |
| Web service / Redis | `day12-agent` / `day12-redis` |
| Cấu hình | `render.yaml`, vùng Singapore |

Luồng chạy: HTTPS → FastAPI → xác thực → rate limit → budget → Redis history → mock LLM.
`/health` kiểm tra liveness; `/ready` xác nhận kết nối Redis. Đường dẫn `/`
chưa được khai báo nên trả 404; điều này không phải lỗi triển khai.
Không sử dụng phương án local fallback.

## Biến Môi Trường Trên Cloud

Chỉ ghi tên biến và nguồn cấu hình, không ghi giá trị secret.

| Biến | Nguồn |
|------|-------|
| `PORT` | Render tự cấp; Docker CMD đọc biến này |
| `AGENT_API_KEY` | Nhập riêng trên Render; Blueprint dùng `sync: false` |
| `REDIS_URL` | Blueprint lấy `connectionString` từ Key Value `day12-redis` |
| `RATE_LIMIT_PER_MINUTE` | `render.yaml` |
| `MONTHLY_BUDGET_USD` | `render.yaml` |
| `LOG_LEVEL` | `render.yaml` |

## Lệnh Kiểm Tra

Chạy trong Bash. Nhập khóa của service bằng lời nhắc ẩn; không dán khóa vào
lệnh, tài liệu hoặc ảnh. Tắt shell tracing trước khi thao tác với khóa.

```bash
URL=https://day12-agent-x6ug.onrender.com
curl -i "$URL/health"
curl -i "$URL/ready"
curl -i -X POST "$URL/ask" \
  -H 'Content-Type: application/json' -d '{"question":"Hello"}'

set +x
read -rsp 'API key của service: ' DEPLOY_API_KEY
printf '\n'
export DEPLOY_API_KEY
# Truyền header qua stdin để khóa không nằm trong tham số tiến trình curl.
printf 'X-API-Key: %s\n' "$DEPLOY_API_KEY" | \
  curl -i -X POST "$URL/ask" -H @- \
    -H 'Content-Type: application/json' \
    -H "X-User-Id: cp5-manual-$(date +%s)" \
    -d '{"question":"Deploy la gi?"}'

LIMIT_USER="cp5-limit-$(date +%s)"
for i in $(seq 1 15); do
  printf 'X-API-Key: %s\n' "$DEPLOY_API_KEY" | \
    curl -sS -o /dev/null -w '%{http_code} ' -X POST "$URL/ask" \
      -H @- -H 'Content-Type: application/json' \
      -H "X-User-Id: $LIMIT_USER" -d '{"question":"test"}'
done
printf '\n'
LOCAL_FALLBACK=false .venv/bin/python -m pytest tests/test_cp5.py -v
unset DEPLOY_API_KEY
```

Dùng một user riêng cho thử rate limit để không ảnh hưởng bài kiểm tra xác thực.
Mười lệnh đầu phải nằm trong cùng cửa sổ 60 giây để quan sát 429 ở các lệnh sau.
`DEPLOY_API_KEY` dùng cho test cloud; không phải token Render. Có thể truyền
biến vào tiến trình test mà không sửa `.env`.

## Kết Quả Chạy Thật

Các yêu cầu dưới đây được chạy bằng HTTPX trên URL công khai; không sử dụng
fake Redis hoặc mock HTTP response. LLM của bài lab vẫn là mock LLM offline.

Thời điểm kiểm tra (UTC): `2026-09-28T11:00:25.817074+00:00`.

### GET /health

HTTP status: **200**

```json
{
  "status": "ok",
  "service": "day12-agent",
  "version": "1.0.0"
}
```

### GET /ready

HTTP status: **200**

```json
{
  "status": "ready",
  "redis": true
}
```

### POST /ask (không API key)

HTTP status: **401**

```json
{
  "detail": "invalid or missing API key"
}
```

### POST /ask (có API key)

HTTP status: **200**

```json
{
  "answer": "Ngắn gọn: Deploy la gi phụ thuộc vào ba yếu tố — cấu hình qua biến môi trường, health check để orchestrator biết trạng thái, và giới hạn tài nguyên.",
  "user_id": "cp5-evidence-413dcdad4f",
  "history_length": 0,
  "cost_usd": 2.265e-05,
  "tokens": {
    "in": 3,
    "out": 37
  }
}
```

### Rate limit — 15 request cùng user

```text
200 200 200 200 200 200 200 200 200 200 429 429 429 429 429
```

## Kết Quả Test CP5

Chạy bộ test gốc với `LOCAL_FALLBACK=false` và `DEPLOY_API_KEY` được truyền
riêng vào tiến trình, không sửa `.env` hoặc test:

```text
9 passed, 4 skipped in 2.86s
```

Cả 9 kiểm tra tài liệu/cloud đều đạt, gồm `/ask` có khóa thật. Bốn test bỏ
qua chỉ dành cho local fallback, không áp dụng cho bản deploy cloud này.
Lần chạy trước có 8 passed, 1 failed, 4 skipped: `/health` gặp
`RemoteProtocolError: Server disconnected without sending a response`.
Chạy lại nguyên bộ test đạt; nguyên nhân ngắt kết nối chưa được xác định.

## Ảnh Chụp Màn Hình

Ba ảnh gốc đã được kiểm tra và chép nguyên vẹn từ Downloads vào repository:

- [x] [screenshots/dashboard.png](screenshots/dashboard.png) — dashboard Render với URL, commit `2def526` và trạng thái Live.
- [x] [screenshots/health.png](screenshots/health.png) — URL HTTPS `/health` và JSON `status: ok`.
- [x] [screenshots/logs.png](screenshots/logs.png) — log runtime với `/health` trả 200 (bổ sung).

Test cloud thành công không thay thế yêu cầu nộp file ảnh thật. Không đưa
API key, token hoặc chuỗi kết nối Redis có mật khẩu vào ảnh.
