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
  `{"action":"create_reminder","arguments":{"title":"Tái khám","due_at":"2026-12-01T09:00:00+07:00"}}`
- `GET /companion/actions`
- `POST /companion/actions/{action_id}/approve`
- `POST /companion/actions/{action_id}/reject`

The current allowlist is intentionally small:

- `create_reminder`
- `request_clinician_review`
- `add_timeline_note`

The last two are proposals only. A handler must be explicitly implemented and registered before a worker can execute an action type. Unknown action types fail closed.

## Apply and operate

1. Apply `supabase/migrations/202611240001_companion_action_tasks.sql` in the target Supabase project.
2. Deploy the backend containing the API routes.
3. Run a separate worker process only after registering reviewed handlers:
   `python -m temporal_action_worker` is not a standalone entrypoint yet; use a small deployment entrypoint that creates the service-role Supabase client and calls `serve(db)`.
4. Configure exactly one worker deployment initially. The database claim RPC prevents two workers from claiming the same queued row concurrently.

Do not expose the Supabase service-role key to the browser. The API checks ownership on every action read/update. RLS is enabled and browser roles have no table privileges.

## Safety and current limitations

- The LLM may suggest an action but never approves it.
- User approval is persisted separately from proposal creation.
- Reminders are scheduled at `due_at`; they are not a notification delivery integration yet.
- No email, SMS, hospital booking, prescription, medication change, or clinical order handler is enabled.
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
