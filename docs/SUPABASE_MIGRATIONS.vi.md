# Hướng dẫn migration Supabase cho Y TẾ MỞ

## Project được kiểm tra

Trong kết nối hiện tại có project y-te-mo-beta (ref vmueimzrwhtvjyjydbzj) với các bảng Companion/Memory đã tồn tại. Kiểm tra schema cho thấy healthcare_documents, bucket healthcare-documents, healthcare_analysis_runs và companion_action_tasks chưa tồn tại. Không áp dụng thay đổi vào project khác.

Migration history của project trả về rỗng dù một số bảng nền đã tồn tại; vì vậy không chạy supabase db push hàng loạt trước khi đối chiếu lịch sử. Chỉ áp dụng các migration còn thiếu đã kiểm tra bên dưới.

## Thứ tự phụ thuộc

1. 202611240002_healthcare_document_storage.sql — tạo bảng metadata hồ sơ y tế và private Storage bucket healthcare-documents.
2. 202611240010_healthcare_analysis_history.sql — tạo lịch sử phân tích; FK tham chiếu healthcare_documents từ migration 002.
3. 202611240011_companion_action_tasks.sql — tạo action queue, retry/lease fields, RPC claim; bổ sung unique action_task_id vào companion_needs và companion_events.

Migration nền 202611180001_companion_persistence.sql phải có hai bảng companion_needs và companion_events trước khi chạy migration 011. Hai bảng này đã được xác nhận tồn tại trên project beta.

## Đã thực hiện

Chưa áp dụng migration nào trong lần kiểm tra này. Đây là tài liệu và kế hoạch an toàn; thay đổi DB chỉ chạy sau khi xác nhận đúng project và dependency state.

## Quy trình CLI

```powershell
supabase login
supabase link --project-ref vmueimzrwhtvjyjydbzj
supabase migration list
```

Do remote migration history đang trống nhưng schema nền đã có sẵn, không chạy supabase db push ngay. Đối chiếu từng file với schema thực tế và đồng bộ migration history trước khi dùng CLI để triển khai tiếp.

## Áp dụng từng migration bằng SQL Editor

Mở Supabase Dashboard của đúng project y-te-mo-beta → SQL Editor. Chạy tuần tự từng file, kiểm tra kết quả sau mỗi file:

1. supabase/migrations/202611240002_healthcare_document_storage.sql
2. supabase/migrations/202611240010_healthcare_analysis_history.sql
3. supabase/migrations/202611240011_companion_action_tasks.sql

Không chạy song song. Không chạy file nếu bảng prerequisite không tồn tại hoặc nếu bảng đã tồn tại với schema khác. Không chạy các file 003–009 trong cùng lượt này.

## SQL xác minh

```sql
select table_name
from information_schema.tables
where table_schema = 'public'
  and table_name in ('healthcare_documents','healthcare_analysis_runs','companion_action_tasks','companion_needs','companion_events')
order by table_name;

select id, name, public, file_size_limit
from storage.buckets where id = 'healthcare-documents';

select routine_name, specific_name
from information_schema.routines
where routine_schema = 'public' and routine_name = 'claim_companion_action_tasks';

select c.relname, c.relrowsecurity
from pg_class c join pg_namespace n on n.oid = c.relnamespace
where n.nspname = 'public'
  and c.relname in ('healthcare_documents','healthcare_analysis_runs','companion_action_tasks')
order by c.relname;

select table_name, column_name, data_type
from information_schema.columns
where table_schema = 'public'
  and table_name in ('companion_needs','companion_events')
  and column_name = 'action_task_id';
```

Kết quả mong đợi: ba bảng tồn tại và RLS bật; bucket private (public=false); RPC tồn tại; hai bảng Companion có cột action_task_id.

## Vận hành sau migration

- Backend và worker phải trỏ cùng Supabase project.
- Backend sử dụng SUPABASE_SECRET_KEY; không đưa secret key vào frontend.
- Worker cần SUPABASE_URL và SUPABASE_SECRET_KEY; email cần thêm RESEND_API_KEY và RESEND_FROM_EMAIL.
- Kiểm thử bằng tài khoản test và hồ sơ giả lập; không dùng hồ sơ sức khỏe thật để smoke test.