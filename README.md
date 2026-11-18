# Y TẾ MỞ (Y TE MO)

**Open-source Healthcare AI Agent Platform**

Y TẾ MỞ là dự án phát triển nền tảng AI Agent chuyên biệt cho lĩnh vực y tế. Mục tiêu là xây dựng hệ thống có khả năng tiếp nhận yêu cầu, phân tích nhiệm vụ, nghiên cứu thông tin y khoa, sử dụng công cụ và phối hợp các năng lực Agent.

## Mục tiêu phát triển

- Healthcare Interaction: tiếp nhận và duy trì ngữ cảnh hội thoại.
- Agent Core: lập kế hoạch, thực thi công cụ và quản lý trạng thái tác vụ.
- Medical Research: tìm kiếm, phân tích và tổng hợp tài liệu y khoa.
- Medical Knowledge: xây dựng kho tri thức và hệ thống truy xuất có nguồn.
- Healthcare Agents: phát triển các Agent theo nhiệm vụ y tế.
- Multi-Agent: điều phối nhiều Agent.
- Safety & Evaluation: đánh giá độ tin cậy, nguồn tham chiếu và rủi ro.

## Kiến trúc hiện tại

- Backend: Python, FastAPI.
- Agent orchestration: LangGraph và Agent Core.
- AI service: Google Gemini.
- Data/Auth integration: Supabase.
- Frontend: HTML và JavaScript.

Xem [kiến trúc tổng thể](docs/ARCHITECTURE.md).

## Năng lực đã có trong mã nguồn

- API hội thoại và các API hỗ trợ.
- Agent Core và logic thực thi tác vụ.
- Gemini Service có timeout và cơ chế retry.
- Tích hợp Supabase.
- Quản lý task bằng atomic claim, lease và heartbeat.
- Cơ chế startup recovery.
- Frontend prototype để tương tác với hệ thống.

## Kết quả kiểm thử đã ghi nhận

17/17 unit tests đã PASS trong ba nhóm:

- Agent Core, Atomic Claim và Heartbeat: 9 tests.
- Gemini Service: 5 tests.
- Startup Recovery: 3 tests.

Các bài kiểm thử này xác nhận một số hành vi kỹ thuật của Agent Core và dịch vụ liên quan. Chúng không thay thế kiểm thử tích hợp với Gemini/Supabase hoặc đánh giá lâm sàng.

Chi tiết: [PROJECT STATUS](docs/PROJECT_STATUS.md).

## Cấu trúc repository

- `backend/`: API, Agent Core, AI service và unit tests.
- `frontend/`: giao diện tương tác prototype.
- `docs/`: kiến trúc, trạng thái dự án và hướng dẫn.

## Cài đặt cơ bản

Yêu cầu Python tương thích với các dependency trong `backend/requirements.txt`.

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Tạo file `.env` từ `.env.example` và tự cấu hình các thông tin dịch vụ cần thiết. Không commit `.env` hoặc bất kỳ API key/secret nào.

## Chạy unit tests

```powershell
python -m unittest -v test_agent_core test_gemini_service test_startup_recovery
```

## Lộ trình phát triển

1. Hoàn thiện Agent Core và execution engine.
2. Phát triển Medical Research Agent.
3. Xây dựng Medical Knowledge và RAG.
4. Phát triển Healthcare Agents theo từng nhiệm vụ.
5. Xây dựng Multi-Agent orchestration.
6. Tăng cường Safety, Evaluation và observability.
7. Đóng gói và triển khai Agent trong môi trường vận hành phù hợp.

## Đóng góp

Xem [CONTRIBUTING.md](CONTRIBUTING.md).

## Giới hạn sử dụng

Y TẾ MỞ đang trong quá trình phát triển. Không sử dụng phiên bản hiện tại như công cụ chẩn đoán, kê đơn hoặc thay thế quyết định của nhân viên y tế. Mọi năng lực y tế cần được đánh giá chuyên môn, kiểm thử an toàn và xác minh nguồn dữ liệu trước khi sử dụng thực tế.
