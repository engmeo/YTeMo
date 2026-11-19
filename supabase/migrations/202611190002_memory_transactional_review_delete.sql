create or replace function public.memory_update_with_audit(
    p_memory_id uuid,
    p_user_id uuid,
    p_values jsonb,
    p_audit jsonb,
    p_expected_status text default null
)
returns jsonb
language plpgsql
set search_path = pg_catalog, public
as $$
declare
    v_previous jsonb;
    v_saved jsonb;
    v_audit jsonb;
begin
    if p_user_id is null or p_memory_id is null then
        raise exception 'Memory ID and owner user ID are required';
    end if;

    if p_values is null
       or jsonb_typeof(p_values) is distinct from 'object'
       or p_audit is null
       or jsonb_typeof(p_audit) is distinct from 'object' then
        raise exception 'Values and audit must be JSON objects';
    end if;

    -- Strict allowlist: no other memory columns may be changed.
    if exists (
        select 1
          from jsonb_object_keys(p_values) as item(key)
         where item.key not in (
             'status',
             'verification_state',
             'reviewed_by',
             'reviewed_at',
             'deleted_at',
             'updated_at'
         )
    ) then
        raise exception 'Unsupported memory update field';
    end if;

    if coalesce(p_audit->>'action', '') not in
       ('ACTIVATED', 'REJECTED', 'DELETED') then
        raise exception 'Unsupported memory audit action';
    end if;

    if coalesce(p_audit->>'actor_type', '') not in ('HUMAN', 'SYSTEM')
       or nullif(trim(p_audit->>'actor_id'), '') is null then
        raise exception 'A valid audit actor is required';
    end if;

    -- Enforce lifecycle transition/action consistency.
    if p_audit->>'action' in ('ACTIVATED', 'REJECTED')
       and p_expected_status is distinct from 'CANDIDATE' then
        raise exception 'Review actions require CANDIDATE status';
    end if;

    if p_audit->>'action' = 'ACTIVATED'
       and p_values->>'status' is distinct from 'ACTIVE' then
        raise exception 'ACTIVATED requires ACTIVE status';
    end if;

    if p_audit->>'action' = 'REJECTED'
       and p_values->>'status' is distinct from 'REJECTED' then
        raise exception 'REJECTED requires REJECTED status';
    end if;

    if p_audit->>'action' = 'DELETED'
       and (
           p_values->>'status' is distinct from 'ARCHIVED'
           or not (p_values ? 'deleted_at')
       ) then
        raise exception 'DELETED requires ARCHIVED status and deleted_at';
    end if;

    if p_values ? 'deleted_at'
       and nullif(p_values->>'deleted_at', '') is null then
        raise exception 'deleted_at must contain a timestamp';
    end if;

    -- Lock the exact owner-scoped row before checking and updating it.
    select to_jsonb(m)
      into v_previous
      from public.agent_memories m
     where m.id = p_memory_id
       and m.owner_type = 'USER'
       and m.user_id = p_user_id
       and m.deleted_at is null
       and (p_expected_status is null or m.status = p_expected_status)
     for update;

    if v_previous is null then
        raise exception 'Memory not found or update not permitted';
    end if;

    update public.agent_memories m
       set status = coalesce(p_values->>'status', m.status),
           verification_state = coalesce(
               p_values->>'verification_state', m.verification_state
           ),
           reviewed_by = case
               when p_values ? 'reviewed_by' then p_values->>'reviewed_by'
               else m.reviewed_by
           end,
           reviewed_at = case
               when p_values ? 'reviewed_at'
               then (p_values->>'reviewed_at')::timestamptz
               else m.reviewed_at
           end,
           deleted_at = case
               when p_values ? 'deleted_at'
               then (p_values->>'deleted_at')::timestamptz
               else m.deleted_at
           end,
           updated_at = coalesce(
               (p_values->>'updated_at')::timestamptz, now()
           )
     where m.id = p_memory_id
       and m.owner_type = 'USER'
       and m.user_id = p_user_id
       and m.deleted_at is null
       and (p_expected_status is null or m.status = p_expected_status)
    returning to_jsonb(m) into v_saved;

    if v_saved is null then
        raise exception 'Memory update lost its owner/status condition';
    end if;

    v_audit := p_audit || jsonb_build_object(
        'memory_id', p_memory_id,
        'previous_state', jsonb_build_object(
            'status', v_previous->'status',
            'verification_state', v_previous->'verification_state',
            'deleted_at', v_previous->'deleted_at'
        ),
        'new_state', jsonb_build_object(
            'status', v_saved->'status',
            'verification_state', v_saved->'verification_state',
            'deleted_at', v_saved->'deleted_at'
        ),
        'created_at', now()
    );

    insert into public.agent_memory_audit (
        memory_id,
        action,
        actor_type,
        actor_id,
        previous_state,
        new_state,
        reason,
        created_at
    )
    values (
        (v_audit->>'memory_id')::uuid,
        v_audit->>'action',
        v_audit->>'actor_type',
        v_audit->>'actor_id',
        v_audit->'previous_state',
        v_audit->'new_state',
        v_audit->>'reason',
        (v_audit->>'created_at')::timestamptz
    );

    return v_saved;
end;
$$;

revoke all on function public.memory_update_with_audit(
    uuid, uuid, jsonb, jsonb, text
) from public, anon, authenticated;

grant execute on function public.memory_update_with_audit(
    uuid, uuid, jsonb, jsonb, text
) to service_role;
