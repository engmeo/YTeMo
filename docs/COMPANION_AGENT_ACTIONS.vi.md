# Companion Agent Actions & Temporal Runtime

## Năng lực đã triển khai

- Allowlist action; LLM chỉ đề xuất, không tự thực thi.
- Chủ tài khoản phải phê duyệt trước khi action được đưa vào queue.
- API đọc/ghi có owner scope; idempotency key theo nội dung đề xuất.
- Worker riêng, atomic claim bằng FOR UPDATE SKIP LOCKED, chỉ claim action type đã đăng ký.
- Lease 3 phút, thu hồi task bị worker chết, retry có backoff 15 giây đến tối đa 1 giờ, giới hạn 5 lần.
- Lease fencing ngăn worker cũ ghi đè kết quả sau khi task đã được worker khác nhận.
- Email Resend dùng idempotency key theo task ID.

## API

Tất cả endpoint yêu cầu Supabase access token:
- POST /companion/actions/propose
- GET /companion/actions
- POST /companion/actions/{action_id}/approve
- POST /companion/actions/{action_id}/reject

Ví dụ tạo reminder (frontend gửi consent boolean từ checkbox):

```json
{
  "action": "create_reminder",
  "arguments": {
    "title": "Tái khám",
    "due_at": "2026-12-01T09:00:00+07:00",
    "delivery_channel": "email",
    "email_consent": true
  }
}
```

Backend xác thực email_consent=true, tự ghi timestamp consent, yêu cầu due_at có timezone và nằm trong tương lai. Recipient không nhận từ request/LLM; worker chỉ gửi tới email Supabase Auth đã xác minh.

## Ba handler đã đăng ký

1. create_reminder: gửi email qua Resend nếu RESEND_API_KEY và RESEND_FROM_EMAIL tồn tại. Nếu chưa cấu hình, worker vẫn chạy các handler khác và không claim reminder.
2. request_clinician_review: tạo nhu cầu review ưu tiên cao trong companion_needs; đây là yêu cầu nội bộ chờ nhân viên y tế tiếp nhận, chưa tự gửi thông báo tới bệnh viện/bác sĩ.
3. add_timeline_note: ghi sự kiện vào companion_events, lưu cả nội dung và nguồn do người dùng cung cấp.

Hai handler nội bộ dùng unique action_task_id để retry không tạo bản ghi trùng. Chúng không thay thế hồ sơ bệnh án đã xác minh.

## Migration prerequisites

- 202611180001_companion_persistence.sql phải được áp dụng trước vì tạo companion_needs và companion_events.
- 202611240011_companion_action_tasks.sql tạo action queue, retry/lease fields, unique effect references và RPC claim.
- Xem docs/SUPABASE_MIGRATIONS.vi.md để áp dụng theo thứ tự và kiểm tra schema.
- Worker và backend phải trỏ tới cùng một Supabase project.

## Vận hành worker

Trong môi trường worker riêng, cấu hình:
- Bắt buộc: SUPABASE_URL, SUPABASE_SECRET_KEY.
- Để gửi email: RESEND_API_KEY, RESEND_FROM_EMAIL.
- Tùy chọn: YTEMO_ACTION_POLL_SECONDS (mặc định 5 giây).

Chạy từ thư mục backend:

```bash
python companion_action_worker_service.py
```

Có thể chạy nhiều worker; database lease/skip-locked bảo vệ việc claim đồng thời. Bắt đầu với một worker để theo dõi log, sau đó tăng số lượng khi đã có giám sát. Không chạy trong FastAPI request hoặc Vercel Function.

## An toàn và giới hạn

- Không có SMS, đặt lịch bệnh viện, kê đơn, thay đổi thuốc hay chỉ định cận lâm sàng.
- Email chỉ gửi sau khi người dùng chọn email, xác nhận consent, phê duyệt action và tài khoản có email đã xác minh.
- Resend idempotency bảo vệ retry trong khoảng thời gian provider lưu key; worker lease và DB uniqueness bổ sung bảo vệ nội bộ.
- Request clinician review chỉ tạo yêu cầu nội bộ, chưa có tích hợp clinician inbox/paging.
- Không coi worker thành công hoặc test pass là xác nhận lâm sàng.