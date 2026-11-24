# Companion Agent Actions & Temporal Runtime

## What this adds

- An allowlisted action proposal API; LLMs cannot execute arbitrary Python, SQL, HTTP, or shell commands.
- Explicit owner approval before any action enters the worker queue.
- Owner-scoped Supabase records and idempotency keys.
- Scheduled execution timestamps; reminders are not claimable before their due time.
- A separate polling worker. Do not run it inside a FastAPI request or on every web replica.
- Atomic queue claiming through `claim_companion_action_tasks` using `FOR UPDATE SKIP LOCKED`.

## API

All endpoints require the user's Supabase access token:

- `POST /companion/actions/propose`
  `{"action":"create_reminder","arguments":{"title":"Tái khám","due_at":"2026-12-01T09:00:00+07:00","delivery_channel":"email"}}`
- `GET /companion/actions`
- `POST /companion/actions/{action_id}/approve`
- `POST /companion/actions/{action_id}/reject`

The current allowlist is intentionally small:

- `create_reminder`
- `request_clinician_review`
- `add_timeline_note`

The last two are proposals only. A handler must be explicitly implemented and registered before a worker can execute an action type. Unknown action types fail closed.

## Apply and operate

1. Apply `supabase/migrations/202611240009_companion_action_tasks.sql` and `supabase/migrations/202611240010_healthcare_analysis_history.sql` in order in the target Supabase project.
2. Deploy the backend containing the API routes.
3. Configure the separate worker service with `SUPABASE_URL`, `SUPABASE_SECRET_KEY`, `RESEND_API_KEY`, `RESEND_FROM_EMAIL` and optional `YTEMO_ACTION_POLL_SECONDS`.
4. Run `python companion_action_worker_service.py` from the `backend` directory. It registers the `create_reminder` email handler and refuses to start without Resend configuration.
5. Configure exactly one worker deployment initially. The database claim RPC prevents two workers from claiming the same queued row concurrently.

Do not expose the Supabase service-role key to the browser. The API checks ownership on every action read/update. RLS is enabled and browser roles have no table privileges.

## Safety and current limitations

- The LLM may suggest an action but never approves it.
- User approval is persisted separately from proposal creation.
- Reminders are scheduled at `due_at`. The Resend handler sends email only when the proposal explicitly sets `delivery_channel: "email"` and the owner has a verified Supabase Auth email.
- Email delivery is implemented as an opt-in Resend worker handler, but it is not active until the worker and provider credentials are configured. No SMS, hospital booking, prescription, medication change, or clinical order handler is enabled.
- `request_clinician_review` and `add_timeline_note` remain queued proposals until a separately reviewed handler is registered.
- A failed worker handler is recorded as failed; automatic retries/dead-letter policy and operator dashboard remain follow-up work.
- This is workflow infrastructure, not clinical validation or autonomous medical decision-making.

## Quantized inference

The existing Model Gateway can target OpenAI-compatible local servers. Recommended deployment split:

- API: CPU/lightweight web service; no model weights loaded in FastAPI.
- Inference: separate GPU/CPU host running llama.cpp server (GGUF Q4_K_M/Q5_K_M) or vLLM with a supported AWQ/GPTQ/FP8 format.
- Profiles: small fast model for routing/formatting; stronger specialist/reasoning model only for tasks that need it.
- Benchmark each candidate on Vietnamese quality, tool-call validity, TTFT, inter-token latency, p50/p95 latency, peak VRAM/RAM and clinical safety regression.

Quantization is not automatically faster on every device. Do not enable a quantized model for clinical use until its quality has been compared against the same model in higher precision on an expert-adjudicated evaluation set.


## Gửi email nhắc lịch bằng Resend

Worker gửi email chỉ xử lý `create_reminder` và chỉ khi request có `delivery_channel: "email"`; lựa chọn kênh phải được người dùng xác nhận trước khi phê duyệt hành động. Worker lấy địa chỉ email từ Supabase Auth, yêu cầu email đã xác minh, không nhận địa chỉ gửi đến tùy ý từ LLM.

Cấu hình ở dịch vụ worker (không đặt trên frontend): `SUPABASE_URL`, `SUPABASE_SECRET_KEY`, `RESEND_API_KEY`, `RESEND_FROM_EMAIL`, tùy chọn `YTEMO_ACTION_POLL_SECONDS`. Chạy `python -m backend.companion_action_worker_service` từ thư mục gốc repo hoặc `python companion_action_worker_service.py` trong `backend`.

Các action `request_clinician_review` và `add_timeline_note` chưa có handler thực thi; worker sẽ fail-closed, không giả lập thành công. Không bật worker trước khi migration được áp dụng và Resend domain/from address được xác minh.
