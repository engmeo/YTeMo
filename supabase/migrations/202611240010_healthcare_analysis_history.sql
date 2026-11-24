-- Owner-scoped history for completed healthcare document analyses.
-- Results are stored as user health data and are accessible only through the
-- authenticated backend using the server-side Supabase secret key.
create table if not exists public.healthcare_analysis_runs (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references auth.users(id) on delete cascade,
    source_document_id uuid references public.healthcare_documents(id) on delete set null,
    agent_keys jsonb not null default '[]'::jsonb,
    status text not null default 'completed'
        check (status in ('completed', 'partial', 'failed')),
    result jsonb not null,
    created_at timestamptz not null default now()
);

create index if not exists healthcare_analysis_runs_user_created_idx
    on public.healthcare_analysis_runs(user_id, created_at desc);
create index if not exists healthcare_analysis_runs_document_idx
    on public.healthcare_analysis_runs(source_document_id, created_at desc);

alter table public.healthcare_analysis_runs enable row level security;
revoke all on public.healthcare_analysis_runs from anon, authenticated;
grant all on public.healthcare_analysis_runs to service_role;
