# Open Model Intelligence & Clinical Training — Y TẾ MỞ

## Mục tiêu

Xây dựng một Model Portfolio có thể thay đổi model mà không sửa Companion, ưu tiên:
- Model weights tải miễn phí và license rõ ràng.
- Inference engine mã nguồn mở, self-host khi có phần cứng.
- OpenRouter free-model pool như phương án thử nghiệm miễn phí có giới hạn; không coi đây là SLA hoặc bảo đảm riêng tư.
- Một model cho lượt hỏi thường ngày; chỉ tăng ngân sách suy luận khi câu hỏi phức tạp.
- LoRA/QLoRA trên máy training riêng; không chạy training trong web API.
- Chỉ mở phạm vi lâm sàng đã được kiểm định.

## Mô hình ứng viên

Danh sách và trạng thái hiện hành được quản lý trong `backend/model_registry.json`.

| Model | Vai trò dự kiến | License / điều kiện |
|---|---|---|
| Qwen3-4B | Fast/general reasoning | Apache-2.0 theo model card; kiểm tra revision trước khi tải |
| Mistral-7B-Instruct-v0.3 | General instruction | Apache-2.0 theo model card chính thức |
| DeepSeek-R1-Distill-Qwen-7B | Deep reasoning | MIT; model card nêu quyền thương mại và sửa đổi |
| MedGemma 4B | Medical text/image candidate | Health AI Developer Foundations terms; phải đọc và chấp thuận điều khoản riêng |
| BioMistral-7B | Biomedical language candidate | Chưa cho phép tải tự động cho tới khi xác minh upstream license và model card |

Các model trên là ứng viên kỹ thuật, không phải danh sách đã chứng minh độ an toàn lâm sàng. Model registry cố ý không bật mặc định. Không tải hoặc phục vụ đồng thời tất cả weights: tải theo từng model, đo VRAM/RAM, throughput và latency trên máy thực tế. Không commit weights vào Git.

Nguồn model card/license:
- Qwen3-4B: https://huggingface.co/Qwen/Qwen3-4B
- Mistral 7B Instruct v0.3: https://huggingface.co/mistralai/Mistral-7B-Instruct-v0.3
- DeepSeek R1 Distill Qwen 7B: https://huggingface.co/deepseek-ai/DeepSeek-R1-Distill-Qwen-7B
- MedGemma: https://developers.google.com/health-ai-developer-foundations/medgemma/model-card

## Inference miễn phí và tốc độ

### Chế độ 1: self-host (ưu tiên dài hạn)

Dùng một inference server OpenAI-compatible:
- vLLM hoặc SGLang cho GPU server.
- llama.cpp server cho quantized GGUF trên máy phù hợp.
- API backend gọi endpoint `/v1/chat/completions`.

Cấu hình:
- `YTEMO_MODEL_BACKEND=local`
- `YTEMO_LOCAL_MODEL_BASE_URL=http://127.0.0.1:8001/v1`
- `YTEMO_LOCAL_MODEL_API_KEY=local`
- `YTEMO_FAST_MODEL=<model-id-served>`
- `YTEMO_REASONING_MODEL=<model-id-served>`
- `YTEMO_MEDICAL_MODEL=<model-id-served>`

### Chế độ 2: free hosted pool

- `YTEMO_MODEL_BACKEND=openrouter`
- `OPENROUTER_API_KEY=<server-secret>`
- Mặc định dùng `openrouter/free`, có thể cấu hình model riêng theo từng profile.
- Free pool có thể thay đổi model, bị giới hạn tốc độ, hết quota hoặc không khả dụng. Không gửi dữ liệu định danh hoặc hồ sơ sức khỏe nhạy cảm tới provider bên ngoài nếu chưa có đánh giá quyền riêng tư, consent và điều khoản xử lý dữ liệu phù hợp.

### Routing và độ trễ

`backend/model_intelligence.py`:
- Chọn profile fast/reasoning/medical.
- Routine chat gọi một model, không chạy ensemble.
- Timeout được giới hạn; không âm thầm fallback sang model khác có chi phí.
- Reasoning model có thể chậm hơn; không bật chain-of-thought dài cho câu hỏi đơn giản.
- Latency được trả về metadata nội bộ, cần đo p50/p95 qua benchmark và production telemetry trước khi cam kết SLA.

Routing profile là lựa chọn ngân sách suy luận, không phải bộ quy tắc lâm sàng. Clinical governance, consent, emergency handling và quyền truy cập bằng chứng vẫn là lớp riêng.

## Dữ liệu y khoa và giấy phép

Nguồn tham khảo và chính sách intake nằm ở `backend/clinical_training/dataset_sources.json`.

Nguyên tắc:
1. Miễn phí đọc không đồng nghĩa miễn phí tái sử dụng hoặc dùng để training.
2. Ghi nhận source URL, publisher, document/version, article-level license, license URL, retrieval date và SHA-256.
3. Với Europe PMC, chỉ dùng bài trong OA subset có license từng bài phù hợp.
4. PubMed abstract không tự động được coi là public domain.
5. WHO publications cần kiểm tra điều khoản của từng ấn phẩm; không lấy toàn bộ nội dung chỉ vì đọc miễn phí.
6. CDC/US government: kiểm tra thành phần third-party có thể có quyền riêng.
7. Không đưa dữ liệu bệnh nhân thật vào pipeline mặc định. Nếu cần dữ liệu thực tế phải có cơ sở pháp lý, consent/ethics, de-identification và privacy review độc lập.
8. Không dùng forum, social media, nội dung scrape không rõ quyền hoặc dữ liệu bệnh án rò rỉ.

Allowlist mặc định của pipeline: CC0-1.0, CC-BY-4.0, CC-BY-3.0, US-GOV-PD. CC-BY-SA, CC-BY-NC, CC-BY-ND và unknown bị loại mặc định cho tới khi pháp chế/đơn vị phụ trách quyền dữ liệu xem xét tương thích. Allowlist có thể cấu hình theo từng dự án nhưng phải lưu lại lý do phê duyệt.

## Pipeline 8 bước

### 1. Thu thập

Dùng nguồn có API hoặc OA collection. Lưu metadata, license, provenance, version và hash. Source sync phải có log, retry, rate limit và lịch sử phiên bản.

### 2. Làm sạch, chuẩn hóa, deduplicate

- Chuẩn hóa Unicode và whitespace.
- Exact dedup bằng SHA-256 trên nội dung chuẩn hóa.
- Near-duplicate detection là bước gợi ý, không tự xóa nếu có khác biệt phiên bản/erratum.
- Chuẩn hóa thuật ngữ, đơn vị, ngày tháng và ngôn ngữ.
- Giữ nguyên nguồn gốc và nội dung gốc; mọi biến đổi có version.

### 3. Instruction–response

Tạo instruction–response draft từ claim đã có cấu trúc:
```bash
cd backend
python -m clinical_training.draft_sft_examples --input path/to/reviewed_claims.jsonl --output artifacts/clinical_sft_drafts.jsonl
```

Script tạo ví dụ cho STRONG/WEAK/CONFLICTING/INSUFFICIENT và giữ source/version/license. Tất cả đầu ra vẫn là `DRAFT`, chưa được phép training; phải có clinical review, source verification và privacy review trước khi đưa qua `prepare_dataset.py`.


Không tự động biến toàn bộ tài liệu thành câu trả lời huấn luyện. Tạo ví dụ từ claim/tình huống đã được review, kèm source, license, evidence locator, reviewer và trạng thái.

### 4. Evidence-state training

Mỗi ví dụ phải có một trong:
- STRONG
- WEAK
- CONFLICTING
- INSUFFICIENT

Dữ liệu cần dạy mô hình nhận diện mức độ bằng chứng, giới hạn ngoại suy, yêu cầu thông tin còn thiếu, nêu bất định và abstain khi thích hợp. Không biến nhãn thành xác suất lâm sàng nếu chưa có calibration.

### 5. LoRA/QLoRA

Cài optional dependencies:
```bash
pip install -r backend/requirements-training.txt
```

Chuẩn bị dataset:
```bash
cd backend
python -m clinical_training.prepare_dataset --input path/to/reviewed_records.jsonl --output artifacts/clinical_sft.jsonl
```

LoRA:
```bash
python -m clinical_training.train_lora --model Qwen/Qwen3-4B --dataset artifacts/clinical_sft.jsonl --output-dir artifacts/qwen3-4b-lora
```

QLoRA (cần CUDA GPU):
```bash
python -m clinical_training.train_lora --model Qwen/Qwen3-4B --dataset artifacts/clinical_sft.jsonl --output-dir artifacts/qwen3-4b-qlora --qlora
```

Không chạy lệnh training trên web worker hoặc máy không đủ RAM/VRAM. Adapter phải được version hóa cùng base model, dataset hash, license manifest, hyperparameters và training code revision.

### 6–7. Benchmark độc lập và before/after

Tạo benchmark case JSONL từ template, không chứa PHI. Chạy base và fine-tuned endpoint:
```bash
BENCH_BASE_URL=http://127.0.0.1:8001/v1 \
BENCH_BASE_MODEL=base-model \
BENCH_TUNED_URL=http://127.0.0.1:8002/v1 \
BENCH_TUNED_MODEL=finetuned-model \
python -m clinical_training.benchmark --cases clinical_training/benchmark_cases.template.jsonl
```

Runner chỉ thu output và latency; không tự chấm clinical correctness. Cần:
- Ẩn danh model thành A/B khi reviewer chấm.
- Ít nhất hai reviewer độc lập cho các case lâm sàng rủi ro cao.
- Chấm factual correctness, evidence-state classification, citation correctness, context use, missing-information handling, abstention, harmful advice, bias và Vietnamese clarity.
- Báo cáo riêng theo scenario group và mức rủi ro; không chỉ báo cáo accuracy trung bình.
- Dùng test set tách biệt khỏi training, không tune trên benchmark holdout.

### 8. Release gates

Một model chỉ được bật trong phạm vi đã kiểm định khi:
- License/model terms đã được xem xét.
- Dataset provenance và privacy audit đạt yêu cầu.
- Không có regression nghiêm trọng ở red-flag, medication, abstention và conflict cases.
- Blind benchmark before/after cho thấy cải thiện có ý nghĩa và không làm giảm safety.
- Latency p50/p95 đạt ngưỡng triển khai.
- Có model card nội bộ, intended use, excluded use, version, monitoring, rollback và incident workflow.
- Với clinical use: có đánh giá chuyên môn, prospective validation phù hợp và phê duyệt tổ chức.

Passing unit tests hoặc benchmark công khai không chứng minh an toàn để chẩn đoán/kê đơn.

## Trạng thái triển khai

| Thành phần | Trạng thái của PR này |
|---|---|
| Model registry và gateway | Implemented, cần cấu hình endpoint/keys |
| Companion routing integration | Implemented, cần test trong môi trường triển khai |
| Model weights | Chưa tải vào repo/server |
| Licensed source intake policy | Registry + validation policy implemented; chưa có crawler tự động |
| Dataset clean/dedup/provenance | CLI implemented |
| Instruction/evidence-state schema | Implemented |
| LoRA/QLoRA runner | Implemented, chưa chạy training thực |
| Paired benchmark runner | Implemented; clinical scoring cần blinded reviewers |
| Before/after comparison | Output collection + latency; reviewer scoring chưa có |
| Clinical validation | Chưa thực hiện |
| Patient-facing model release | Chưa được cho phép |

Không có API trả phí bắt buộc trong kiến trúc này. Tuy nhiên, self-host vẫn cần phần cứng/điện/năng lực vận hành; hosted free endpoints có quota và không đảm bảo tốc độ hoặc quyền riêng tư.
