-- Durable, owner-scoped action proposals and temporal jobs.
-- Apply through Supabase migrations before enabling action endpoints/workers.
create table if not exists public.companion_action_tasks (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references auth.users(id) on delete cascade,
    action_type text not null,
    arguments jsonb not null default '{}'::jsonb,
    status text not null default 'awaiting_approval'
        check (status in ('awaiting_approval','queued','running','completed','failed','rejected','cancelled')),
    requires_approval boolean not null default true,
    idempotency_key text not null,\n    scheduled_at timestamptz not null default now(),
    result jsonb,
    last_error text,
    approved_at timestamptz,
    created_at timestamptz not null default now(),
    completed_at timestamptz,
    unique(user_id, idempotency_key)
);

create index if not exists companion_action_tasks_user_created_idx
    on public.companion_action_tasks(user_id, created_at desc);
create index if not exists companion_action_tasks_queue_idx
    on public.companion_action_tasks(status, created_at)
    where status = 'queued';

alter table public.companion_action_tasks enable row level security;
-- Browser access is intentionally denied; API uses the server-side secret key
-- and enforces owner checks in every query.
revoke all on public.companion_action_tasks from anon, authenticated;

create or replace function public.claim_companion_action_tasks(p_now timestamptz, p_limit integer default 10)
returns setof public.companion_action_tasks
language plpgsql
security definer
set search_path = public
as $$
begin
  return query
  with candidates as (
    select id
    from public.companion_action_tasks
    where status = 'queued'
      and (approved_at is not null or requires_approval = false)
    order by created_at
    for update skip locked
    limit greatest(1, least(p_limit, 50))
  )
  update public.companion_action_tasks t
     set status = 'running'
    from candidates c
   where t.id = c.id
  returning t.*;
end;
$$;
revoke all on function public.claim_companion_action_tasks(timestamptz, integer) from public, anon, authenticated;
grant execute on function public.claim_companion_action_tasks(timestamptz, integer) to service_role;
