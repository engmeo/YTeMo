# Companion Persistence — Status

**Trạng thái: CODE INTEGRATION PREPARED — NOT YET DEPLOYED/VERIFIED AGAINST LIVE SUPABASE**

- Supabase schema migration was reported as applied by the project owner.
- Added Supabase-backed repository adapters for Companion Core and Proactive proposals.
- Added authenticated FastAPI endpoints for consent, context, needs, follow-up and proposals.
- All repository reads/writes explicitly scope by authenticated `user_id`.
- Database enum values are mapped between Python lowercase enums and SQL uppercase CHECK values.
- Context deletion uses a soft-delete timestamp.
- Proactive Engine creates suggestions only; no external notifications/actions.

Validation in this package:
- Python syntax compilation passed.
- Companion + Proactive + repository unit tests: 33/33 passed (repository uses a fake DB).
- Live Supabase integration, frontend integration, deployment, live multi-request concurrency,
  retention/deletion policy, and independent security review remain unverified.

Do not describe this as production-ready or clinically validated.


## Cập nhật an toàn repository (bản sửa)
- Repository chỉ upsert các bản ghi thay đổi so với snapshot vừa đọc trong request.
- Xóa context chỉ đánh dấu xóa các ID đã có trong snapshot và bị loại khỏi state; không quét/xóa toàn bộ context của người dùng.
- CORS cho phép GET/POST/PUT/PATCH/DELETE/OPTIONS.
- Đã thêm unit test riêng cho repository dùng DB giả; đây không thay thế kiểm thử Supabase thật.
- Lưu ý: các thao tác ghi gồm nhiều lệnh PostgREST riêng lẻ, chưa phải transaction xuyên nhiều bảng. Với cập nhật đồng thời cùng một bản ghi, quy tắc hiện tại là lần ghi cuối cùng thắng. Cần RPC/transaction và kiểm thử tải trước khi dùng quy mô nhiều worker.
