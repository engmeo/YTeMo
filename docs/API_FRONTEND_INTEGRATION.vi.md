# Y TẾ MỞ — HƯỚNG DẪN TÍCH HỢP FRONTEND ↔ BACKEND

> Tài liệu triển khai cho Frontend, Backend và QA. Danh mục endpoint và schema chi tiết được đồng bộ từ OpenAPI hiện tại tại `docs/api/openapi.json`. Đây là tài liệu kỹ thuật, không phải tuyên bố mọi luồng đã chạy production.

## 1. Nguyên tắc kiến trúc

Y TẾ MỞ là hệ thống Multi-Agent, không phải một chatbot duy nhất gắn nhiều nhãn.

- **Personal Healthcare Companion Agent:** đầu mối đồng hành, duy trì ngữ cảnh theo consent và điều phối nhu cầu.
- **Specialist Agents:** mỗi Agent có một nhiệm vụ chuyên môn, phạm vi quyền hạn, input/output và tiêu chí đánh giá riêng; phối hợp qua workflow.
- **AgentCore:** quản lý vòng đời task thực thi bền vững (claim/lease, heartbeat, resume, trạng thái và sự kiện).
- **Planning Engine:** lập kế hoạch, kiểm tra, giám sát và đề xuất recovery/replanning; không trực tiếp thực thi hành động.
- **Governance/Safety:** consent, phân quyền, audit, human review và các rào chắn an toàn.

API hiện có là các cổng Backend để Frontend tích hợp những năng lực nền tảng. Không được hiểu mỗi route là một Agent riêng.

## 2. Phân biệt trạng thái

| Trạng thái | Ý nghĩa |
|---|---|
| Backend route có trong OpenAPI | Có hợp đồng API được mô tả |
| Frontend đã gọi | Có bằng chứng mã Frontend gọi endpoint |
| E2E verified | Đã kiểm thử luồng thật từ trình duyệt tới Backend và dependency |
| Production verified | Đã xác minh cấu hình, migration, auth và deployment trên môi trường production |

Không chuyển trạng thái chỉ dựa trên việc tìm thấy tên endpoint trong source.

## 3. API hiện có và nhóm chức năng

Danh sách đầy đủ method/path, parameters, request/response schema được đặt tại [`api/API_ENDPOINTS.md`](api/API_ENDPOINTS.md).

| Nhóm | Endpoint | Vai trò Frontend |
|---|---|---|
| System | `GET /`, `GET /health` | Kiểm tra Backend và health |
| Public configuration | `GET /public-config` | Lấy Supabase URL và publishable key công khai |
| Conversation | `POST /chat` | Gửi lượt hội thoại tới Backend |
| Conversation history | `GET /conversations/{conversation_id}/messages` | Khôi phục lịch sử hội thoại |
| Agent task | `POST /agent/tasks` | Tạo task bất đồng bộ |
| Agent task | `GET /agent/tasks` | Danh sách task của người dùng |
| Agent task | `GET /agent/tasks/{task_id}` | Chi tiết/trạng thái task |
| Agent task | `POST /agent/tasks/{task_id}/resume` | Yêu cầu tiếp tục task |
| Companion | `POST /companion/initialize` | Khởi tạo Companion |
| Companion | `GET /companion` | Đọc trạng thái Companion |
| Consent | `PUT /companion/consent` | Cập nhật phạm vi đồng ý |
| Patient context | `POST /companion/context` | Ghi context theo consent |
| Patient context | `GET /companion/context` | Đọc context được phép |
| Patient context | `DELETE /companion/context/{context_id}` | Xóa context |
| Needs | `POST /companion/needs` | Tạo nhu cầu |
| Needs | `GET /companion/needs` | Danh sách nhu cầu |
| Needs | `PATCH /companion/needs/{need_id}` | Cập nhật trạng thái/chi tiết nhu cầu |
| Follow-up | `POST /companion/follow-up` | Tiếp tục hỏi làm rõ nhu cầu |
| Proactive | `POST /companion/proactive/evaluate` | Đánh giá nhu cầu hỗ trợ chủ động |
| Proactive | `GET /companion/proactive/proposals` | Lấy đề xuất hỗ trợ |
| Proactive | `PATCH /companion/proactive/proposals/{proposal_id}` | Phản hồi/cập nhật proposal |

> Bảng trên là inventory route đã được xác định trong Backend. Chi tiết schema phải đọc từ `API_ENDPOINTS.md`; không tự đoán body hoặc response.

## 4. Xác thực và API client dùng chung

Frontend dùng Supabase Auth. Sau khi đăng nhập, lấy access token từ session và gửi Bearer token tới Backend. Không bao giờ đưa service-role key vào HTML/JavaScript phía client.

Ví dụ mẫu theo cách tích hợp hiện tại:

```javascript
async function getAccessToken(supabase) {
  const { data, error } = await supabase.auth.getSession();
  if (error) throw error;
  const token = data.session?.access_token;
  if (!token) throw new Error("Phiên đăng nhập đã hết hạn.");
  return token;
}

async function apiRequest(supabase, apiBase, path, options = {}) {
  const token = await getAccessToken(supabase);
  const response = await fetch(`${apiBase}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
      "Authorization": `Bearer ${token}`
    }
  });

  const raw = await response.text();
  let payload = null;
  try { payload = raw ? JSON.parse(raw) : null; }
  catch { payload = raw; }

  if (!response.ok) {
    const message = payload?.detail || payload?.message || `HTTP ${response.status}`;
    throw new Error(message);
  }
  return payload;
}
```

Ví dụ gọi lịch sử hội thoại:

```javascript
const messages = await apiRequest(
  supabase,
  API_BASE,
  `/conversations/${encodeURIComponent(conversationId)}/messages`
);
```

Ví dụ gửi chat — body phải khớp schema OpenAPI đang có:

```javascript
const result = await apiRequest(supabase, API_BASE, "/chat", {
  method: "POST",
  body: JSON.stringify(chatRequestBody)
});
```

`chatRequestBody` phải được tạo theo schema thật trong `api/API_ENDPOINTS.md`; không sao chép ví dụ payload từ tài liệu cũ nếu schema đã thay đổi.

## 5. Luồng Frontend cần triển khai

### 5.1 Authentication

1. Gọi `GET /public-config`.
2. Khởi tạo Supabase client bằng URL và publishable key công khai.
3. Đăng nhập/đăng xuất qua Supabase Auth.
4. Lắng nghe thay đổi session.
5. Mỗi request protected API lấy access token mới nhất.
6. Khi 401/403: dừng thao tác phù hợp, hiển thị trạng thái phiên/quyền truy cập; không retry vô hạn.

### 5.2 Personal Healthcare Companion

1. Sau đăng nhập, gọi `GET /companion`.
2. Nếu chưa khởi tạo, dùng `POST /companion/initialize`.
3. Hiển thị và quản lý consent bằng `PUT /companion/consent`.
4. Chỉ tải/ghi context khi scope consent cho phép.
5. Dùng `GET/POST/DELETE /companion/context` theo đúng schema.
6. Hiển thị nhu cầu bằng `GET/POST/PATCH /companion/needs`.
7. Dùng `POST /companion/follow-up` cho lượt làm rõ tiếp theo.

### 5.3 Proactive support

1. Chỉ đánh giá chủ động trong phạm vi consent.
2. Gọi `POST /companion/proactive/evaluate` theo trigger được Backend cho phép.
3. Hiển thị proposals từ `GET /companion/proactive/proposals`.
4. Người dùng phải nhìn thấy nội dung, lý do, mức độ ưu tiên và hành động dự kiến trước khi chấp nhận/từ chối.
5. Gửi phản hồi qua `PATCH /companion/proactive/proposals/{proposal_id}` theo schema OpenAPI.
6. Không tự động biến proposal thành hành động y tế hoặc thực thi bên ngoài khi chưa có authorization thích hợp.

### 5.4 Agent Tasks

1. Tạo task qua `POST /agent/tasks`.
2. Hiển thị task qua `GET /agent/tasks` và `GET /agent/tasks/{task_id}`.
3. Làm mới trạng thái theo chiến lược polling/backoff hoặc cơ chế realtime được Backend hỗ trợ.
4. Chỉ hiển thị nút Resume khi trạng thái và quyền cho phép.
5. Gọi `POST /agent/tasks/{task_id}/resume`; xử lý 202 là accepted, không phải completed.
6. Hiển thị timeline/event/output/attempt và trạng thái terminal.

### 5.5 Chat

Chat là một điểm vào hội thoại. Nó không đồng nghĩa toàn bộ Specialist Agent đã được điều phối. UI cần cho biết khi nào request đang ở luồng chat, khi nào đã tạo task, Agent nào được chọn và trạng thái thực thi nếu Backend cung cấp các dữ liệu đó.

### 5.6 Healthcare document extraction and specialists (STT17)

1. Require an authenticated session and send the current Supabase access token as `Authorization: Bearer <access_token>` to each protected route.
2. Upload the selected file to `POST /healthcare/documents/extract` as `multipart/form-data` with field name `file`. Supported formats: PDF, DOCX, TXT, Markdown; maximum 10 MB.
3. Read `response.document.text` and `response.document.extraction_status`. Do not send an empty extraction to the analysis endpoint.
4. For a text-based PDF, DOCX, TXT, or Markdown file, the Backend extracts text locally. For a scanned PDF with no text layer, OCR is attempted only if local Tesseract + `vie`/`eng` language data and Python OCR dependencies are configured.
5. For scanned-PDF OCR on the Backend host, install `backend/requirements-ocr.txt`, install Tesseract with `vie` and `eng` language data, and set `TESSERACT_CMD` only when Tesseract is not on `PATH`. This is optional; text-layer PDF and DOCX/TXT/Markdown extraction do not require OCR.
6. Call `GET /healthcare/agents` to obtain the available agents and `default_agent_keys`.
7. Call `POST /healthcare/agents/run` with JSON `{ "document_text": "<extracted text>", "agent_keys": ["cost", "medication", "lab", "bhyt"] }`. Omit `agent_keys` to use the Backend defaults.
8. Render each finding together with its `evidence` line/quote and `missing_information`. Preserve the source document and page/line context; do not present extracted amounts as a verified bill total.
9. Treat all outputs as information extraction only. Do not use them to diagnose, prescribe, change medication, determine BHYT entitlement, or replace review by qualified healthcare professionals.

Example browser request (the token must come from the authenticated session):

```javascript
const form = new FormData();
form.append("file", selectedFile);
const extracted = await fetch(`${API_BASE}/healthcare/documents/extract`, {
  method: "POST",
  headers: { Authorization: `Bearer ${accessToken}` },
  body: form
}).then(checkResponse);

const analysis = await fetch(`${API_BASE}/healthcare/agents/run`, {
  method: "POST",
  headers: {
    Authorization: `Bearer ${accessToken}`,
    "Content-Type": "application/json"
  },
  body: JSON.stringify({ document_text: extracted.document.text })
}).then(checkResponse);
```

Do not manually set the multipart `Content-Type`; the browser must add its boundary. Do not log document text, access tokens, or identifiable health information.

### 5.7 Cost Intelligence — STT19
`POST /healthcare/agents/run` vẫn yêu cầu Supabase session hợp lệ. Ngoài `document_text` và `agent_keys`, Frontend có thể gửi thêm:
- `cost_items`: tối đa 500 dòng; `category` thuộc `visit`, `medicine`, `lab`, `imaging`, `procedure`, `supplies`, `transport`, `other`; mỗi dòng cần `description`, `quantity`, `unit_price`, `currency` và ít nhất một trong `source_quote` / `source_ref`. Nếu có `source_quote`, backend kiểm tra trích dẫn xuất hiện trong `document_text`.
- `bhyt`: chỉ gửi khi dữ liệu đã được xác minh; bắt buộc `eligible_amount` và `coverage_rate` (0–100), tùy chọn `patient_cap`, `currency`, `rule_reference`.

Ví dụ payload:
```javascript
{
  document_text: extracted.document.text,
  agent_keys: ["cost", "medication", "lab", "bhyt"],
  cost_items: [{
    item_id: "lab-01", category: "lab", description: "Glucose",
    quantity: 1, unit_price: 50000, currency: "VND",
    source_quote: "Glucose — 50.000đ"
  }],
  bhyt: { eligible_amount: 50000, coverage_rate: 80, currency: "VND" }
}
```

Response bổ sung `cost_intelligence_report`: tổng chi phí, phân nhóm, tổng nhóm thuốc/xét nghiệm và phép tính BHYT. Không có dữ liệu tài chính thì báo cáo ở trạng thái `insufficient_data` / `not_calculated`, không tự tạo giá. BHYT chỉ là phép tính số học từ đầu vào; không xác định đúng tuyến, đối tượng, quyền lợi pháp lý hoặc phạm vi được chi trả. Thuốc và xét nghiệm chỉ được trích xuất/tổng hợp, không kê đơn hoặc kết luận chỉ định.

## 6. Mapping API → màn hình

| Màn hình | API chính |
|---|---|
| Đăng nhập / phiên | `GET /public-config` + Supabase Auth |
| Trợ lý hội thoại | `POST /chat`, `GET /conversations/{id}/messages` |
| Trang tổng quan Companion | `GET /companion`, `POST /companion/initialize` |
| Quyền riêng tư / Consent | `PUT /companion/consent` |
| Patient Context | `GET/POST/DELETE /companion/context` |
| Nhu cầu chăm sóc | `GET/POST/PATCH /companion/needs` |
| Làm rõ nhu cầu | `POST /companion/follow-up` |
| Đề xuất chủ động | `POST /companion/proactive/evaluate`, `GET/PATCH /companion/proactive/proposals` |
| Công việc Agent | `POST/GET /agent/tasks`, `GET /agent/tasks/{id}`, `POST /agent/tasks/{id}/resume` |
| Trạng thái hệ thống | `GET /health` |

## 7. Những phần chưa được coi là API đã có

Từ inventory hiện tại, chưa thấy route chuyên biệt cho:
- CRUD/registry và cấu hình Specialist Agent.
- Agent capability discovery, assignment và routing policy hiển thị cho UI.
- Giao diện quản lý Independent Review Network.
- Memory CRUD/review/conflict-resolution APIs cho người dùng.
- Patient Journey dashboard chuyên biệt theo năm giai đoạn.
- Care Navigation, Cost Intelligence, Medication Support và các domain workflow chuyên biệt.

Các năng lực nội bộ có thể đã tồn tại ở module Backend nhưng nếu chưa có API công khai trong OpenAPI thì Frontend chưa được tự gọi trực tiếp. Cần thiết kế API/contract riêng trước khi làm UI tương ứng.

## 8. Bảo mật và dữ liệu y tế

- Không lưu access token hoặc thông tin sức khỏe nhạy cảm vào log.
- Không đưa service-role key vào browser.
- Backend phải xác minh JWT và derive owner/user ID từ danh tính đã xác thực; không tin user_id do client tự gửi.
- Mọi truy vấn dữ liệu phải enforce owner/tenant/agent scope ở Backend.
- Consent phải được kiểm tra tại Backend, không chỉ ẩn nút ở Frontend.
- Xóa context phải có xác nhận phù hợp và phản ánh rõ soft-delete hay hard-delete theo contract.
- Không dùng dữ liệu bệnh nhân thật trong bản thử nghiệm nếu chưa có phê duyệt, bảo vệ dữ liệu và quy trình phù hợp.
- Các quyết định lâm sàng cần người có chuyên môn và thẩm quyền.

## 9. Tiêu chí nghiệm thu Frontend

- Mọi endpoint được gọi đều có typed/request contract bám OpenAPI.
- Có loading, empty, success, error, unauthorized và retry states.
- Không gọi API protected trước khi có session.
- Có test cho token hết hạn, mất mạng, request trùng, double-submit và dữ liệu rỗng.
- Có test owner isolation và consent enforcement ở Backend.
- E2E test xác minh request thật từ trình duyệt đến Backend.
- Không đánh dấu production-ready chỉ vì unit tests hoặc OpenAPI contract tests pass.

## 10. Tài liệu liên quan

- `README.md` — tổng quan dự án.
- `docs/api/API_ENDPOINTS.md` — endpoint và schema được sinh từ OpenAPI.
- `docs/FRONTEND_AGENT_UI_PROPOSAL.vi.md` — đề xuất cấu trúc giao diện Multi-Agent.
- `docs/api/openapi.json` — API contract nguồn.
