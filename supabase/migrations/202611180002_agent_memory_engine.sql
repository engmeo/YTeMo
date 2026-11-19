begin;

-- 1. Agent identity and version registry
create table if not exists public.agent_memory_agents (
    id uuid primary key default gen_random_uuid(),
    agent_key text not null,
    display_name text not null,
    version text not null default '1.0.0',
    description text,
    capabilities jsonb not null default '[]'::jsonb,
    memory_policy jsonb not null default '{}'::jsonb,
    enabled boolean not null default true,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    unique (agent_key, version)
);

-- 2. Unified memory store
create table if not exists public.agent_memories (
    id uuid primary key default gen_random_uuid(),

    -- Isolation boundary
    owner_type text not null check (
        owner_type in ('USER', 'AGENT', 'TENANT', 'SHARED')
    ),
    user_id uuid references auth.users(id) on delete cascade,
    tenant_id uuid,
    agent_key text,

    -- Memory classification
    memory_type text not null check (
        memory_type in (
            'WORKING',
            'EPISODIC',
            'SEMANTIC',
            'PROCEDURAL',
            'RELATIONAL',
            'SHARED_KNOWLEDGE'
        )
    ),

    -- Content and provenance
    content jsonb not null,
    summary text,
    source_type text not null,
    source_ref text,
    source_metadata jsonb not null default '{}'::jsonb,

    -- Trust and review
    status text not null default 'CANDIDATE' check (
        status in ('CANDIDATE', 'ACTIVE', 'SUPERSEDED', 'REJECTED', 'ARCHIVED')
    ),
    verification_state text not null default 'UNVERIFIED' check (
        verification_state in (
            'UNVERIFIED', 'SUPPORTED', 'REVIEWED', 'VERIFIED', 'DISPUTED'
        )
    ),
    confidence numeric(5,4) check (
        confidence is null or (confidence >= 0 and confidence <= 1)
    ),
    sensitivity text not null default 'NORMAL' check (
        sensitivity in ('NORMAL', 'PERSONAL', 'HEALTH', 'HIGH')
    ),

    -- Consent and access scope
    consent_scope text,
    access_policy jsonb not null default '{}'::jsonb,

    -- Temporal memory
    valid_from timestamptz,
    valid_until timestamptz,
    observed_at timestamptz,
    recorded_at timestamptz not null default now(),
    expires_at timestamptz,

    -- Deduplication and lifecycle
    dedupe_hash text,
    supersedes_id uuid references public.agent_memories(id),
    created_by_agent text,
    reviewed_by text,
    reviewed_at timestamptz,
    metadata jsonb not null default '{}'::jsonb,

    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),

    constraint agent_memories_owner_check check (
        (owner_type = 'USER' and user_id is not null)
        or (owner_type = 'AGENT' and agent_key is not null)
        or (owner_type = 'TENANT' and tenant_id is not null)
        or (owner_type = 'SHARED' and user_id is null and tenant_id is null)
    )
);

-- 3. Explicit relations between memories
create table if not exists public.agent_memory_relations (
    id uuid primary key default gen_random_uuid(),
    from_memory_id uuid not null references public.agent_memories(id) on delete cascade,
    to_memory_id uuid not null references public.agent_memories(id) on delete cascade,
    relation_type text not null,
    confidence numeric(5,4) check (
        confidence is null or (confidence >= 0 and confidence <= 1)
    ),
    source_ref text,
    created_by_agent text,
    created_at timestamptz not null default now(),
    unique (from_memory_id, to_memory_id, relation_type),
    check (from_memory_id <> to_memory_id)
);

-- 4. Append-only memory audit trail
create table if not exists public.agent_memory_audit (
    id uuid primary key default gen_random_uuid(),
    memory_id uuid not null references public.agent_memories(id) on delete cascade,
    action text not null check (
        action in (
            'CREATED', 'UPDATED', 'ACTIVATED', 'REVIEWED',
            'REJECTED', 'SUPERSEDED', 'ARCHIVED', 'DELETED'
        )
    ),
    actor_type text not null,
    actor_id text,
    previous_state jsonb,
    new_state jsonb,
    reason text,
    created_at timestamptz not null default now()
);

-- Indexes for scoped and temporal retrieval
create index if not exists agent_memories_user_type_time_idx
    on public.agent_memories (user_id, memory_type, recorded_at desc)
    where owner_type = 'USER';

create index if not exists agent_memories_agent_type_time_idx
    on public.agent_memories (agent_key, memory_type, recorded_at desc)
    where owner_type = 'AGENT';

create index if not exists agent_memories_status_expiry_idx
    on public.agent_memories (status, expires_at);

create index if not exists agent_memories_validity_idx
    on public.agent_memories (valid_from, valid_until);

create index if not exists agent_memories_source_idx
    on public.agent_memories (source_type, source_ref);

create index if not exists agent_memory_relations_from_idx
    on public.agent_memory_relations (from_memory_id);

create index if not exists agent_memory_relations_to_idx
    on public.agent_memory_relations (to_memory_id);

create index if not exists agent_memory_audit_memory_time_idx
    on public.agent_memory_audit (memory_id, created_at desc);

-- Prevent duplicate active/candidate memories in the same ownership scope
create unique index if not exists agent_memories_user_dedupe_idx
    on public.agent_memories (user_id, agent_key, memory_type, dedupe_hash)
    where owner_type = 'USER'
      and dedupe_hash is not null
      and status in ('CANDIDATE', 'ACTIVE');

-- Backend-only access. Service key bypasses RLS, so backend must enforce
-- authentication, ownership, consent and access_policy on every operation.
alter table public.agent_memory_agents enable row level security;
alter table public.agent_memories enable row level security;
alter table public.agent_memory_relations enable row level security;
alter table public.agent_memory_audit enable row level security;

revoke all on table
    public.agent_memory_agents,
    public.agent_memories,
    public.agent_memory_relations,
    public.agent_memory_audit
from public, anon, authenticated;

grant all on table
    public.agent_memory_agents,
    public.agent_memories,
    public.agent_memory_relations,
    public.agent_memory_audit
to service_role;

comment on table public.agent_memories is
    'Agent memory store. Backend must enforce owner isolation, consent and provenance.';
comment on table public.agent_memory_audit is
    'Memory lifecycle audit trail. Do not use as a substitute for clinical verification.';
comment on table public.agent_memory_agents is
    'Versioned identities and memory policies for registered Y TE MO agents.';
-- YTEMO_MEMORY_SCHEMA_NORMALIZATION_V1
-- Soft-delete marker: retain memory history without exposing deleted records.
alter table public.agent_memories
    add column if not exists deleted_at timestamptz;

-- Keep audit history if a memory row is physically deleted.
do $$
declare c record;
begin
    for c in
        select conname
        from pg_constraint
        where conrelid = 'public.agent_memory_audit'::regclass
          and contype = 'f'
          and pg_get_constraintdef(oid) ilike '%memory_id%'
          and pg_get_constraintdef(oid) ilike '%agent_memories%'
    loop
        execute format(
            'alter table public.agent_memory_audit drop constraint %I',
            c.conname
        );
    end loop;
end $$;

-- One deduplication rule even when agent_key is NULL.
do $$
declare i record;
begin
    for i in
        select idx.relname as index_name
        from pg_index ix
        join pg_class tbl on tbl.oid = ix.indrelid
        join pg_class idx on idx.oid = ix.indexrelid
        where tbl.oid = 'public.agent_memories'::regclass
          and ix.indisunique
          and pg_get_indexdef(ix.indexrelid) ilike '%dedupe_hash%'
    loop
        execute format('drop index if exists public.%I', i.index_name);
    end loop;
end $$;

create unique index if not exists agent_memories_user_dedupe_v1_uidx
on public.agent_memories (
    user_id,
    (coalesce(agent_key, '')),
    memory_type,
    dedupe_hash
)
where owner_type = 'USER'
  and status in ('CANDIDATE', 'ACTIVE')
  and dedupe_hash is not null;

create index if not exists agent_memories_not_deleted_idx
on public.agent_memories (user_id, agent_key, updated_at desc)
where deleted_at is null and status = 'ACTIVE';

commit;

