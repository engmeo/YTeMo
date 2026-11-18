# Proactive Engine — integration and safety contract

## Usage

Place `proactive_engine.py` beside `companion_core.py` in the backend package.

```python
from companion_core import CompanionCore, ConsentScope, InMemoryCompanionRepository
from proactive_engine import (
    InMemoryProposalRepository, ProactiveEngine, TriggerEvent, TriggerType
)

core = CompanionCore(InMemoryCompanionRepository())
engine = ProactiveEngine(core, InMemoryProposalRepository())
```

The in-memory repositories are test-only. Do not use them for real patient data.

## Event contract

A trusted backend event source calls `evaluate(TriggerEvent(...))`.
Do not accept arbitrary `user_id` or trigger claims from an unauthenticated browser.
Derive the user identity from the verified authentication session.

Supported triggers:
- `user_returned`
- `user_requested_follow_up`
- `scheduled_review`
- `task_completed`
- `need_status_changed`

## Consent gates

- `proactive_contact` is always required to create a proactive proposal.
- `care_needs` is additionally required before inspecting unresolved care needs.
- `follow_up` is additionally required for a user-requested follow-up proposal.

Granting one scope does not grant another. Consent revocation should be checked on every
evaluation, not cached in a background worker.

## Safety boundaries

- This engine creates proposals only. A separate delivery component must check consent,
  quiet hours, channel preference, rate limits, and opt-out immediately before sending.
- The engine does not interpret symptoms or assign clinical urgency.
- If emergency language is detected by a future component, it must use a separate,
  clinically reviewed safety pathway; do not route emergencies through routine follow-up.
- Never use model-generated hypotheses as confirmed user facts.
- Keep evaluation bounded; the configured limits cap proposal generation.
- Production implementation needs durable storage, audit logs, retention rules, RLS,
  and authenticated API ownership checks.
