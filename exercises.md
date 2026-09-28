# Phiếu Phản Ánh — K4 Level 3A, Ngày 12

> **Bài làm cá nhân.** Trả lời bằng lời của chính bạn, dựa trên những gì bạn
> quan sát được khi chạy code — không sao chép đáp án của người khác.
>
> Cách trả lời: thay dòng đánh dấu bên dưới mỗi câu hỏi bằng câu trả lời.
> `grade.py` đếm số câu đã trả lời (15 điểm cho 10 câu).
>
> Họ và tên: Bui Dinh De (không dấu theo tên repository) — Mã học viên: 2A202602818

---

### Câu 1 — Fail fast (CP1)

Trong `Settings`, `agent_api_key` không có giá trị mặc định nên app chết ngay
khi khởi động nếu thiếu biến môi trường. Hãy mô tả một tình huống cụ thể mà
việc "chết sớm" này cứu bạn, so với việc để mặc định `"changeme"`.

Một tình huống cụ thể là deploy lên cloud nhưng quên khai báo
`AGENT_API_KEY`. Nếu code dùng mặc định `"changeme"`, ứng dụng vẫn khởi động;
khi lớp xác thực được triển khai, người biết khóa mặc định có thể gọi API
và tiêu tốn tài nguyên hoặc chi phí LLM ngoài ý muốn của chủ service.

Với `agent_api_key: str` không có mặc định, `get_settings()` được gọi trong
startup sẽ gây `ValidationError` nếu cả environment và `.env` đều không
cung cấp khóa. Service dừng trước khi nhận request, giúp phát hiện thiếu
cấu hình ngay lúc deploy thay vì để lỗi bảo mật tồn tại âm thầm.

Kiểm chứng ở CP1: chạy Uvicorn trong môi trường thử không có `.env` và đã
bỏ biến `AGENT_API_KEY` khiến startup bị từ chối với lỗi `Field required`
cho `agent_api_key`. Đây là lỗi cấu hình có chủ đích, không phải thiếu thư viện.
Fail fast không tự bảo đảm khóa mạnh; vẫn phải tạo khóa riêng và giữ bí mật.

---

### Câu 2 — Log cho máy đọc (CP1)

Chạy service và gọi `/ask` vài lần. Dán một dòng log JSON bạn thu được, rồi
nêu **hai** việc bạn làm được với dòng log đó mà `print("đã trả lời xong")`
không làm được.

Đã gọi `/ask` ba lần với cùng user trên service Docker local tại
`http://localhost:8001`, cả ba lần trả HTTP 200. Dòng dưới đây lấy nguyên
vẹn từ stdout của container bằng `docker compose logs --no-log-prefix agent`;
đây là log thực tế của app dùng mock LLM, không phải log ví dụ được tự tạo:

```json
{"user_id": "reflection-cp1-3f1a8c65", "tokens_in": 4, "tokens_out": 36, "cost_usd": 2.22e-05, "event": "ask_completed", "level": "info", "timestamp": "2026-09-28T11:25:14.562253+00:00"}
```

Với log `ask_completed` có các trường theo thiết kế trong `app/main.py`,
có thể làm hai việc:

1. Lọc theo `user_id` và cộng `cost_usd` qua nhiều sự kiện để biết từng user
   đã tiêu bao nhiêu, từ đó phát hiện người dùng có chi phí bất thường.
2. Lọc theo khoảng thời gian của `timestamp` và cộng `tokens_in`,
   `tokens_out` để theo dõi mức sử dụng token theo thời gian, tìm thời điểm
   lượng sử dụng tăng cao.

Chuỗi `print("đã trả lời xong")` không chứa user, thời gian, token hoặc
chi phí nên không cung cấp dữ liệu cho hai phép thống kê trên. JSON có
các trường rõ ràng và giữ giá trị số để chương trình đọc, lọc và cộng;
mỗi sự kiện nằm trên một dòng giúp hệ thống thu thập log xử lý đúng ranh giới.

---

### Câu 3 — Kích thước image (CP2)

Build cả hai phiên bản và ghi lại số đo thật:

```bash
docker build -f <Dockerfile-1-stage> -t agent:single .
docker build -t agent:multi .
docker images | grep agent
```

| Bản | Dung lượng |
|-----|-----------|
| 1 stage (bản đầu) | 1.727,64 MB (`day12-agent:single`) |
| Multi-stage | 270,94 MB (`day12-agent:prod`) |

Giải thích: phần dung lượng chênh lệch đó là những gì?

Hai image đã build thành công. Đo bằng `docker image inspect --format
'{{.Size}}' <image>` cho kết quả single-stage là **1,727,642,638 byte** và
multi-stage là **270,937,145 byte**. Bảng dùng MB thập phân (1 MB = 1.000.000
byte); đây là dung lượng image Docker báo, không phải dung lượng tải nén.
`docker images` hiển thị làm tròn tương ứng **1.73GB** và **271MB**.

Bản mới giảm khoảng **1.456,71 MB**, tương đương
**84,32%**, và đạt yêu cầu dưới 500MB.

Phần dung lượng khác biệt đến từ các yếu tố:

- Bản gốc dùng `python:3.11` đầy đủ, chứa nhiều công cụ và thư viện hệ
  thống hơn `python:3.11-slim` của bản mới.
- Bản gốc cài dependencies ngay trong image cuối bằng `pip install` mặc
  định. Bản mới dùng `--no-cache-dir` và chỉ copy kết quả cài đặt từ
  `/install` sang runtime, tránh mang cache tải package vào image cuối.
- Runtime chỉ nhận source cần thiết (`app/`, `utils/`) và dependencies;
  các công cụ chỉ có trong builder không tự động đi sang runtime. Lần
  build này không cài thêm `build-essential`, nên không quy mức giảm cho
  việc loại một gói compiler được cài thêm như trong ví dụ của guide.

Vì vậy mức giảm là kết quả của base image gọn hơn và nội dung được giữ
lại, không chỉ do thêm lệnh `FROM`. Bản mới vẫn cài toàn bộ
`requirements.txt`, bao gồm dependencies phục vụ test.

Để đo an toàn, Dockerfile single-stage gốc được build trong context tạm
chỉ chứa `Dockerfile`, `requirements.txt`, `app/`, `utils/`, không có
`.env`, `.venv` hay Git. Không tính secret hoặc môi trường ảo của máy vào
phép so sánh. Log build thực tế được lưu tại `/tmp/cp2-single-final.log`.

---

### Câu 4 — Thứ tự lệnh trong Dockerfile (CP2)

Sửa một ký tự trong `app/main.py` rồi build lại. Với Dockerfile của bạn, những
layer nào được dùng lại từ cache, layer nào phải chạy lại? Nếu bạn đặt
`COPY . .` lên trước `RUN pip install` thì kết quả khác thế nào?

Trong lần kiểm chứng CP2, source `app/main.py` được thay đổi bằng cách thêm
một comment trong context tạm, không sửa file bài làm đang chạy. Log build
thực tế ghi bước `RUN pip install --no-cache-dir --prefix=/install -r
requirements.txt` là `CACHED`, còn `COPY app ./app` chạy lại (`DONE 0.1s`).

Nguyên nhân là `requirements.txt` không đổi và được copy trước source,
nên Docker dùng lại kết quả cài dependencies của stage builder. Các bước
runtime trước `COPY app` cũng có thể dùng cache khi đầu vào không đổi;
bước copy source thay đổi và các bước phía sau phải được Docker xử lý lại.
Không phải mọi bước xử lý lại đều chậm như cài thư viện.

Nếu đặt `COPY . .` trước `RUN pip install`, thay đổi source sẽ làm thay đổi
layer đầu vào của bước cài thư viện. Docker phải chạy lại `pip install` dù
`requirements.txt` không đổi, làm build chậm và có thể phải tải lại packages.
Vì vậy tách dependency ra khỏi source giúp lần build sau chỉ làm lại phần
thực sự thay đổi.

---

### Câu 5 — Vì sao không chạy bằng root (CP2)

Container mặc định chạy bằng root. Mô tả chuỗi sự kiện dẫn từ "một lỗ hổng
trong code Python của bạn" tới "kẻ tấn công có quyền cao trên máy host", và
lệnh `USER` cắt đứt chuỗi đó ở chỗ nào.

Ví dụ ứng dụng có lỗ hổng cho phép thực thi lệnh: kẻ tấn công có thể chạy
lệnh với quyền của tiến trình Python. Nếu app chạy bằng root, họ có quyền
cao trong container, dễ sửa các file thuộc root và tác động tới tài nguyên
được cấp cho container.

Để tiếp tục có quyền cao trên host còn cần điều kiện khác, chẳng hạn lỗi
thoát container/kernel hoặc cấu hình nguy hiểm như mount Docker socket,
mount thư mục nhạy cảm của host hay chạy privileged. Root trong container
không tự động đồng nghĩa với quyền root trên host; đây là chuỗi rủi ro có
điều kiện, không phải cứ khai thác app là chiếm được máy host.

Dockerfile hiện tạo `appuser` có UID 10001 và đặt `USER appuser` trước khi
chạy Uvicorn. Kiểm tra container thực tế đã trả UID 10001. Nếu app bị khai
thác, lệnh của kẻ tấn công ban đầu chạy với quyền user thường thay vì root,
giảm khả năng sửa file hệ thống và hạn chế phạm vi thiệt hại.

`USER` giảm đặc quyền ngay tại bước thực thi code bị khai thác; nó không
sửa lỗ hổng ứng dụng hoặc bảo đảm chặn mọi cách leo thang quyền. Vẫn cần
cập nhật phần mềm và tránh cấp quyền hoặc mount không cần thiết.

---

### Câu 6 — Cửa sổ trượt (CP3)

Rate limit của bạn dùng sliding window 60 giây. Nếu thay bằng cách đếm theo
phút đồng hồ (reset lúc giây 00), một người dùng có thể gửi tối đa bao nhiêu
request trong 2 giây liên tiếp khi hạn mức là 10/phút? Giải thích cách đạt được
con số đó.

Với bộ đếm reset theo phút đồng hồ, một user có thể gửi tối đa **20
request trong khoảng 2 giây đi qua ranh giới hai phút**, giả sử không có
cơ chế giới hạn nào khác:

- Gửi 10 request trong giây `10:00:59`, dùng hết hạn mức của phút 10:00.
- Đến `10:01:00`, bộ đếm reset; gửi thêm 10 request trong giây này, dùng
  hạn mức của phút 10:01.

Mỗi phút vẫn chỉ có 10 request, nhưng hai nhóm nằm sát nhau nên hệ thống
nhận 20 request trong khoảng thời gian rất ngắn. Đây là điểm yếu ở ranh
giới của cửa sổ cố định.

Sliding window xét 60 giây gần nhất tại mỗi lần gọi, không reset chỉ vì
đồng hồ sang phút mới. Khi nhóm thứ hai đến, 10 request ở `10:00:59` vẫn
nằm trong cửa sổ nên request tiếp theo bị chặn với HTTP 429. Chỉ khi các
request cũ ra khỏi cửa sổ mới có quota trở lại. Trong thuật toán của lab,
entry có timestamp nhỏ hơn hoặc bằng `now - 60` được loại bỏ trước khi đếm.
Giải thích này áp dụng khi các thao tác kiểm tra được xử lý tuần tự; phiên
bản hiện tại chưa gộp kiểm tra và ghi nhận thành thao tác Redis nguyên tử
để bảo đảm giới hạn tuyệt đối khi nhiều request chạy đồng thời.

---

### Câu 7 — Rate limit và cost guard (CP3)

Hai cơ chế này khác nhau ở điểm nào? Cho một tình huống mà rate limit cho qua
nhưng cost guard phải chặn, và một tình huống ngược lại.

**Rate limit** giới hạn số request của mỗi user trong 60 giây gần nhất,
nhằm hạn chế gọi quá nhanh; vượt hạn mức trả HTTP **429**.
**Cost guard** kiểm tra chi phí tích lũy theo user/tháng UTC so với ngân
sách, nhằm hạn chế mức chi tiêu; vượt ngân sách trả HTTP **402**.

Hai tình huống minh họa, với hạn mức 10 request/phút và ngân sách 10 USD/tháng:

1. **Rate limit cho qua, cost guard chặn:** user chưa gọi request nào trong
   60 giây gần nhất nhưng tổng chi phí tháng đã là 10,01 USD. Request mới
   còn quota về số lượng, nhưng `guard.check()` thấy chi phí vượt 10 USD
   nên trả 402 trước khi gọi LLM.
2. **Rate limit chặn, ngân sách vẫn còn:** user đã gửi đủ 10 request trong
   60 giây, nhưng mới tiêu 0,01 USD trong tháng. Request thứ 11 bị trả 429,
   dù nếu kiểm tra riêng thì cost guard vẫn cho qua. Trong luồng `/ask`
   hiện tại, limiter chạy trước nên request này dừng ngay, không chạy đến
   cost guard hoặc LLM.

Hai cơ chế bổ sung cho nhau: ít request vẫn có thể đắt nếu dùng nhiều token;
nhiều request rẻ vẫn có thể gây tải lớn. Cần kiểm tra cả hai trước khi gọi
LLM và ghi chi phí thực tế bằng `guard.record()` sau khi có kết quả.

Lưu ý theo code hiện tại: điều kiện chặn là
`spent + estimated_cost > budget`, còn `/ask` gọi `check()` với ước tính
mặc định bằng 0. Vì vậy nó chặn khi chi phí đã vượt ngân sách, không bảo
đảm request kế tiếp không làm vượt trần. Đây là giới hạn của bài lab;
không nên mô tả cơ chế hiện tại như một hệ thống đặt trước ngân sách tuyệt đối.
Các số tiền trên là ví dụ minh họa, không phải hóa đơn thực tế; lab dùng
mock LLM nên không phát sinh phí từ nhà cung cấp.

---

### Câu 8 — /health khác /ready (CP4)

Nếu gộp hai endpoint làm một và cho nó kiểm tra Redis, chuyện gì xảy ra với cụm
3 container khi Redis mất kết nối 30 giây? Trả lời theo đúng thứ tự sự kiện.

Nếu một endpoint vừa làm liveness vừa làm readiness và gọi Redis, thứ tự
sự kiện có thể là:

1. Redis mất kết nối; cả ba container vẫn chạy nhưng endpoint chung trả
   lỗi do không truy cập được Redis.
2. Readiness thất bại khiến hệ thống điều phối hoặc load balancer đã được
   cấu hình dùng probe loại các instance khỏi luồng nhận request mới.
3. Nếu lỗi kéo dài đủ số lần kiểm tra thất bại của liveness, hệ thống điều
   phối có chính sách restart theo liveness sẽ khởi động lại các container,
   dù tiến trình ứng dụng không bị lỗi. Cả ba có thể bị restart gần nhau
   vì cùng phụ thuộc một Redis.
4. Restart app không sửa được Redis. Khi Redis vẫn mất kết nối, container
   mới tiếp tục báo lỗi; dịch vụ có thể bị gián đoạn và các request đang
   xử lý có nguy cơ thất bại.
5. Sau 30 giây, Redis phục hồi nhưng một số container có thể còn đang
   khởi động lại. Hệ thống phải chờ chúng sẵn sàng và probe thành công,
   nên thời gian gián đoạn có thể dài hơn thời gian Redis mất kết nối.

Restart không phải kết quả chắc chắn của mọi sự cố 30 giây: còn phụ thuộc
chu kỳ, timeout, ngưỡng thất bại và chính sách của platform. Docker Compose
với `HEALTHCHECK` đơn thuần chỉ đánh dấu `unhealthy`, không tự restart chỉ
vì trạng thái đó. Vì vậy cần phân biệt tín hiệu probe với hành động của
hệ thống sử dụng probe.

Cách tách hiện tại tránh restart process chỉ vì lỗi Redis: `/health`
không gọi Redis, còn `/ready` kiểm tra kết nối. Kiểm chứng CP4 trên môi
trường container tách riêng đã cho kết quả khi dừng Redis: `/health=200`,
`/ready=503`; khi bật Redis lại: `/ready=200`. Thử nghiệm này kiểm tra
mất kết nối/phục hồi, không đo một đợt gián đoạn đúng 30 giây.

---

### Câu 9 — Stateless (CP4)

Chạy `docker compose up --scale agent=3` rồi gọi `/ask` nhiều lần với cùng một
`X-User-Id`. Quan sát `history_length` trong response. Nếu lịch sử được lưu
trong một dict Python thay vì Redis, bạn sẽ thấy con số đó thay đổi thế nào?

Trong kiểm chứng CP4, ba container agent riêng biệt kết nối cùng một
Redis và nhận request luân phiên với cùng user `cp4-shared`. Thử nghiệm
dùng các cổng host được Docker cấp động để tránh xung đột; không chạy
nguyên lệnh scale trong đề với cấu hình mỗi replica cùng publish một
host port cố định.

Kết quả `history_length` thực tế qua 12 request là:

```text
0, 2, 4, 6, 8, 10, 12, 14, 16, 18, 20, 20
```

Mỗi request đọc history trước khi thêm hai message mới: câu hỏi của user
và câu trả lời của assistant. Vì vậy lượt đầu trả 0, lượt kế tiếp thấy
2 message, rồi tăng thêm 2 dù request chuyển sang container khác. History
chỉ giữ 20 message mới nhất nên sau đó số lượng dừng ở 20. TTL đã đo là
604800 giây (7 ngày); restart một container vẫn đọc được history dùng chung.

Nếu mỗi process lưu history trong một dict Python riêng, container mới
nhận user sẽ không thấy các lượt đã xử lý ở container khác. Ví dụ, khi
luân phiên đều A → B → C từ trạng thái trống, kết quả có thể là:

```text
0, 0, 0, 2, 2, 2, 4, 4, 4, ...
```

Đây là ví dụ giả định, không phải số đo Redis ở trên. Nếu phân phối request
không đều, `history_length` có thể tăng rồi giảm khi chuyển sang container
có ít lịch sử hơn; restart process còn làm mất dict của process đó.

Do đó stateless nghĩa là instance ứng dụng không giữ history dùng chung
trong RAM của riêng mình: Redis giữ dữ liệu bên ngoài để các instance
đọc cùng một nguồn. Kết quả thực tế được ghi tại `/tmp/cp4-runtime-check.log`.

---

### Câu 10 — Deploy thật (CP5)

Ghi lại **một** lỗi bạn gặp khi deploy lên cloud (build fail, health check
timeout, sai REDIS_URL, app không đọc `$PORT`...): thông báo lỗi là gì, bạn
tìm ra nguyên nhân bằng cách nào, và sửa ra sao?

Sau khi Render báo service Live, mở URL gốc
`https://day12-agent-x6ug.onrender.com/` trên trình duyệt lại nhận:

```json
{"detail":"Not Found"}
```

Ban đầu phản hồi này dễ bị hiểu là deploy thất bại. Đối chiếu các route
trong `app/main.py` cho thấy app chỉ khai báo `/health`, `/ready` và `/ask`,
không có handler cho `/`. Vì vậy phản hồi 404 ở URL gốc là do truy cập
đường dẫn chưa được khai báo, không chứng minh process khởi động lỗi.

Cách xử lý là kiểm tra đúng endpoint: mở `/health` nhận HTTP 200 với
`status: ok`; gọi `/ready` nhận HTTP 200 với `redis: true`. Tiếp tục gọi
POST `/ask` không có khóa nhận 401, còn khóa hợp lệ nhận 200. Không cần
sửa Dockerfile, Redis URL hay thêm trang chủ chỉ để làm mất thông báo 404.
Ảnh dashboard và `/health` được lưu trong `screenshots/`, kết quả kiểm tra
được ghi trong `DEPLOYMENT.md`.

Qua sự cố này cần phân biệt ba lớp: process đang chạy, các dependency đã
sẵn sàng, và đường dẫn/phương thức HTTP đang gọi có đúng hay không. Dashboard
Live cùng `/health` 200 chưa đủ chứng minh `/ask` hoạt động; phải kiểm tra
cả readiness và request có xác thực.
