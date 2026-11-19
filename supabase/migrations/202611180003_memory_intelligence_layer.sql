-- Y TE MO: Memory Intelligence Layer v1
-- Additive migration; requires 202611180002_agent_memory_engine.sql.
-- Conflict detection preserves all claims. It does not decide clinical truth.

begin;

alter table public.agent_memories
    add column if not exists subject_key text,
    add column if not exists fact_key text,
    add column if not exists last_verified_at timestamptz,
    add column if not exists verification_method text;

create index if not exists agent_memories_subject_fact_idx
    on public.agent_memories (owner_type, user_id, agent_key, subject_key, fact_key)
    where deleted_at is null;

create index if not exists agent_memories_temporal_owner_idx
    on public.agent_memories (owner_type, user_id, agent_key, valid_from desc)
    where deleted_at is null;

create table if not exists public.memory_evidence (
    id uuid primary key default gen_random_uuid(),
    memory_id uuid not null references public.agent_memories(id) on delete restrict,
    evidence_type text not null check (evidence_type in (
        'USER_STATEMENT', 'CLINICAL_RECORD', 'CLINICIAN_REVIEW',
        'EXTERNAL_DOCUMENT', 'DEVICE_MEASUREMENT', 'AGENT_OUTPUT', 'TOOL_OUTPUT'
    )),
    source_ref text,
    source_type text not null,
    source_metadata jsonb not null default '{}'::jsonb,
    content_hash text,
    excerpt_or_locator text,
    observed_at timestamptz,
    captured_at timestamptz not null default now(),
    provided_by text,
    verification_state text not null default 'UNVERIFIED'
        check (verification_state in ('UNVERIFIED', 'SUPPORTED', 'REVIEWED', 'VERIFIED', 'DISPUTED')),
    sensitivity text not null default 'NORMAL'
        check (sensitivity in ('NORMAL', 'PERSONAL', 'HEALTH', 'HIGH')),
    consent_scope text,
    metadata jsonb not null default '{}'::jsonb
);
create index if not exists memory_evidence_memory_time_idx
    on public.memory_evidence (memory_id, captured_at desc);
create index if not exists memory_evidence_source_idx
    on public.memory_evidence (source_type, source_ref);

create table if not exists public.memory_conflicts (
    id uuid primary key default gen_random_uuid(),
    owner_type text not null check (owner_type in ('USER', 'AGENT', 'TENANT', 'SHARED')),
    user_id uuid references auth.users(id) on delete restrict,
    tenant_id uuid,
    agent_key text,
    subject_key text not null,
    fact_key text,
    conflict_type text not null check (conflict_type in (
        'VALUE_MISMATCH', 'TEMPORAL_CHANGE', 'SOURCE_DISAGREEMENT',
        'DUPLICATE_WITH_VARIATION', 'MISSING_VS_NEGATIVE', 'SCOPE_MISMATCH', 'OTHER'
    )),
    status text not null default 'OPEN' check (status in (
        'OPEN', 'UNDER_REVIEW', 'RESOLVED', 'UNRESOLVED', 'NOT_A_CONFLICT', 'SUPERSEDED'
    )),
    severity text not null default 'NORMAL'
        check (severity in ('LOW', 'NORMAL', 'HIGH', 'CRITICAL')),
    detection_method text not null default 'RULE_BASED',
    detection_metadata jsonb not null default '{}'::jsonb,
    resolution_method text,
    resolution_summary text,
    resolution_metadata jsonb not null default '{}'::jsonb,
    reviewed_by text,
    reviewed_at timestamptz,
    detected_at timestamptz not null default now(),
    resolved_at timestamptz,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    check (
        (owner_type = 'USER' and user_id is not null)
        or (owner_type = 'AGENT' and agent_key is not null)
        or (owner_type = 'TENANT' and tenant_id is not null)
        or (owner_type = 'SHARED' and user_id is null and tenant_id is null)
    )
);
create index if not exists memory_conflicts_owner_status_idx
    on public.memory_conflicts (owner_type, user_id, agent_key, status, detected_at desc);
create index if not exists memory_conflicts_subject_idx
    on public.memory_conflicts (subject_key, fact_key, status);

create table if not exists public.memory_conflict_items (
    id uuid primary key default gen_random_uuid(),
    conflict_id uuid not null references public.memory_conflicts(id) on delete cascade,
    memory_id uuid not null references public.agent_memories(id) on delete restrict,
    side_label text not null default 'UNSPECIFIED'
        check (side_label in ('CLAIM_A', 'CLAIM_B', 'CONTEXT', 'UNSPECIFIED')),
    relevance text,
    created_at timestamptz not null default now(),
    unique (conflict_id, memory_id)
);
create index if not exists memory_conflict_items_memory_idx
    on public.memory_conflict_items (memory_id);

create table if not exists public.memory_versions (
    id uuid primary key default gen_random_uuid(),
    memory_id uuid not null references public.agent_memories(id) on delete restrict,
    version_number integer not null check (version_number > 0),
    snapshot jsonb not null,
    change_type text not null check (change_type in (
        'CREATED', 'CONTENT_UPDATED', 'STATUS_CHANGED',
        'VERIFICATION_CHANGED', 'TEMPORAL_UPDATED', 'OTHER'
    )),
    change_reason text,
    changed_by_type text not null default 'SYSTEM',
    changed_by_id text,
    created_at timestamptz not null default now(),
    unique (memory_id, version_number)
);
create index if not exists memory_versions_memory_time_idx
    on public.memory_versions (memory_id, version_number desc);

create table if not exists public.memory_derivations (
    id uuid primary key default gen_random_uuid(),
    derived_memory_id uuid not null references public.agent_memories(id) on delete restrict,
    source_memory_id uuid not null references public.agent_memories(id) on delete restrict,
    source_role text not null default 'INPUT',
    transformation text not null,
    model_or_agent text,
    derivation_metadata jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now(),
    check (derived_memory_id <> source_memory_id),
    unique (derived_memory_id, source_memory_id, source_role)
);
create index if not exists memory_derivations_source_idx
    on public.memory_derivations (source_memory_id);
create index if not exists memory_derivations_derived_idx
    on public.memory_derivations (derived_memory_id);

create table if not exists public.memory_resolution_policies (
    id uuid primary key default gen_random_uuid(),
    policy_key text not null,
    owner_type text not null default 'SHARED'
        check (owner_type in ('USER', 'AGENT', 'TENANT', 'SHARED')),
    memory_type text,
    conflict_type text,
    policy_version integer not null default 1 check (policy_version > 0),
    policy jsonb not null default '{}'::jsonb,
    enabled boolean not null default true,
    requires_human_review boolean not null default true,
    created_by text,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    unique (policy_key, owner_type, policy_version)
);

create table if not exists public.memory_consolidation_jobs (
    id uuid primary key default gen_random_uuid(),
    owner_type text not null check (owner_type in ('USER', 'AGENT', 'TENANT', 'SHARED')),
    user_id uuid references auth.users(id) on delete restrict,
    tenant_id uuid,
    agent_key text,
    status text not null default 'QUEUED'
        check (status in ('QUEUED', 'RUNNING', 'COMPLETED', 'FAILED', 'CANCELLED')),
    job_type text not null default 'CONSOLIDATE',
    input_count integer not null default 0 check (input_count >= 0),
    output_count integer not null default 0 check (output_count >= 0),
    candidate_memory_ids uuid[] not null default '{}',
    result_metadata jsonb not null default '{}'::jsonb,
    error_summary text,
    requested_by text,
    started_at timestamptz,
    completed_at timestamptz,
    created_at timestamptz not null default now(),
    check (
        (owner_type = 'USER' and user_id is not null)
        or (owner_type = 'AGENT' and agent_key is not null)
        or (owner_type = 'TENANT' and tenant_id is not null)
        or (owner_type = 'SHARED' and user_id is null and tenant_id is null)
    )
);
create index if not exists memory_consolidation_queue_idx
    on public.memory_consolidation_jobs (status, created_at)
    where status in ('QUEUED', 'RUNNING');
create index if not exists memory_consolidation_owner_idx
    on public.memory_consolidation_jobs (owner_type, user_id, agent_key, created_at desc);

alter table public.memory_evidence enable row level security;
alter table public.memory_conflicts enable row level security;
alter table public.memory_conflict_items enable row level security;
alter table public.memory_versions enable row level security;
alter table public.memory_derivations enable row level security;
alter table public.memory_resolution_policies enable row level security;
alter table public.memory_consolidation_jobs enable row level security;

revoke all on table
    public.memory_evidence, public.memory_conflicts, public.memory_conflict_items,
    public.memory_versions, public.memory_derivations, public.memory_resolution_policies,
    public.memory_consolidation_jobs
from public, anon, authenticated;

grant all on table
    public.memory_evidence, public.memory_conflicts, public.memory_conflict_items,
    public.memory_versions, public.memory_derivations, public.memory_resolution_policies,
    public.memory_consolidation_jobs
to service_role;

comment on table public.memory_conflicts is
    'Conflict cases; detection never deletes or silently overwrites involved memories.';
comment on table public.memory_evidence is
    'Evidence provenance attached to a memory; store references/locators, not unnecessary raw patient data.';
comment on table public.memory_versions is
    'Append-only snapshots; application must create a version for each material update.';
comment on table public.memory_derivations is
    'Lineage from derived memories to source memories; derived claims are not automatically verified.';
comment on table public.memory_resolution_policies is
    'Declarative rules; high-risk clinical conflicts require qualified human review.';
comment on table public.memory_consolidation_jobs is
    'Consolidation may create candidates but must not self-verify them.';

commit;
