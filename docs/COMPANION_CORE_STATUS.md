# Companion Core v1 — implementation status

## Included

- A user-scoped companion state model.
- Consent records with deny-by-default behavior.
- Separate consent scopes for profile, care needs, health context, follow-up, and proactive contact.
- Context storage and retrieval gated by the relevant consent.
- Revoking consent hides context from retrieval; explicit context deletion is also supported.
- Support-need tracking with user-declared priority and lifecycle status.
- Follow-up event recording behind follow-up consent.
- Snapshot summary without returning sensitive context content.
- Repository protocol to allow a future Supabase-backed adapter.
- Deterministic unit tests.

## Deliberately not included

- No production database adapter. `InMemoryCompanionRepository` loses data when the process exits.
- No authentication, authorization middleware, API routes, background scheduler, or proactive messaging.
- No LLM, medical knowledge retrieval, diagnosis, triage, prescription, or treatment decisions.
- No automatic inference of clinical urgency. `user_priority` is only the priority stated by the user.
- No clinical validation or production security certification.

## Run tests

From the backend directory:

```powershell
python -m unittest -v test_companion_core
```

Expected: 14 tests pass.
