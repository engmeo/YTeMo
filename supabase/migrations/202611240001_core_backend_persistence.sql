-- Y TE MO - STT15: Core backend persistence
-- Additive/idempotent baseline for tables used by main.py and AgentCore.
-- This file is added to the repository only. It is NOT applied to Supabase.
-- Backend must authenticate the user and scope every query by user_id.
-- The browser must never receive SUPABASE_SECRET_KEY.

begin;

create table if not exists public.conversations (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references auth.users(id) on delete cascade,
    title text not null default 'Cuoc tro chuyen',
    status text not null default 'active',
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create table if not exists public.messages (
    id uuid primary key default gen_random_uuid(),
    conversation_id uuid not null
        references public.conversations(id) on delete cascade,
    sender_type text not null,
    content text not null,
    created_at timestamptz not null default now()
);

create table if not exists public.agent_tasks (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references auth.users(id) on delete cascade,
    conversation_id uuid
        references public.conversations(id) on delete set null,
    goal text not null,
    status text not null default 'queued'
        check (status in ('queued', 'running', 'completed', 'failed', 'cancelled')),
    plan jsonb not null default '[]'::jsonb,
    result jsonb,
    error text,
    lease_token text,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create table if not exists public.agent_task_steps (
    id uuid primary key default gen_random_uuid(),
    task_id uuid not null
        references public.agent_tasks(id) on delete cascade,
    step_key text not null,
    title text,
    tool_name text,
    input jsonb not null default '{}'::jsonb,
    status text not null default 'queued'
        check (status in ('queued', 'running', 'completed', 'failed', 'skipped')),
    output jsonb,
    attempts integer not null default 0 check (attempts >= 0),
    completed_at timestamptz,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    constraint agent_task_steps_task_key_unique unique (task_id, step_key)
);

create table if not exists public.agent_task_events (
    id uuid primary key default gen_random_uuid(),
    task_id uuid not null
        references public.agent_tasks(id) on delete cascade,
    event_type text not null,
    payload jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now()
);

create index if not exists conversations_user_updated_idx
    on public.conversations (user_id, updated_at desc);

create index if not exists messages_conversation_created_idx
    on public.messages (conversation_id, created_at);

create index if not exists agent_tasks_user_created_idx
    on public.agent_tasks (user_id, created_at desc);

create index if not exists agent_tasks_status_updated_idx
    on public.agent_tasks (status, updated_at);

create index if not exists agent_task_steps_task_created_idx
    on public.agent_task_steps (task_id, created_at);

create index if not exists agent_task_events_task_created_idx
    on public.agent_task_events (task_id, created_at);

-- These tables are accessed through the authenticated backend only.
-- Backend derives user_id from the verified Supabase session.
alter table public.conversations enable row level security;
alter table public.messages enable row level security;
alter table public.agent_tasks enable row level security;
alter table public.agent_task_steps enable row level security;
alter table public.agent_task_events enable row level security;

revoke all on table
    public.conversations,
    public.messages,
    public.agent_tasks,
    public.agent_task_steps,
    public.agent_task_events
from public, anon, authenticated;

grant all on table
    public.conversations,
    public.messages,
    public.agent_tasks,
    public.agent_task_steps,
    public.agent_task_events
to service_role;

comment on table public.conversations is
    'Conversation metadata; ownership is enforced by authenticated backend queries.';
comment on table public.messages is
    'Conversation messages; access is mediated through the owning conversation.';
comment on table public.agent_tasks is
    'Durable, user-scoped AgentCore tasks with lease-based worker ownership.';
comment on table public.agent_task_steps is
    'Durable per-task execution steps for resume and idempotent progression.';
comment on table public.agent_task_events is
    'Append-oriented lifecycle events for AgentCore task observability.';

commit;
