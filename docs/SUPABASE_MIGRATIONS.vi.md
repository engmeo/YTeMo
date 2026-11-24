# Hướng dẫn áp dụng migration Supabase cho prototype

## Các migration mới trong PR #5

Chạy theo thứ tự version:

1. `202611240010_healthcare_analysis_history.sql`
   - Tạo bảng lưu kết quả phân tích sức khỏe theo user.
   - Chỉ backend dùng `SUPABASE_SECRET_KEY` được truy cập; RLS bật, browser roles bị revoke.
   - Kết quả chỉ được lưu khi người dùng bật lựa chọn lưu lịch sử ở frontend.

2. `202611240011_companion_action_tasks.sql`
   - Tạo bảng đề xuất/tác vụ Companion có owner scope, approval và idempotency.
   - Tạo RPC claim worker có khóa hàng và điều kiện `scheduled_at <= p_now`.
   - Chỉ service role được truy cập bảng/RPC.

Migration `202611240009_clinical_evidence_intelligence.sql` đã tồn tại trước phần thay đổi này. Không chạy lại migration đã có trong remote history. Bảng `healthcare_documents` phải tồn tại trước khi chạy migration 010 vì migration này tạo foreign key tới bảng đó.

## Cách khuyến nghị: Supabase CLI

Chạy từ thư mục gốc repository trong PowerShell hoặc terminal:

```powershell
supabase login
supabase link --project-ref <PROJECT_REF>
supabase migration list
supabase db push
supabase migration list
```

- Đăng nhập bằng tài khoản có quyền quản trị project.
- Kiểm tra migration list trước khi push; chỉ áp dụng các version chưa có trong remote history.
- Không chia sẻ hoặc commit access token, database password hay service-role/secret key.
- Nếu CLI báo migration history không khớp, dừng lại và đối chiếu trước; không tự ý xóa record lịch sử migration.

## Nếu bắt buộc dùng Dashboard SQL Editor

1. Mở đúng Supabase project → SQL Editor.
2. Mở file `supabase/migrations/202611240010_healthcare_analysis_history.sql`, chạy toàn bộ một lần.
3. Chạy tiếp toàn bộ file `supabase/migrations/202611240011_companion_action_tasks.sql`.
4. Kiểm tra hai bảng và RPC đã tồn tại.
5. Đồng bộ migration history với Supabase CLI trước lần `supabase db push` tiếp theo; chạy `supabase migration repair --status applied 202611240010` và `supabase migration repair --status applied 202611240011` chỉ sau khi xác nhận SQL đã chạy thành công.

Không chạy file 010 và 011 đồng thời trong hai SQL Editor session.

## SQL kiểm tra sau triển khai

```sql
select table_name
from information_schema.tables
where table_schema = 'public'
  and table_name in ('healthcare_analysis_runs', 'companion_action_tasks')
order by table_name;

select routine_name
from information_schema.routines
where routine_schema = 'public'
  and routine_name = 'claim_companion_action_tasks';

select c.relname, c.relrowsecurity
from pg_class c
join pg_namespace n on n.oid = c.relnamespace
where n.nspname = 'public'
  and c.relname in ('healthcare_analysis_runs', 'companion_action_tasks')
order by c.relname;
```

Kết quả mong đợi: hai bảng tồn tại, RPC tồn tại và `relrowsecurity = true` cho cả hai bảng.

## Sau migration

- Deploy backend mới để bật các API lịch sử và action.
- Chỉ deploy worker riêng sau khi cấu hình `SUPABASE_URL`, `SUPABASE_SECRET_KEY`, `RESEND_API_KEY`, `RESEND_FROM_EMAIL`.
- Không đặt secret key ở Vercel frontend hoặc gửi xuống trình duyệt.
- Kiểm thử bằng tài khoản test riêng; không dùng hồ sơ sức khỏe thật để smoke test.
