# ĐỀ XUẤT GIAO DIỆN Y TẾ MỞ — MULTI-AGENT & PATIENT JOURNEY

## 1. Nguyên tắc thiết kế

Không biến toàn bộ sản phẩm thành một cửa sổ chat. Người dùng tiếp cận một Companion trung tâm; hệ thống điều phối các Specialist Agent theo nhu cầu và Patient Journey. Mỗi Agent có trách nhiệm, phạm vi, đầu vào, đầu ra và trạng thái riêng.

## 2. Cấu trúc điều hướng

1. **Tổng quan:** trạng thái hành trình chăm sóc, việc cần chú ý, đề xuất đang chờ người dùng.
2. **Companion:** hội thoại trung tâm, tóm tắt ngữ cảnh được phép sử dụng, nhu cầu đang mở.
3. **Patient Journey:** năm giai đoạn Before Care, During Care, Treatment, After Care, Long-term Care.
4. **Agent Directory:** danh mục Agent, nhiệm vụ, phạm vi hỗ trợ, trạng thái sẵn sàng và Agent phối hợp.
5. **My Tasks:** task đã tạo, tiến trình, timeline, output, lỗi và resume.
6. **Proactive Inbox:** đề xuất hỗ trợ, lý do đề xuất, dữ liệu/consent được dùng, chấp nhận/từ chối.
7. **Health Context & Memory:** dữ liệu người dùng cho phép lưu, nguồn gốc, thời hạn, quyền xem/xóa; chỉ bật các thao tác Memory khi API Backend đã được công bố.
8. **Privacy & Consent:** scope, mục đích, trạng thái, lịch sử thay đổi và thu hồi consent.
9. **Human Review:** nội dung chờ chuyên gia/người dùng xác nhận; không giả lập chuyên gia AI như người có thẩm quyền.

## 3. Bản đồ Agent

### Trung tâm
**Personal Healthcare Companion Agent**
- Tiếp nhận người dùng.
- Duy trì context có consent.
- Nhận diện nhu cầu và điều phối.
- Theo dõi kết quả và nhắc việc.
- Không tự nhận quyền quyết định lâm sàng.

### Năm Agent theo Patient Journey
- **Before Care Agent:** khám phá nhu cầu, chuẩn bị khám, định hướng tiếp cận dịch vụ.
- **During Care Agent:** hỗ trợ người dùng hiểu quy trình, ghi nhận câu hỏi và phối hợp thông tin trong quá trình chăm sóc.
- **Treatment Agent:** hỗ trợ hiểu kế hoạch đã được nhân viên y tế chỉ định, theo dõi việc thực hiện và cảnh báo cần hỏi lại chuyên gia.
- **After Care Agent:** theo dõi sau khám/điều trị, hướng dẫn đã được phê duyệt, phục hồi và follow-up.
- **Long-term Care Agent:** theo dõi liên tục, phát hiện thay đổi và hỗ trợ quản lý nhu cầu dài hạn.

### Agent hỗ trợ xuyên suốt
- **Safety & Triage Agent:** nhận diện dấu hiệu cảnh báo theo quy tắc được chuyên gia xác nhận; chuyển người dùng tới chăm sóc phù hợp.
- **Care Navigation Agent:** cơ sở, chuyên khoa, dịch vụ và tuyến chăm sóc.
- **Cost Intelligence Agent:** chi phí, BHYT, quyền lợi và khả năng tiếp cận.
- **Medical Knowledge Agent:** giải thích kiến thức từ nguồn có thể truy xuất.
- **Medication Support Agent:** thông tin và nhắc việc theo chỉ định; không tự kê đơn/đổi thuốc.
- **Human Review Agent/Queue:** điều phối yêu cầu cần con người có thẩm quyền.

Các Agent trên là đề xuất tổ chức sản phẩm. Chỉ đánh dấu “đã triển khai” khi có Agent profile, workflow/runner, policy, API integration và test tương ứng.

## 4. Màn hình chính đề xuất

### A. Home / Companion Dashboard
- Lời chào và trạng thái Companion.
- “Điều gì đang cần chú ý?”: needs đang mở.
- “Đang ở giai đoạn nào?”: Patient Journey.
- “Đề xuất dành cho bạn”: proactive proposals.
- “Công việc đang chạy”: Agent tasks.
- CTA rõ ràng: tiếp tục trò chuyện, xem nhu cầu, quản lý consent.

### B. Companion Workspace
Bố cục ba vùng:
- Trái: Patient Journey và Agent đang tham gia.
- Giữa: hội thoại với Companion.
- Phải: context được phép dùng, nhu cầu đã xác nhận, thông tin còn thiếu và nguồn.
Không hiển thị chain-of-thought; chỉ hiển thị giải thích ngắn gọn, bằng chứng và trạng thái có thể kiểm chứng.

### C. Patient Journey
Hiển thị timeline năm giai đoạn. Mỗi giai đoạn có:
- Mục tiêu hỗ trợ.
- Agent phụ trách.
- Needs và task liên quan.
- Tài liệu/thông tin người dùng đã cho phép.
- Follow-up tiếp theo.
- Trạng thái: chưa bắt đầu / đang hỗ trợ / chờ người dùng / chờ chuyên gia / hoàn tất.

### D. Agent Directory
Mỗi thẻ Agent cần có:
- Tên và một nhiệm vụ chính.
- Những gì Agent có thể làm / không thể làm.
- Input cần thiết và output cung cấp.
- Các Agent phối hợp.
- API/workflow backing.
- Trạng thái: Planned / Implemented / Integrated / E2E verified.
Không tạo nút “chạy Agent” nếu chưa có API/authorization thực thi.

### E. Task Center
- Danh sách task theo trạng thái.
- Chi tiết từng task, step timeline, attempt, heartbeat nếu được phép hiển thị.
- Output và lỗi.
- Resume khi Backend cho phép.
- Phân biệt accepted/running/completed/failed; HTTP 202 không có nghĩa task hoàn thành.

### F. Privacy & Memory
- Consent theo mục đích và scope.
- Context đang được lưu, nguồn, thời gian và lý do.
- Nút thu hồi consent.
- Yêu cầu xem/xóa dữ liệu.
- Conflict/evidence chỉ hiển thị theo contract đã được phê duyệt.
Không xây giao diện thao tác Memory trước khi API Memory công khai và kiểm thử quyền truy cập.

## 5. Mapping màn hình với API hiện có

| Màn hình | API hiện có |
|---|---|
| Companion Dashboard | `GET /companion`, `GET /companion/needs`, `GET /companion/proactive/proposals`, `GET /agent/tasks` |
| Companion Workspace | `POST /chat`, `GET /conversations/{conversation_id}/messages` |
| Consent | `PUT /companion/consent` |
| Context | `GET/POST/DELETE /companion/context` |
| Needs & Follow-up | `GET/POST/PATCH /companion/needs`, `POST /companion/follow-up` |
| Proactive Inbox | `POST /companion/proactive/evaluate`, `GET/PATCH /companion/proactive/proposals` |
| Task Center | `POST/GET /agent/tasks`, `GET /agent/tasks/{task_id}`, `POST /agent/tasks/{task_id}/resume` |
| System Status | `GET /health` |

## 6. Những API cần thiết kế thêm trước khi hoàn thiện UI

- Specialist Agent Registry: list/detail/capabilities/version/status.
- Agent routing/assignment: Agent nào được chọn, vì sao, workflow nào đang chạy.
- Agent run/interaction contract nếu không đi qua Agent Tasks.
- Patient Journey state và event timeline.
- Human Review queue, assignment, decision và audit.
- Memory user-facing read/review/delete/conflict endpoints.
- Domain-specific workflows cho Navigation, Cost, Medication Support và các chuyên khoa.
- Notification/subscription API nếu cần cập nhật task/proposal theo thời gian thực.

Không dùng endpoint giả hoặc gọi thẳng module nội bộ từ browser để lấp các khoảng trống này.

## 7. Lộ trình Frontend

**Sprint 1 — Foundation**
- Auth/session, API client chung, lỗi/loading states.
- Chat và conversation history.
- Companion dashboard, initialize, consent.

**Sprint 2 — Companion workflow**
- Context, needs, follow-up.
- Proactive Inbox và phản hồi proposal.

**Sprint 3 — Agent execution**
- Task Center, timeline, status, resume.
- Agent Directory dựa trên registry/API thật; phần chưa có backend hiển thị Planned.

**Sprint 4 — Patient Journey**
- Năm giai đoạn và workflow thật.
- Human Review và domain-specific agent screens khi API đã sẵn sàng.

**Sprint 5 — Memory & production readiness**
- Memory UI sau khi API được công bố.
- E2E, authorization, privacy, accessibility và production checks.

## 8. Quy tắc nghiệm thu

Không đánh dấu một Agent là Integrated chỉ vì có một card trên UI. Cần đủ:
1. Agent profile và responsibility rõ ràng.
2. Workflow/runner thực thi được.
3. Backend authorization và consent.
4. API contract.
5. UI hiển thị trạng thái thật.
6. Unit/integration/E2E tests.
7. Human oversight cho quyết định rủi ro cao.
