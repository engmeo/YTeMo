# Y TẾ MỞ — Companion Persistence Integration

## Phạm vi

Bản tích hợp này nối `CompanionCore` và `ProactiveEngine` hiện có với 5 bảng Supabase:
- `companion_consents`
- `companion_context`
- `companion_needs`
- `companion_events`
- `proactive_proposals`

Tệp mới: `backend/supabase_companion_repository.py`.

`main.py` khởi tạo hai repository Supabase và cung cấp API có xác thực. Mọi `user_id`
được lấy từ `get_current_user()` sau khi kiểm tra access token; API không nhận
`user_id` từ request body. Repository cũng lọc `user_id` trong mọi truy vấn.

## API

Tất cả endpoint dưới đây yêu cầu `Authorization: Bearer <Supabase access token>`.

| Method | Endpoint | Mục đích |
|---|---|---|
| POST | `/companion/initialize` | Khởi tạo trạng thái, không tự cấp consent |
| GET | `/companion` | Snapshot |
| PUT | `/companion/consent` | Cấp/thu hồi một phạm vi consent |
| POST | `/companion/context` | Lưu ngữ cảnh theo consent |
| GET | `/companion/context` | Đọc ngữ cảnh còn consent |
| DELETE | `/companion/context/{context_id}` | Đánh dấu xóa ngữ cảnh |
| POST | `/companion/needs` | Tạo nhu cầu hỗ trợ |
| GET | `/companion/needs` | Liệt kê nhu cầu |
| PATCH | `/companion/needs/{need_id}` | Cập nhật trạng thái/bước tiếp theo |
| POST | `/companion/follow-up` | Ghi sự kiện theo dõi |
| POST | `/companion/proactive/evaluate` | Đánh giá một sự kiện và tạo đề xuất |
| GET | `/companion/proactive/proposals` | Liệt kê đề xuất |
| PATCH | `/companion/proactive/proposals/{proposal_id}` | Chấp nhận/từ chối/cập nhật đề xuất |

Các giá trị enum trong API dùng chữ thường như `health_context`, `in_progress`,
`proposed`. Repository chuyển đổi sang chữ hoa theo CHECK constraint trong migration.

## Bảo vệ dữ liệu

- Backend dùng `SUPABASE_SECRET_KEY`; khóa này bypass RLS.
- Vì vậy mọi truy vấn repository đều phải có điều kiện `user_id` lấy từ token đã xác thực.
- Consent được kiểm tra trong `CompanionCore` trước khi đọc/ghi dữ liệu tương ứng.
- Thu hồi consent làm dữ liệu context không còn được trả về; không đồng nghĩa xóa vật lý.
- Xóa context sử dụng `deleted_at` (soft delete).
- Proactive Engine chỉ tạo đề xuất; không gửi email/SMS/push và không tự thực hiện hành động.
- Đây chưa phải hệ thống hồ sơ bệnh án, chưa có clinical validation hay đánh giá bảo mật độc lập.

## Cách cập nhật mã

1. Sao lưu thư mục backend hiện tại.
2. Chép các tệp trong gói vào đúng vị trí repo:
   - `backend/main.py` ghi đè `backend/main.py`
   - `backend/supabase_companion_repository.py` là tệp mới
   - giữ nguyên các tệp core/test hiện tại nếu không có thay đổi tương ứng trong gói.
3. Đảm bảo biến môi trường backend có `SUPABASE_URL`, `SUPABASE_PUBLISHABLE_KEY`,
   `SUPABASE_SECRET_KEY`. Không đưa secret key lên frontend/GitHub.
4. Cài requirements hiện tại (không cần thêm thư viện mới).
5. Chạy test core và kiểm tra cú pháp.
6. Khởi động backend, đăng nhập lấy access token rồi kiểm tra API theo thứ tự:
   initialize → grant consent → create need/context → list → revoke consent → verify context is hidden.
7. Chỉ sau khi kiểm thử trên Supabase đúng project mới triển khai.

## Kiểm thử đã thực hiện khi đóng gói

- `py_compile`: `main.py`, `companion_core.py`, `proactive_engine.py`,
  `supabase_companion_repository.py` — đạt.
- Unit tests hiện có: 28/28 đạt (Companion Core + Proactive Engine).
- Chưa chạy kiểm thử tích hợp với project Supabase thật trong môi trường đóng gói.


## Bản sửa an toàn
Repository đã bỏ thao tác quét toàn bộ context để soft-delete. Nó chỉ ghi các hàng thay đổi so với snapshot vừa đọc và chỉ soft-delete ID bị loại khỏi snapshot đó. CORS đã bổ sung PUT/PATCH/DELETE/OPTIONS. Có thêm `test_supabase_companion_repository.py` với DB giả; tổng cộng 33/33 unit test đạt trong môi trường đóng gói. Đây vẫn là adapter nhiều lệnh PostgREST, không phải transaction đa bảng; chưa tuyên bố an toàn cho concurrent write cùng bản ghi hoặc triển khai nhiều worker.
