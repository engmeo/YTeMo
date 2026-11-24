-- Durable, owner-scoped action proposals and retryable temporal jobs.
-- Apply through Supabase migrations before enabling action endpoints/workers.
create table if not exists public.companion_action_tasks (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references auth.users(id) on delete cascade,
    action_type text not null,
    arguments jsonb not null default '{}'::jsonb,
    status text not null default 'awaiting_approval'
        check (status in ('awaiting_approval','queued','running','completed','failed','rejected','cancelled')),
    requires_approval boolean not null default true,
    idempotency_key text not null,
    scheduled_at timestamptz not null default now(),
    result jsonb,
    last_error text,
    approved_at timestamptz,
    created_at timestamptz not null default now(),
    completed_at timestamptz,
    attempt_count integer not null default 0 check (attempt_count >= 0),
    max_attempts integer not null default 5 check (max_attempts between 1 and 10),
    next_attempt_at timestamptz,
    last_attempt_at timestamptz,
    lease_expires_at timestamptz,
    unique(user_id, idempotency_key)
);

alter table public.companion_action_tasks
    add column if not exists attempt_count integer not null default 0,
    add column if not exists max_attempts integer not null default 5,
    add column if not exists next_attempt_at timestamptz,
    add column if not exists last_attempt_at timestamptz,
    add column if not exists lease_expires_at timestamptz;

create index if not exists companion_action_tasks_user_created_idx
    on public.companion_action_tasks(user_id, created_at desc);
create index if not exists companion_action_tasks_queue_idx
    on public.companion_action_tasks(status, scheduled_at, next_attempt_at)
    where status in ('queued','running');

alter table public.companion_action_tasks enable row level security;
-- Browser access is intentionally denied; API and worker use server-side
-- secret credentials and enforce owner checks in application code.
revoke all on public.companion_action_tasks from public, anon, authenticated;
grant all on public.companion_action_tasks to service_role;

-- Approved review requests and timeline notes are persisted exactly once per action.
alter table public.companion_needs
    add column if not exists action_task_id uuid
    references public.companion_action_tasks(id) on delete cascade;
alter table public.companion_events
    add column if not exists action_task_id uuid
    references public.companion_action_tasks(id) on delete cascade;
create unique index if not exists companion_needs_action_task_id_uidx
    on public.companion_needs(action_task_id) where action_task_id is not null;
create unique index if not exists companion_events_action_task_id_uidx
    on public.companion_events(action_task_id) where action_task_id is not null;

drop function if exists public.claim_companion_action_tasks(timestamptz, integer);

create function public.claim_companion_action_tasks(
    p_now timestamptz,
    p_limit integer,
    p_action_types text[]
)
returns setof public.companion_action_tasks
language plpgsql
security definer
set search_path = ''
as $$
begin
  -- Expired leases that exhausted their retry budget must not remain running forever.
  update public.companion_action_tasks
     set status = 'failed',
         last_error = 'Worker lease expired after maximum attempts.',
         completed_at = p_now,
         lease_expires_at = null
   where status = 'running'
     and lease_expires_at <= p_now
     and attempt_count >= max_attempts;

  return query
  with candidates as (
    select t.id
      from public.companion_action_tasks as t
     where (
            (t.status = 'queued'
             and t.scheduled_at <= p_now
             and coalesce(t.next_attempt_at, t.scheduled_at) <= p_now)
            or
            (t.status = 'running' and t.lease_expires_at <= p_now)
           )
       and t.attempt_count < t.max_attempts
       and t.action_type = any(p_action_types)
       and (t.approved_at is not null or t.requires_approval = false)
     order by t.created_at
     for update skip locked
     limit pg_catalog.greatest(1, pg_catalog.least(p_limit, 50))
  )
  update public.companion_action_tasks as t
     set status = 'running',
         attempt_count = t.attempt_count + 1,
         last_attempt_at = p_now,
         lease_expires_at = p_now + interval '3 minutes',
         next_attempt_at = null
    from candidates as c
   where t.id = c.id
  returning t.*;
end;
$$;
revoke all on function public.claim_companion_action_tasks(timestamptz, integer, text[]) from public, anon, authenticated;
grant execute on function public.claim_companion_action_tasks(timestamptz, integer, text[]) to service_role;
