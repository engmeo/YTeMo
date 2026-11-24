# Hướng dẫn migration Supabase cho Y TẾ MỞ

## Project đã kiểm tra

Project beta đang dùng: y-te-mo-beta (ref vmueimzrwhtvjyjydbzj). Không áp dụng các thay đổi này vào project khác.

Schema nền Companion/Memory và Core đã tồn tại từ trước, nhưng remote migration history không phản ánh đầy đủ schema đó. Vì vậy không chạy supabase db push hàng loạt. Đã đối chiếu dependency và áp dụng có chọn lọc các migration bên dưới.

## Các migration đã áp dụng thành công trên y-te-mo-beta

1. 202611240002_healthcare_document_storage — tạo healthcare_documents và private Storage bucket healthcare-documents.
2. 202611240010_healthcare_analysis_history — tạo healthcare_analysis_runs, FK tới healthcare_documents.
3. 202611240011_companion_action_tasks — tạo queue, retry/lease, RPC claim, unique action_task_id cho companion_needs và companion_events.
4. 202611240012_lockdown_rls_auto_enable — thu hồi EXECUTE trên rls_auto_enable khỏi public/anon/authenticated.
5. 202611240013_healthcare_document_service_grants — cấp quyền metadata cho service_role để backend đọc/ghi/xóa hồ sơ.
6. 202611240014_fix_action_claim_batch_bound — sửa biểu thức giới hạn batch của RPC claim; đã gọi RPC smoke test thành công, trả 0 row do queue trống.

Migration nền 202611180001_companion_persistence.sql có hai bảng companion_needs và companion_events đã tồn tại; prerequisite đã được xác minh trước khi áp dụng migration 011.

## Xác minh sau áp dụng

- healthcare_documents, healthcare_analysis_runs, companion_action_tasks tồn tại và RLS bật.
- Bucket healthcare-documents tồn tại, private, giới hạn 10 MB.
- claim_companion_action_tasks có chữ ký (p_now timestamptz, p_limit integer, p_action_types text[]), chỉ service_role được EXECUTE; smoke test trả về 0 row như mong đợi khi queue trống.
- anon/authenticated không có SELECT trên ba bảng mới; service_role có SELECT/INSERT/DELETE.
- rls_auto_enable không còn EXECUTE cho anon/authenticated.

## Migration history và CLI

Tool apply migration đã ghi lịch sử tên migration với version timestamp do Supabase sinh. Trước khi chạy CLI db push trong tương lai, cần chạy supabase migration list và đồng bộ local migration history tương ứng. Không sửa/xóa remote history để che schema drift.

```powershell
supabase login
supabase link --project-ref vmueimzrwhtvjyjydbzj
supabase migration list
```

Không chạy lại các migration đã áp dụng. Các migration Clinical Knowledge 003–009 chưa được áp dụng trong lượt này; cần kiểm tra dependencies và kế hoạch triển khai riêng trước khi bật các chức năng đó.

## Vận hành

- Backend và worker phải trỏ cùng Supabase project.
- Backend/worker dùng SUPABASE_SECRET_KEY; tuyệt đối không đưa secret key vào frontend.
- Worker cần SUPABASE_URL và SUPABASE_SECRET_KEY; email cần thêm RESEND_API_KEY và RESEND_FROM_EMAIL.
- Kiểm thử bằng tài khoản test và hồ sơ giả lập; không dùng hồ sơ sức khỏe thật để smoke test.