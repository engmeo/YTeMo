# Y TẾ MỞ

**Nền tảng Personal Healthcare Companion và hệ thống Multi-Agent hỗ trợ hành trình chăm sóc sức khỏe.**

Y TẾ MỞ hướng tới việc giúp người dùng hiểu nhu cầu, tiếp cận nguồn lực chăm sóc, duy trì tính liên tục của hành trình và kết nối chuyên gia, nhà nghiên cứu, kỹ sư để phát triển giải pháp y tế có thể kiểm chứng.

> **Trạng thái dự án:** nền tảng Backend, Planning, AgentCore, Companion, Proactive và các lớp Memory đang được phát triển/kiểm thử. Release gates sáu phase đã PASS theo kết quả kiểm thử được ghi nhận. Điều đó không tự chứng minh mọi luồng Frontend đã tích hợp E2E, Supabase production đã áp dụng migration, hay sản phẩm đã được đánh giá lâm sàng.

## API Quick Reference — Backend hiện có

## 4. Backend API hiện có

API contract đầy đủ được duy trì trong:
- [`docs/api/API_ENDPOINTS.md`](docs/api/API_ENDPOINTS.md)
- [`docs/api/openapi.json`](docs/api/openapi.json)
- [`docs/API_FRONTEND_INTEGRATION.vi.md`](docs/API_FRONTEND_INTEGRATION.vi.md)

Các nhóm route đã được xác định:

| Nhóm | Endpoint |
|---|---|
| System | `GET /`, `GET /health`, `GET /public-config` |
| Conversation | `POST /chat`, `GET /conversations/{conversation_id}/messages` |
| Agent Tasks | `POST /agent/tasks`, `GET /agent/tasks`, `GET /agent/tasks/{task_id}`, `POST /agent/tasks/{task_id}/resume` |
| Companion | `POST /companion/initialize`, `GET /companion` |
| Consent | `PUT /companion/consent` |
| Context | `POST /companion/context`, `GET /companion/context`, `DELETE /companion/context/{context_id}` |
| Needs | `POST /companion/needs`, `GET /companion/needs`, `PATCH /companion/needs/{need_id}` |
| Follow-up | `POST /companion/follow-up` |
| Proactive | `POST /companion/proactive/evaluate`, `GET /companion/proactive/proposals`, `PATCH /companion/proactive/proposals/{proposal_id}` |

**Lưu ý:** Có route trong Backend/OpenAPI không có nghĩa Frontend đã gọi route đó. Có API contract cũng không tự chứng minh luồng production hoạt động. Trạng thái Frontend/E2E cần kiểm thử riêng.

## 1. Định hướng sản phẩm

Y TẾ MỞ không được định nghĩa là một chatbot đa năng. Đây là một hệ thống gồm:

1. **Personal Healthcare Companion Agent** — trung tâm đồng hành, hiểu ngữ cảnh được cấp quyền, khám phá nhu cầu và điều phối.
2. **Specialist Agents** — từng Agent đảm nhiệm một nhiệm vụ chuyên môn hoặc một giai đoạn Patient Journey.
3. **AgentCore** — quản lý vòng đời task, thực thi, lease, heartbeat, resume, persistence và recovery.
4. **Planning Engine** — lập kế hoạch, kiểm tra, giám sát và đề xuất recovery/replanning; không trực tiếp thực thi hành động.
5. **Memory Intelligence** — quản lý thông tin có nguồn gốc, thời gian, quan hệ, xung đột và consent.
6. **Safety & Governance** — xác thực, consent, phân quyền, audit, human review và rào chắn an toàn.

## 2. Multi-Agent theo Patient Journey

| Giai đoạn | Agent phụ trách | Trách nhiệm |
|---|---|---|
| Before Care | Before Care Agent | Khám phá nhu cầu, chuẩn bị khám, định hướng tiếp cận |
| During Care | During Care Agent | Hỗ trợ hiểu quy trình và phối hợp thông tin trong quá trình chăm sóc |
| Treatment | Treatment Agent | Hỗ trợ hiểu và theo dõi kế hoạch do nhân viên y tế chỉ định |
| After Care | After Care Agent | Theo dõi sau khám/điều trị, phục hồi và follow-up |
| Long-term Care | Long-term Care Agent | Theo dõi liên tục và phát hiện nhu cầu mới |

Các Agent hỗ trợ xuyên suốt có thể gồm Safety & Triage, Care Navigation, Cost Intelligence, Medical Knowledge, Medication Support và Human Review. Đây là cấu trúc mục tiêu; chỉ đánh dấu triển khai khi có profile, workflow, policy, API và test tương ứng.

## 3. Kiến trúc kỹ thuật

```text
User
 |
 v
Personal Healthcare Companion
 |
 +--> Patient Journey Specialist Agents
 |      +--> Before Care
 |      +--> During Care
 |      +--> Treatment
 |      +--> After Care
 |      +--> Long-term Care
 |
 +--> Cross-cutting Specialist Agents
 |      +--> Safety & Triage
 |      +--> Care Navigation
 |      +--> Cost Intelligence
 |      +--> Medical Knowledge
 |      +--> Medication Support
 |      +--> Human Review
 |
 +--> Memory Intelligence (consent-controlled)
 |
 +--> Healthcare workflows / Planning Engine
 |
 v
AgentCore (durable task lifecycle and execution)
 |
 v
Tools / approved services / human review
 |
 v
Observations, outcomes and audit
```

Planning và AgentCore có ranh giới rõ ràng: Planning đề xuất và giám sát; AgentCore chịu trách nhiệm vòng đời thực thi. Không thay thế AgentCore bằng một workflow UI hoặc chatbot.

## 5. Frontend

Frontend có thể dùng HTML/CSS/JavaScript thuần hoặc framework phù hợp với năng lực đội ngũ. Không bắt buộc React/Vue.

Frontend cần tổ chức theo trải nghiệm sản phẩm:
- Companion Dashboard.
- Companion Workspace.
- Patient Journey.
- Agent Directory.
- Task Center.
- Proactive Inbox.
- Health Context & Memory.
- Privacy & Consent.
- Human Review.

Đề xuất chi tiết và mapping màn hình/API: [`docs/FRONTEND_AGENT_UI_PROPOSAL.vi.md`](docs/FRONTEND_AGENT_UI_PROPOSAL.vi.md).

## 6. Công nghệ và thành phần

- Backend: Python / FastAPI.
- Authentication: Supabase Auth.
- Persistence: Supabase/PostgreSQL adapters và migrations.
- Agent execution: AgentCore.
- Planning: domain-neutral Planning Engine và các adapter/workflow nghiệp vụ.
- Frontend: HTML/CSS/JavaScript hoặc framework do nhóm Frontend lựa chọn.
- API contract: OpenAPI.

Không đưa Supabase `service_role` key vào Frontend. Backend phải xác minh người dùng, derive owner từ token, enforce tenant/owner/agent scope và consent.

## 7. Release gates và kiểm thử

Sáu phase release gates đã được chạy PASS theo log người dùng cung cấp. Full backend regression gần nhất: **520 passed, 10 subtests passed**. Các kiểm thử này là bằng chứng cho những contract và hành vi được kiểm thử; không thay thế:
- E2E browser → API → persistence.
- Xác minh migration đã áp dụng trên Supabase production.
- Kiểm thử quyền truy cập và tenant isolation trên môi trường thật.
- Đánh giá an toàn lâm sàng và usability với chuyên gia/người dùng.

## 8. Cấu trúc tài liệu

| Tài liệu | Nội dung |
|---|---|
| `docs/README.md` | Điều hướng tài liệu |
| `docs/API_FRONTEND_INTEGRATION.vi.md` | Hướng dẫn Frontend gọi Backend |
| `docs/api/API_ENDPOINTS.md` | Danh mục endpoint và schema |
| `docs/api/openapi.json` | OpenAPI contract |
| `docs/FRONTEND_AGENT_UI_PROPOSAL.vi.md` | Đề xuất giao diện Multi-Agent |
| `docs/README_MEMORY_PLANNING.vi.md` | Memory và Planning architecture |

## 9. Nguyên tắc an toàn

- Không sử dụng hệ thống hiện tại như công cụ chẩn đoán hoặc kê đơn độc lập.
- Không tự ý bắt đầu, ngừng hoặc thay đổi thuốc/phác đồ theo đầu ra AI.
- Quyết định lâm sàng cần người có chuyên môn và thẩm quyền.
- Chỉ xử lý dữ liệu sức khỏe trong phạm vi consent và chính sách bảo vệ dữ liệu phù hợp.
- Không dùng dữ liệu bệnh nhân thật trong môi trường thử nghiệm chưa được phê duyệt.
- Unit tests và release gates không thay thế đánh giá lâm sàng.

## Clinical Knowledge Governance — nền tảng tri thức y khoa

Backend bổ sung module quản trị nguồn và tài liệu y khoa, gồm provenance, kiểm tra metadata/chất lượng trích xuất, hàng đợi thẩm định chuyên gia, phê duyệt theo phạm vi và audit.

| Endpoint | Chức năng |
|---|---|
| GET /clinical-knowledge/sources | Danh mục nguồn tri thức được đăng ký |
| POST /clinical-knowledge/documents | Đăng ký tài liệu và chạy kiểm tra tự động |
| GET /clinical-knowledge/documents | Danh sách tài liệu, có thể lọc theo status |
| GET /clinical-knowledge/review-queue | Hàng đợi dành cho reviewer được cấp quyền |\n| GET /clinical-knowledge/documents/{id} | Reviewer đọc nội dung gốc đã trích xuất |
| POST /clinical-knowledge/documents/{id}/review | Ghi nhận phê duyệt/từ chối/yêu cầu sửa |

**Ranh giới an toàn:** automated checks chỉ kiểm tra nguồn/domain, metadata và tính toàn vẹn trích xuất; không xác minh nội dung y khoa đúng. Chỉ reviewer có quyền phù hợp mới được phê duyệt và phải chỉ rõ approved_scope. Tài liệu chưa được phê duyệt không được coi là clinical evidence. Module hiện chưa có crawler, OCR scheduler, vector retrieval hay clinical decision support.

- Kiến trúc, quy trình và hướng dẫn: [docs/CLINICAL_KNOWLEDGE_GOVERNANCE.vi.md](docs/CLINICAL_KNOWLEDGE_GOVERNANCE.vi.md)
- Migration: [supabase/migrations/202611240001_clinical_knowledge_governance.sql](supabase/migrations/202611240001_clinical_knowledge_governance.sql)

## 10. Đóng góp

Các nhóm Frontend, Backend, AI/Agent, Data, Clinical Governance và QA cần làm việc theo API contract, responsibility boundaries và tiêu chí nghiệm thu. Không xây giao diện giả cho năng lực chưa có API; ghi rõ Planned/Implemented/Integrated/E2E verified.

---

**Y TẾ MỞ — Hiểu nhu cầu. Kết nối nguồn lực. Duy trì hành trình chăm sóc.**

## Healthcare Document APIs (STT17)

- `POST /healthcare/documents/extract` — extract text from PDF/DOCX/TXT/Markdown; optional local OCR for scanned PDFs.
- `GET /healthcare/agents` — list Cost, Medication, Lab, and BHYT specialists.
- `POST /healthcare/agents/run` — run selected specialists against extracted text.

See [`docs/api/API_ENDPOINTS.md`](docs/api/API_ENDPOINTS.md) and [`docs/API_FRONTEND_INTEGRATION.vi.md`](docs/API_FRONTEND_INTEGRATION.vi.md) for request contracts and integration guidance.
