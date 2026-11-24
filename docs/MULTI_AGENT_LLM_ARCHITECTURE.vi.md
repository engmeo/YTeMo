# Multi-Agent LLM của Y TẾ MỞ

## Kiến trúc đang triển khai

Luồng hội thoại theo miền chuyên môn:

```text
User message + consented context + approved clinical evidence
                         |
                 Intent / risk router
                         |
                 LLM Supervisor Planner
                         |
             Parallel specialist fan-out
          /       |        |       |       \
     Medication  Lab    Clinical  Cost    BHYT / Care
          \       |        |       |       /
                 LLM Supervisor Synthesis
                         |
                Independent LLM Reviewer
                         |
                 Reviewer-approved answer
```

- Router xác định miền yêu cầu và chặn fast path cấp cứu trước khi gọi specialist.
- Supervisor Planner dùng LLM để đề xuất specialist; các miền đã được router nhận diện là bắt buộc, planner không được bỏ sót.
- Các specialist là LLM call độc lập với system role/prompt và model override riêng. LangGraph fan-out chúng trong cùng superstep; chỉ các agent được chọn mới gọi model.
- Supervisor Synthesis tổng hợp báo cáo, nêu agent lỗi và bất đồng.
- Reviewer là một agent role riêng kiểm tra draft trước khi phát hành. Nếu reviewer lỗi hoặc từ chối, hệ thống trả thông báo an toàn thay vì phát hành draft.
- Với chat streaming, frontend nhận trạng thái từng bước; nội dung cuối chỉ xuất hiện sau khi reviewer hoàn tất.

Đây là **multi-agent LLM orchestration** thực sự. Tuy nhiên, nếu không cấu hình `YTEMO_REVIEWER_MODEL` riêng thì reviewer có thể dùng cùng model nền với supervisor/synthesis. Reviewer tự động không phải bác sĩ phản biện, không bảo đảm độc lập thống kê và chưa được xác nhận độ chính xác lâm sàng.

## Specialist roles

| Role | Phạm vi |
|---|---|
| medication | Đọc thuốc/hàm lượng/lịch dùng, nêu điểm cần xác minh; không kê đơn hoặc đổi liều |
| laboratory | Đọc chỉ số/đơn vị/khoảng tham chiếu được cung cấp; không tự tạo reference range hoặc chẩn đoán |
| clinical | Tổ chức triệu chứng/diễn tiến/dấu hiệu cảnh báo; không tự chẩn đoán |
| cost | Phân tích khoản tiền người dùng cung cấp; không tự tạo giá |
| insurance | Đọc thông tin BHYT được cung cấp; không tự kết luận quyền lợi |
| care_navigation | Làm rõ nhu cầu và điều hướng; không giả định lịch khám/dịch vụ có sẵn |

Các specialist LLM không thay thế extractor xác định hiện có. Với hồ sơ, extractor vẫn cung cấp số dòng, dữ kiện và phép tính có thể kiểm thử; LLM chỉ diễn giải/tổng hợp trong phạm vi đã định.

## Model configuration

Model Gateway vẫn dùng 3 profile mặc định: `fast`, `reasoning`, `medical`. Có thể override riêng từng vai trò bằng model ID do đơn vị triển khai chọn:

- `YTEMO_SUPERVISOR_MODEL`
- `YTEMO_MEDICATION_MODEL`
- `YTEMO_LABORATORY_MODEL`
- `YTEMO_CLINICAL_MODEL`
- `YTEMO_COST_MODEL`
- `YTEMO_INSURANCE_MODEL`
- `YTEMO_CARE_NAVIGATION_MODEL`
- `YTEMO_SYNTHESIS_MODEL`
- `YTEMO_REVIEWER_MODEL`

Nếu không đặt override, role dùng model profile tương ứng. Vì vậy các role có prompt/ranh giới riêng nhưng có thể dùng chung model ID. Muốn model thực sự khác nhau phải cấu hình model ID tương ứng và xác minh provider hỗ trợ.

Các biến điều khiển:
- `YTEMO_MULTI_AGENT_ENABLED=true`: bật multi-agent cho chat theo miền chuyên môn; chỉ hoạt động khi Model Gateway đã cấu hình.
- `YTEMO_MODEL_BACKEND=openrouter` hoặc `local`.
- `YTEMO_MODEL_TIMEOUT_SECONDS`: timeout theo cấu hình Model Gateway.
- Các model ID phải là ID thật có trên provider hoặc được serve tại endpoint local; không dùng model ID minh họa.

## Phân tích hồ sơ tải lên và quyền riêng tư

Endpoint `POST /healthcare/agents/run` vẫn chạy extractor xác định và phép tính deterministic như trước.

Để gửi nội dung hồ sơ cho LLM specialist, request phải có `allow_external_llm_analysis: true` **và** quản trị viên phải bật `YTEMO_ALLOW_EXTERNAL_DOCUMENT_LLM=true`. Mặc định là tắt. Khi bật, nội dung hồ sơ được gửi tới provider đã cấu hình (OpenRouter hoặc endpoint local); phải kiểm tra điều khoản xử lý dữ liệu, nơi lưu trữ, retention và thỏa thuận dữ liệu trước khi bật với hồ sơ thật. Không dùng nội dung hồ sơ làm training data.

## Giới hạn an toàn và vận hành

- Chỉ có tối đa 5 specialist cho một lượt để giới hạn số model calls.
- Specialist chạy song song; planner, synthesis và reviewer chạy theo thứ tự.
- Một specialist lỗi được ghi rõ trong báo cáo; nếu không có specialist nào hoàn tất thì không tạo câu trả lời giả.
- Nếu synthesis hoặc reviewer lỗi, hệ thống fail closed.
- Không có retry tự động nhiều lần trong lượt chat.
- Emergency signal được xử lý trước multi-agent; cơ chế từ khóa chỉ là safety escalation thận trọng, không phải phát hiện cấp cứu đã được thẩm định.
- Không có claim đã duyệt thì không được đưa ra kết luận lâm sàng cá nhân.
- LLM reviewer không phải independent clinical validation. Cần bộ test gold do chuyên gia y tế xây dựng và đánh giá người thật.

## Benchmark cần chạy trước production

Đo riêng từng stage và toàn luồng:
- Supervisor planning latency
- từng specialist latency và tỷ lệ lỗi
- parallel fan-out wall time
- synthesis latency
- reviewer latency
- TTFT / end-to-end p50 / p95
- token usage và chi phí mỗi lượt
- groundedness, citation correctness, omission, unsafe completion, abstention precision/recall

Không công bố mục tiêu latency là kết quả thực tế trước khi đo trên Render/provider đang dùng.
