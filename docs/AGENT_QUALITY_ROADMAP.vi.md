# Nâng chất lượng AI Agent và lựa chọn mã nguồn mở

## Những gì đã có trong nhánh này

### 1. Điều phối hội thoại

LangGraph đang được dùng để chạy graph có các node:

1. `intent_router`: phân loại yêu cầu bằng nhiều tín hiệu tiếng Việt (thuốc, xét nghiệm, chi phí, BHYT, điều hướng khám, độ phức tạp và tín hiệu cấp cứu).
2. `emergency_triage`: đường xử lý xác định, không gọi LLM khi phát hiện tín hiệu cấp cứu; ưu tiên hướng dẫn liên hệ cấp cứu.
3. `discovery`: gọi một model cho hội thoại thông thường.

Đây là graph có định tuyến và fast path, **chưa phải mạng nhiều LLM chuyên gia tự tranh luận**. Không bật ensemble mặc định vì nó tăng latency và chi phí. Cần có bộ benchmark trước khi bổ sung LLM sub-agent.

### 2. Specialist Agents cho hồ sơ

`HealthcareAgentService` đã đăng ký các specialist độc lập:

- Cost: trích xuất khoản tiền được ghi rõ.
- Medication: trích xuất dòng thuốc/hàm lượng/lịch dùng.
- Lab: trích xuất chỉ số xét nghiệm.
- BHYT: trích xuất thông tin bảo hiểm.

Các agent chạy qua `AgentRegistry` và có Evidence Trace Critic + Safety Boundary Critic. Hiện đây là các agent trích xuất xác định, không phải chuyên gia LLM và không được phép tự chẩn đoán, kê đơn, diễn giải xét nghiệm hoặc kết luận quyền lợi BHYT.

### 3. Streaming

- Model Gateway hỗ trợ OpenAI-compatible SSE.
- `POST /chat?stream=true` trả token từng phần.
- `POST /chat` vẫn giữ JSON contract cũ.
- Không retry nhiều lần trong luồng tương tác; lỗi giữa luồng không lưu câu trả lời chưa hoàn tất.
- Frontend hiển thị từng token và có timeout tổng 60 giây.

Streaming cải thiện thời điểm người dùng bắt đầu nhìn thấy nội dung, không chứng minh model hoàn tất nhanh hơn. Chưa có số đo TTFT/p50/p95 trên môi trường Render/OpenRouter thực tế.

### 4. Trích xuất hồ sơ

Docling được tích hợp qua adapter tùy chọn:
- MIT codebase; phải rà soát license của model artifacts được tải riêng.
- Layout-aware extraction và table reconstruction.
- Tesseract CLI OCR cấu hình tiếng Việt + tiếng Anh (`vie`, `eng`).
- Giới hạn 10 MB và 100 trang.
- Không thêm vào runtime requirements mặc định.

**Chưa tách worker**: nếu bật `YTEMO_DOCUMENT_ENGINE=docling`, nó chạy đồng bộ trong FastAPI process. Không bật trên production trước khi có worker riêng và đo RAM/CPU/concurrency.

## Thư viện mã nguồn mở: trạng thái tích hợp

| Dự án | Vai trò | Giấy phép / điều kiện | Trạng thái |
|---|---|---|---|
| LangGraph | Điều phối graph | MIT | Đã dùng trong backend |
| Docling | Bố cục, bảng, PDF/DOCX | MIT codebase; rà soát model artifacts | Adapter tùy chọn đã thêm |
| PaddleOCR | OCR đa ngôn ngữ, gồm tiếng Việt | Apache-2.0; rà soát model weights | Chưa tích hợp; cần benchmark với Tesseract trên hồ sơ tiếng Việt |
| DeepEval | Đánh giá RAG/Agent/conversation | Apache-2.0 | Chưa tích hợp; cần chọn metrics và dataset chuyên gia trước |
| MedGemma | Model y tế đa phương thức | Health AI Developer Foundations terms, không phải giấy phép Apache/MIT phổ thông | Chưa bật; cần review terms và intended-use |

Không copy nguyên dự án hoặc model weights một cách mù quáng. Phải lưu upstream URL, commit/version, license, model card, checksum và điều kiện phân phối.

## Các việc còn thiếu để gọi là Agent chất lượng cao

1. Tách Docling thành worker có queue, concurrency limit, resource limit và retry nền.
2. Tạo evaluation dataset đã khử định danh, có reviewer chuyên môn, gold answer, citation, abstention và risk label.
3. Benchmark từng model/profile trên đúng hạ tầng triển khai: TTFT, inter-token latency, end-to-end p50/p95, lỗi provider, timeout và chi phí.
4. Cấu hình model ID tường minh cho fast/reasoning/medical; không dùng `openrouter/free` làm lựa chọn production nếu cần SLA.
5. Tích hợp DeepEval hoặc bộ evaluator tương đương sau khi có dataset gold; không dùng LLM-as-judge làm chuẩn lâm sàng duy nhất.
6. Nâng specialist thuốc/xét nghiệm/chi phí/BHYT từ extraction sang evidence-backed analysis theo từng phạm vi, có citation và reviewer.
7. Chỉ sau các bước trên mới thử supervisor LLM và parallel sub-agents; mặc định chỉ gọi đúng specialist cần thiết để không tăng latency vô ích.

## Nguyên tắc dữ liệu

- Patient Data không tự động trở thành Training Data.
- Clinical Knowledge chỉ được dùng như evidence sau review và có provenance.
- Evaluation Data tách riêng khỏi training, giữ cả trường hợp phải từ chối/abstain.
- Training Data cần kiểm tra license, provenance, quyền riêng tư, khử trùng lặp và phê duyệt của con người.
- Không dùng hồ sơ thật để huấn luyện nếu chưa có cơ sở pháp lý, consent phù hợp và quy trình bảo vệ dữ liệu được phê duyệt.
