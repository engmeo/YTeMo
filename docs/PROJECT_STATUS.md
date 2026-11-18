# Y TẾ MỞ - Project Status

Ngày ghi nhận: 2026-11-18

## 1. Những gì đã có trong mã nguồn staging

- FastAPI backend.
- Agent integration qua agent.py.
- Agent Core.
- Gemini service.
- Supabase integration.
- API hội thoại và các API hỗ trợ.
- Logic quản lý task và startup recovery.
- Frontend prototype.

## 2. Kiểm thử đã thực hiện

### Unit tests

| Test module | Số lượng | Kết quả |
|---|---:|---|
| test_agent_core.py | 9 | PASS |
| test_gemini_service.py | 5 | PASS |
| test_startup_recovery.py | 3 | PASS |
| Tổng | 17 | PASS |

### Các hành vi đã kiểm thử

- Trích xuất thông tin còn thiếu.
- Từ chối tool không được hỗ trợ.
- Tạo checklist nghiên cứu có cảnh báo dữ liệu chưa xác minh.
- Atomic claim ngăn hai worker nhận cùng task.
- Worker cũ bị fencing sau khi lease hết hạn.
- Resume bỏ qua các bước đã hoàn thành.
- Heartbeat chạy lặp trong lúc tool thực thi.
- Không trả kết quả nếu lease bị mất.
- Gemini timeout và retry lỗi tạm thời.
- Dừng retry sau số lần tối đa.
- Startup recovery xử lý lỗi riêng lẻ và giới hạn worker.

### Syntax check

Lệnh py_compile đã chạy thành công trên 12 file Python trong staging trước khi loại bỏ 5 script kiểm thử thủ công.

## 3. Những gì chưa được xác nhận

- Integration test với Gemini API thật.
- Integration test với Supabase thật.
- End-to-end test toàn bộ luồng người dùng.
- Medical Research Agent hoàn chỉnh.
- Medical Knowledge/RAG hoàn chỉnh.
- Bộ Healthcare Agents chuyên biệt.
- Multi-Agent orchestration hoàn chỉnh.
- Clinical validation và đánh giá an toàn y tế toàn diện.
- Triển khai vận hành production.

## 4. Lưu ý về test

Năm script kiểm thử thủ công cũ đã được loại khỏi bản staging vì chúng thực hiện khởi tạo dịch vụ hoặc gọi API ngay khi import. Chúng không thuộc ba module unit test đã PASS.

Không được diễn giải 17 unit tests PASS thành bằng chứng toàn bộ hệ thống đã được kiểm định y tế hoặc đã vượt qua integration tests.

## 5. Lộ trình

1. Hoàn thiện Agent Core.
2. Xây dựng Medical Research Agent.
3. Xây dựng Medical Knowledge và RAG.
4. Phát triển Healthcare Agents theo nhiệm vụ.
5. Xây dựng Multi-Agent orchestration.
6. Bổ sung safety evaluation, observability và audit.
7. Kiểm thử tích hợp và triển khai Agent trong môi trường phù hợp.
