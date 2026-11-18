# Companion Core — integration contract

## Architectural role

`CompanionCore` owns the durable companion-state use cases, not the user interface.
The future companion experience should call this layer through authenticated API services.
Specialist agents should receive only the minimum context needed for their assigned task.

## Consent model

All scopes default to not granted:

- `basic_profile`
- `care_needs`
- `health_context`
- `follow_up`
- `proactive_contact`

Before saving or retrieving a context item, the corresponding scope must be granted.
Revocation immediately makes existing items in that scope unavailable through `get_context`.
Revocation does not physically erase old records; use explicit deletion and define a retention
policy before production deployment.

## Important production requirements

Before connecting Supabase or real users:

1. Implement a Supabase repository with strict `user_id` ownership filters and database RLS.
2. Never trust a user_id supplied by the browser; derive it from the verified auth session.
3. Store consent version, purpose, timestamp, actor, and policy text/version.
4. Add export, deletion, retention, audit, and recovery workflows.
5. Encrypt sensitive data at rest and in transit; minimize data sent to external model providers.
6. Add a separate policy gate for proactive contact, quiet hours, channel preferences, and opt-out.
7. Do not treat this module as a clinical decision engine.

## Next implementation increments

- Supabase-backed repository and schema/migrations.
- Companion API endpoints protected by the existing authenticated user dependency.
- Event-driven proactive engine, only for users who explicitly enable proactive contact.
- Agent orchestration that supplies consent-filtered context to specialist agents.
