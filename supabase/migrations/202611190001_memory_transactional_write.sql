create or replace function public.memory_write_with_audit(
    p_memory jsonb,
    p_audit jsonb
)
returns jsonb
language plpgsql
set search_path = pg_catalog, public
as $$
declare
    v_memory jsonb;
    v_audit jsonb;
    v_saved jsonb;
begin
    if jsonb_typeof(p_memory) <> 'object'
       or jsonb_typeof(p_audit) <> 'object' then
        raise exception 'Memory and audit payloads must be JSON objects';
    end if;

    -- Supply database defaults for fields populated through JSON records.
    v_memory := p_memory || jsonb_build_object(
        'id', coalesce(p_memory->>'id', gen_random_uuid()::text),
        'recorded_at', coalesce(p_memory->>'recorded_at', now()::text),
        'created_at', coalesce(p_memory->>'created_at', now()::text),
        'updated_at', coalesce(p_memory->>'updated_at', now()::text),
        'source_metadata', coalesce(p_memory->'source_metadata', '{}'::jsonb),
        'access_policy', coalesce(p_memory->'access_policy', '{}'::jsonb),
        'metadata', coalesce(p_memory->'metadata', '{}'::jsonb)
    );

    insert into public.agent_memories
    select (jsonb_populate_record(
        null::public.agent_memories, v_memory
    )).*
    returning to_jsonb(agent_memories) into v_saved;

    -- The audit memory_id is always taken from the inserted database row.
    v_audit := p_audit || jsonb_build_object(
        'memory_id', v_saved->>'id',
        'created_at', coalesce(p_audit->>'created_at', now()::text)
    );

    insert into public.agent_memory_audit (
        memory_id, action, actor_type, actor_id,
        previous_state, new_state, reason, created_at
    ) values (
        (v_audit->>'memory_id')::uuid,
        v_audit->>'action',
        v_audit->>'actor_type',
        v_audit->>'actor_id',
        v_audit->'previous_state',
        v_audit->'new_state',
        v_audit->>'reason',
        coalesce((v_audit->>'created_at')::timestamptz, now())
    );

    return v_saved;
end;
$$;

revoke all on function public.memory_write_with_audit(jsonb, jsonb)
    from public, anon, authenticated;
grant execute on function public.memory_write_with_audit(jsonb, jsonb)
    to service_role;
