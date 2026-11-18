# Y TẾ MỞ - Kiến trúc tổng thể

## 1. Định hướng

Y TẾ MỞ hướng tới nền tảng Healthcare AI Agent, không giới hạn ở một chatbot hỏi đáp. Hệ thống được định hướng phát triển thành kiến trúc có thể lập kế hoạch, nghiên cứu, sử dụng công cụ, quản lý tác vụ và phối hợp các Agent chuyên biệt.

## 2. Kiến trúc logic

```text
User / Healthcare Interaction
              |
              v
     API Layer (FastAPI)
              |
              v
    Agent Orchestration
       (LangGraph)
              |
              v
         Agent Core
   - Intent / task handling
   - Planning and tool execution
   - Task state management
   - Lease and heartbeat
   - Recovery
              |
       +------+------+
       |             |
       v             v
 Gemini Service   Supabase
 AI inference     Data / Auth
```

Frontend hiện tại là prototype giao tiếp với Backend. Nó không phải trọng tâm kiến trúc Agent.

## 3. Thành phần đã có trong mã nguồn

### API Layer
Backend sử dụng FastAPI. Các endpoint đã được ghi nhận gồm health check, public configuration, hội thoại, chat và các endpoint tác vụ Agent.

### Agent Layer
`agent.py` là lớp kết nối Agent. `agent_core.py` chứa logic Agent Core và quản lý tiến trình tác vụ.

### Gemini Service
`gemini_service.py` quản lý việc gọi Gemini, timeout và retry lỗi tạm thời.

### Supabase Integration
Backend có mã tích hợp Supabase cho dữ liệu và xác thực. Việc vận hành thực tế cần cấu hình credentials và kiểm thử tích hợp.

### Task Execution
Agent Core đã có logic và unit tests cho:
- Atomic task claim.
- Lease và fencing worker cũ.
- Heartbeat định kỳ.
- Resume các bước đã hoàn thành.
- Startup recovery.
- Giới hạn worker recovery.

## 4. Kiến trúc mục tiêu

Các thành phần sau là định hướng phát triển, không đồng nghĩa đã hoàn thiện:

- Healthcare Orchestrator.
- Medical Research Agent.
- Clinical Knowledge Agent.
- Health Analysis Agent.
- Task Execution Agent.
- Medical Knowledge Base và RAG.
- Multi-Agent coordination.
- Safety, evaluation và observability.

## 5. Nguyên tắc an toàn

- Phân biệt thông tin đã xác minh và thông tin chưa xác minh.
- Lưu nguồn tham chiếu cho nội dung nghiên cứu.
- Không xem kết quả mô hình là bằng chứng y khoa.
- Không đưa dữ liệu bệnh nhân hoặc bí mật dịch vụ vào repository.
- Các năng lực có ảnh hưởng đến quyết định y tế cần được chuyên gia đánh giá.
- Không triển khai sử dụng lâm sàng nếu chưa qua kiểm định phù hợp.
