# Proactive Engine v1 — status

## Implemented

- Event-driven evaluation with explicit trigger types.
- Consent gate for proactive contact.
- Separate consent gates for care-needs and follow-up data.
- Creates reviewable proposals, not outbound messages.
- Detects user-recorded needs in `in_progress` or `waiting` state when a next step exists.
- Avoids duplicate active proposals for the same need.
- Enforces per-evaluation and per-user active proposal limits.
- Allows proposals to be accepted, dismissed, or expired by a caller.
- Deterministic unit tests.

## Not implemented

- No background scheduler or event bus.
- No SMS, email, push, or chat message delivery.
- No automatic language-model interpretation of user messages.
- No clinical urgency detection, diagnosis, or treatment recommendations.
- No durable proposal storage; in-memory repository is for local tests only.
- No production API integration.

`PROPOSED` means a suggestion was created for the application to display or review.
It does not mean the user was contacted or agreed to an action.
