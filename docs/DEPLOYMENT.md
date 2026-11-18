# Kế hoạch triển khai Y TẾ MỞ

## Frontend

- Dự kiến: Vercel.
- Root Directory: `frontend`.
- Entry: `index.html`.
- Cần thay API localhost bằng địa chỉ HTTPS của Backend trước khi
  bật website cho người dùng bên ngoài.

## Backend

- Dự kiến: Render Web Service.
- Root Directory: `backend`.
- Build Command: `pip install -r requirements.txt`
- Start Command: `uvicorn main:app --host 0.0.0.0 --port $PORT`

## Secrets

Cấu hình secrets trong phần Environment Variables của nhà cung cấp.
Không commit file `.env` hoặc giá trị bí mật vào GitHub.

## Trạng thái

Chưa triển khai. Cần audit mã nguồn, kiểm thử, xác nhận CORS,
xác nhận cấu hình Supabase và kiểm tra API trước khi public.
