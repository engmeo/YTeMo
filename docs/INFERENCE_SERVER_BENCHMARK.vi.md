# Benchmark inference server cho Y TẾ MỞ

## Mục tiêu và giới hạn

Tách model inference khỏi FastAPI/Vercel/Render. API gateway chỉ gọi endpoint OpenAI-compatible nội bộ. Chưa chọn GGUF Q4/Q5 hay AWQ/GPTQ cho tới khi biết model cụ thể, CPU/RAM/GPU/VRAM và hệ điều hành máy chủ.

## Chọn định dạng theo runtime

- **llama.cpp**: phù hợp chạy GGUF, có thể thử Q4_K_M và Q5_K_M. Dùng cùng một model family/revision và prompt set khi so sánh.
- **vLLM**: chỉ dùng AWQ/GPTQ khi kiến trúc model và phiên bản runtime hỗ trợ chính xác định dạng đó. Không giả định mọi model đều hỗ trợ mọi quantization.
- **Không trộn model khác nhau khi đo quantization**: so sánh cùng model, cùng tokenizer, cùng prompt, context length, sampling và concurrency.
- Q4/Q5 giảm bộ nhớ nhưng có thể giảm chất lượng; AWQ/GPTQ có hiệu năng phụ thuộc GPU/kernel. Không có lựa chọn nhanh nhất trên mọi máy.

## Benchmark latency

Script `backend/inference_latency_benchmark.py` gọi streaming `/v1/chat/completions` và ghi:
- TTFT (time to first token)
- tổng thời gian
- tokens/second (dùng usage từ server nếu có; nếu không, đánh dấu ước lượng)
- p50/p95 trên các lượt chạy
- toàn bộ output để reviewer so sánh mù

Chỉ dùng prompt tổng hợp hoặc đã khử định danh. Ví dụ:

```powershell
cd backend
$env:YTEMO_BENCHMARK_BASE_URL="http://127.0.0.1:8001/v1"
$env:YTEMO_BENCHMARK_MODEL="model-id-served"
python inference_latency_benchmark.py --prompts ..\docs\inference_benchmark_prompts.vi.jsonl --runs 5 --max-tokens 256 --output q4-results.json
```

Chạy lại chính prompt file đó cho Q5/AWQ/GPTQ, giữ nguyên cấu hình concurrency và warm-up. Không đưa API key vào command history; dùng biến môi trường.

## Chạy server

Ví dụ với llama.cpp (đường dẫn model là file GGUF đã tải và xác minh license):

```bash
llama-server --model /models/model-Q4_K_M.gguf --host 0.0.0.0 --port 8001 --ctx-size 8192 --n-gpu-layers 99
```

Nếu không có GPU, bỏ/giảm `--n-gpu-layers` và benchmark trên CPU; tốc độ có thể không phù hợp cho multi-agent. Với vLLM, tạo environment riêng, cài đúng phiên bản CUDA/vLLM và dùng model ID/quantization được model card xác nhận. Không cài weights vào API service.

## Đánh giá chất lượng

Không tự động coi perplexity hoặc tốc độ là clinical quality. Dùng cùng một bộ prompt, ẩn danh model/quantization và nhờ ít nhất hai reviewer độc lập chấm:
1. đúng dữ kiện và không tự bịa;
2. tiếng Việt, tính dễ hiểu;
3. tuân thủ giới hạn/abstention;
4. citation/provenance khi có evidence;
5. bỏ sót thông tin trọng yếu;
6. unsafe advice và mức độ nghiêm trọng.

So sánh Q4/Q5/AWQ/GPTQ với bản precision cao hơn của chính model đó. Chỉ bật model trong intended-use đã được đánh giá; benchmark kỹ thuật không phải xác nhận lâm sàng.

## Thông tin còn thiếu để dựng máy thật

Cần xác định: model/revision, RAM, GPU model + VRAM, CPU, OS, concurrent users, context length, latency target và ngân sách điện/máy chủ. Chưa có các dữ liệu này thì không thể chọn định dạng hoặc tuyên bố đã benchmark.
