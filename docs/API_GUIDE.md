# Y TẾ MỞ — API Integration Guide

Tài liệu hướng dẫn nhà phát triển cài đặt, khởi chạy, khám phá và tích hợp Backend API của dự án Y TẾ MỞ.

> **Trạng thái:** Development / Local API.
> Chưa xác nhận có API Base URL public. GitHub repository chỉ lưu mã nguồn và tài liệu, không tự chạy Backend API.

---

## 1. Kiến trúc kết nối

```text
External Client / Frontend / Agent
              |
              | HTTP Request
              v
       Y TẾ MỞ FastAPI
              |
              v
       Backend Services
              |
              v
        Supabase Cloud
```

Phân biệt các thành phần:

- GitHub: lưu trữ source code và tài liệu.
- FastAPI: cung cấp các HTTP API endpoints.
- Supabase: dịch vụ dữ liệu và xác thực được Backend sử dụng.
- Swagger UI: giao diện khám phá và thử nghiệm API được FastAPI sinh tự động.

Supabase Cloud không đồng nghĩa với việc FastAPI Backend đã được triển khai lên Internet.

## 2. API Base URL

### Local development

Nếu Backend chạy trên máy của bạn tại cổng 8000:

```text
Base URL: http://127.0.0.1:8000
Swagger:  http://127.0.0.1:8000/docs
OpenAPI:  http://127.0.0.1:8000/openapi.json
Health:   http://127.0.0.1:8000/health
```

`127.0.0.1` chỉ truy cập được trên chính máy đang chạy Backend.

Người khác muốn thử API cần chạy Backend trên máy của họ, hoặc sử dụng một địa chỉ máy chủ đã được triển khai và cấp quyền truy cập.

### Production

Khi triển khai Backend lên máy chủ công khai, thay Base URL bằng địa chỉ HTTPS thực tế.

Ví dụ minh họa:

```text
https://api.example.com
```

Đây không phải địa chỉ production hiện tại của Y TẾ MỞ.

## 3. Cài đặt và khởi chạy Backend

### Yêu cầu

- Python tương thích với dependencies của dự án.
- Git.
- Một Supabase project có cấu hình phù hợp.
- File cấu hình môi trường `.env` theo yêu cầu của Backend.

### Clone repository

```powershell
git clone https://github.com/engmeo/YTe.git
cd YTe
```

### Cài dependencies

```powershell
cd backend
pip install -r requirements.txt
```

### Cấu hình môi trường

Tạo và cấu hình file:

```text
backend/.env
```

Điền các biến môi trường theo cấu hình mà source code yêu cầu.

**Lưu ý bảo mật:**

- Không commit `.env` lên GitHub.
- Không công khai Supabase service_role key.
- Không gửi secret key qua tài liệu API.
- Mỗi người tích hợp nên sử dụng credentials được cấp riêng.

### Khởi chạy

Tại thư mục `backend`:

```powershell
python -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

Sau khi server khởi chạy, mở:

```text
http://127.0.0.1:8000/docs
```

Swagger UI là nơi kiểm tra schema request, response, tham số và cơ chế xác thực được khai báo thực tế trong ứng dụng.

## 4. Endpoint inventory

Danh sách dưới đây được tổng hợp từ các route khai báo trong `backend/main.py` đã kiểm tra trong quá trình phát triển.

| Method | Endpoint | Chức năng |
|---|---|---|
| GET | `/` | Root endpoint |
| GET | `/health` | Kiểm tra tình trạng Backend |
| GET | `/public-config` | Lấy cấu hình công khai |
| GET | `/conversations/{conversation_id}/messages` | Lấy tin nhắn của conversation |
| POST | `/chat` | Gửi yêu cầu chat |
| POST | `/agent/tasks` | Tạo Agent task |
| GET | `/agent/tasks` | Liệt kê Agent tasks |
| GET | `/agent/tasks/{task_id}` | Lấy thông tin một task |
| POST | `/agent/tasks/{task_id}/resume` | Tiếp tục task |
| POST | `/companion/initialize` | Khởi tạo Companion |
| GET | `/companion` | Lấy thông tin Companion |
| PUT | `/companion/consent` | Cập nhật consent |
| POST | `/companion/context` | Gửi context |
| GET | `/companion/context` | Truy xuất context |
| DELETE | `/companion/context/{context_id}` | Xóa context |
| POST | `/companion/needs` | Tạo nhu cầu |
| GET | `/companion/needs` | Truy xuất nhu cầu |
| PATCH | `/companion/needs/{need_id}` | Cập nhật nhu cầu |
| POST | `/companion/follow-up` | Tạo follow-up |
| POST | `/companion/proactive/evaluate` | Đánh giá proactive support |
| GET | `/companion/proactive/proposals` | Lấy proactive proposals |
| PATCH | `/companion/proactive/proposals/{proposal_id}` | Cập nhật proposal |

> Đây là inventory các route đã quan sát trong `main.py`, chưa phải cam kết rằng toàn bộ API của hệ thống chỉ có các route này. Cần kiểm tra OpenAPI schema để xác nhận cả các router được đăng ký từ module khác.

## 5. Cách gọi API

Một HTTP request cơ bản có dạng:

```text
HTTP_METHOD + BASE_URL + ENDPOINT
```

Ví dụ:

```text
GET http://127.0.0.1:8000/health
```

### Ví dụ với PowerShell

```powershell
Invoke-RestMethod `
  -Uri "http://127.0.0.1:8000/health" `
  -Method GET
```

### Ví dụ với Python

```python
import requests

BASE_URL = "http://127.0.0.1:8000"

response = requests.get(
    f"{BASE_URL}/health",
    timeout=15
)

print(response.status_code)
print(response.json())
```

### Ví dụ với cURL

```bash
curl http://127.0.0.1:8000/health
```

Các ví dụ trên chỉ minh họa cách gọi endpoint GET không yêu cầu body. Không suy diễn rằng mọi endpoint đều không cần authentication.

## 6. Request body, authentication và response

Đối với các endpoint POST, PUT và PATCH, cần kiểm tra schema thực tế trong Swagger:

1. Mở `/docs`.
2. Chọn endpoint cần tích hợp.
3. Chọn `Try it out`.
4. Kiểm tra Parameters và Request body.
5. Điền dữ liệu theo schema.
6. Chọn `Execute`.
7. Xem HTTP status code và Response body.

Đối với endpoint có xác thực:

- Kiểm tra security scheme trong OpenAPI.
- Kiểm tra dependencies và middleware xác thực trong Backend.
- Sử dụng credential/token hợp lệ được cấp cho người tích hợp.
- Không tự giả định mọi endpoint đều sử dụng cùng một cơ chế authentication.

Tài liệu này không tự đặt ra request schema, response schema hoặc quyền truy cập chưa được xác minh từ source code.

## 7. Các nhóm API

### Core Backend

- `/chat`
- `/conversations/...`

### Agent Task Management

- `/agent/tasks`
- `/agent/tasks/{task_id}`
- `/agent/tasks/{task_id}/resume`

### Personal Healthcare Companion

- `/companion`
- `/companion/initialize`
- `/companion/consent`
- `/companion/context`
- `/companion/needs`
- `/companion/follow-up`

### Proactive Engine

- `/companion/proactive/evaluate`
- `/companion/proactive/proposals`

Các endpoint này thể hiện những nhóm chức năng được khai báo trong Backend; không đồng nghĩa toàn bộ logic đã được triển khai production hoặc cho phép thực hiện quyết định lâm sàng tự động.

## 8. API integration checklist

Trước khi tích hợp vào Frontend, Agent hoặc hệ thống bên ngoài:

- [ ] Xác nhận Base URL và môi trường chạy.
- [ ] Xác nhận endpoint có tồn tại trong OpenAPI.
- [ ] Xác nhận HTTP method và request schema.
- [ ] Xác nhận authentication và authorization.
- [ ] Kiểm tra response schema và error handling.
- [ ] Kiểm tra timeout, retry và rate limiting nếu có.
- [ ] Kiểm tra quyền truy cập dữ liệu theo user/owner.
- [ ] Không đưa secret key vào frontend hoặc repository.
- [ ] Kiểm tra consent và các giới hạn an toàn đối với dữ liệu y tế.

## 9. Nguồn tài liệu

- `README.md`: tổng quan và hướng dẫn dự án.
- `ARCHITECTURE.md`: kiến trúc hệ thống.
- `DEPLOYMENT.md`: triển khai.
- `AGENT_CONTRACT.md`: hợp đồng giao tiếp và quy ước Agent.
- `MULTI_AGENT_ARCHITECTURE.md`: kiến trúc Multi-Agent.
- `COMPANION_CORE_INTEGRATION.md`: tích hợp Companion Core.
- `PROACTIVE_ENGINE_INTEGRATION.md`: tích hợp Proactive Engine.
- `http://127.0.0.1:8000/docs`: API schema và thử nghiệm trực tiếp khi Backend đang chạy.

---

## 10. Important limitations

Tài liệu này là hướng dẫn tích hợp ban đầu, không phải cam kết production readiness.

Các thông tin cần được xác minh trước khi công bố API chính thức:

1. OpenAPI endpoint inventory đầy đủ, bao gồm router bên ngoài `main.py`.
2. Request/response examples chính xác cho từng endpoint.
3. Authentication, authorization và permission matrix.
4. Error codes và error response format.
5. Public deployment URL, HTTPS và CORS configuration.
6. API versioning, rate limits và operational monitoring.

**Không sử dụng API development/local để xử lý dữ liệu bệnh nhân thật hoặc triển khai dịch vụ lâm sàng production khi chưa hoàn thành đánh giá bảo mật, quyền riêng tư, an toàn và kiểm định phù hợp.**
