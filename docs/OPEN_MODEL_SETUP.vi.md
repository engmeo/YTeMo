# Cài đặt và vận hành Open Models — Y TẾ MỞ

## 1. Dùng miễn phí ngay để thử nghiệm

Y TẾ MỞ hỗ trợ OpenRouter free-model pool. Tạo API key miễn phí, đặt trong backend environment:

```env
YTEMO_MODEL_BACKEND=openrouter
OPENROUTER_API_KEY=...
YTEMO_DEFAULT_MODEL=openrouter/free
YTEMO_FAST_MODEL=openrouter/free
YTEMO_REASONING_MODEL=openrouter/free
YTEMO_MEDICAL_MODEL=openrouter/free
YTEMO_MODEL_TIMEOUT_SECONDS=18
```

Free pool có quota, giới hạn tốc độ và danh sách model thay đổi. Không cam kết SLA. Không gửi dữ liệu sức khỏe định danh lên provider ngoài nếu chưa có đánh giá privacy/consent phù hợp.

## 2. Tải open weights đã có license rõ

Cài Hugging Face Hub:
```bash
pip install 'huggingface_hub>=0.26,<2'
```

Tải riêng các model Apache-2.0/MIT đã ghi trong registry:
```bash
cd backend
python -m clinical_training.download_models --model-ids qwen3-4b,mistral-7b-instruct-v03,deepseek-r1-distill-qwen-7b --confirm-license-review
```

Weights có thể chiếm hàng chục GB. Lệnh tải lưu ở `~/.cache/ytemo-models`, không đưa weights vào Git. MedGemma và BioMistral chưa nằm trong danh sách được tải tự động vì cần review thêm điều khoản/nguồn license.

## 3. Tự host inference

Cài vLLM, SGLang hoặc llama.cpp server theo phần cứng và model format phù hợp. Gateway cần endpoint tương thích OpenAI Chat Completions.

Ví dụ một server local:
```env
YTEMO_MODEL_BACKEND=local
YTEMO_LOCAL_MODEL_BASE_URL=http://127.0.0.1:8001/v1
YTEMO_LOCAL_MODEL_API_KEY=local
YTEMO_DEFAULT_MODEL=Qwen/Qwen3-4B
```

Có thể tách model profile thành nhiều server:
```env
YTEMO_FAST_BASE_URL=http://127.0.0.1:8001/v1
YTEMO_FAST_MODEL=Qwen/Qwen3-4B
YTEMO_REASONING_BASE_URL=http://127.0.0.1:8002/v1
YTEMO_REASONING_MODEL=deepseek-ai/DeepSeek-R1-Distill-Qwen-7B
YTEMO_MEDICAL_BASE_URL=http://127.0.0.1:8003/v1
YTEMO_MEDICAL_MODEL=google/medgemma-1.5-4b-it
```

Chỉ bật MedGemma sau khi chấp thuận terms. Không phải mọi máy chủ có thể chạy ba model cùng lúc. Bắt đầu bằng một model quantized, đo VRAM/RAM và latency, sau đó mới mở rộng.

## 4. Training

Cài dependencies riêng trên máy GPU:
```bash
pip install -r backend/requirements-training.txt
```

Tạo dataset chỉ từ records đã được review:
```bash
cd backend
python -m clinical_training.prepare_dataset --input path/to/reviewed_records.jsonl
```

Chạy QLoRA trên CUDA:
```bash
python -m clinical_training.train_lora --model Qwen/Qwen3-4B --dataset artifacts/clinical_sft.jsonl --output-dir artifacts/qwen3-4b-qlora --qlora
```

Không có GPU tương thích thì không chạy QLoRA. Training dependencies không được cài trên backend web.

## 5. Đo tốc độ và chất lượng

Benchmark base và fine-tuned endpoint bằng cùng bộ case:
```bash
BENCH_BASE_URL=http://127.0.0.1:8001/v1 \
BENCH_BASE_MODEL=base-model \
BENCH_TUNED_URL=http://127.0.0.1:8002/v1 \
BENCH_TUNED_MODEL=fine-tuned-model \
python -m clinical_training.benchmark --cases clinical_training/benchmark_cases.template.jsonl --output artifacts/clinical_benchmark_blinded.jsonl --key-output artifacts/restricted_benchmark_key.jsonl
```

Runner đo latency và xuất hai file: A/B outputs cho reviewers, cùng unblinding key riêng chỉ người quản trị benchmark được giữ. Không chia sẻ key cho reviewers trước khi khóa điểm. Runner không tự động kết luận mô hình đúng về lâm sàng.

## 6. Giới hạn

- “Miễn phí” ở đây là model weights/inference software và hosted free quota; self-host vẫn cần phần cứng và điện.
- Free hosted model không đảm bảo ổn định, riêng tư hoặc tốc độ.
- Model weights, LoRA adapter và benchmark không phải chứng nhận lâm sàng.
- Không bật diagnosis/prescription cho bệnh nhân trước khi hoàn thành kiểm định và phê duyệt.


## 7. Tổng hợp điểm review A/B sau khi khóa đánh giá

Reviewers chấm file A/B bằng rubric 0–2, kèm reviewer_id và xác nhận độc lập. Schema xem docstring của `backend/clinical_training/score_benchmark.py`.

```bash
cd backend
python -m clinical_training.score_benchmark \
  --blinded artifacts/clinical_benchmark_blinded.jsonl \
  --key artifacts/restricted_benchmark_key.jsonl \
  --reviews artifacts/independent_reviews.jsonl \
  --output artifacts/clinical_benchmark_score_report.json
```

Script chỉ unblind khi mỗi case có ít nhất hai reviewer độc lập đã xác minh. Báo cáo so sánh base/fine-tuned theo từng dimension và scenario group; không cấp trạng thái clinical-ready.
