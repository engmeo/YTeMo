-- Correct claim RPC batch bound under an empty search_path.
-- LEAST/GREATEST are SQL special expressions, not schema-qualified functions.
create or replace function public.claim_companion_action_tasks(
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
     limit case
         when p_limit is null or p_limit < 1 then 1
         when p_limit > 50 then 50
         else p_limit
     end
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
