create table if not exists public.clinical_knowledge_sources (
 id uuid primary key default gen_random_uuid(), source_key text not null unique,
 name text not null, base_url text not null, source_type text not null,
 country text not null default 'VN', trust_tier text not null default 'B' check (trust_tier in ('A','B','C')),
 is_active boolean not null default true, created_at timestamptz not null default now(),
 updated_at timestamptz not null default now()
);
create table if not exists public.clinical_knowledge_documents (
 id uuid primary key default gen_random_uuid(), source_id uuid references public.clinical_knowledge_sources(id),
 title text not null, publisher text not null, document_type text not null, source_url text not null,
 published_at text not null, effective_from text, effective_until text, version text,
 language text not null default 'vi', specialty text, license_status text not null default 'unknown',
 source_verified boolean not null default false, automated_checks jsonb not null default '{}'::jsonb,
 content_hash text, extracted_text text,
 status text not null default 'DISCOVERED' check (status in ('DISCOVERED','SOURCE_VERIFIED','PROCESSING','AI_REVIEWED','CLINICAL_APPROVED','SUPERSEDED','REJECTED')),
 approved_scope text[] not null default '{}', created_by uuid, reviewed_by uuid, reviewed_at timestamptz,
 created_at timestamptz not null default now(), updated_at timestamptz not null default now()
);
create index if not exists idx_ck_documents_status_created on public.clinical_knowledge_documents(status, created_at desc);
create index if not exists idx_ck_documents_hash on public.clinical_knowledge_documents(content_hash);
create table if not exists public.clinical_knowledge_reviewers (
 user_id uuid primary key, role text not null check (role in ('physician','pharmacist','clinical_reviewer','knowledge_admin')),
 specialties text[] not null default '{}', is_active boolean not null default true, granted_by uuid,
 created_at timestamptz not null default now()
);
create table if not exists public.clinical_knowledge_reviews (
 id uuid primary key default gen_random_uuid(), document_id uuid not null references public.clinical_knowledge_documents(id) on delete cascade,
 reviewer_id uuid not null, reviewer_role text not null, decision text not null check (decision in ('APPROVED','REJECTED','REQUEST_REVISION')),
 rationale text not null, approved_scope text[] not null default '{}', created_at timestamptz not null default now()
);
create index if not exists idx_ck_reviews_document on public.clinical_knowledge_reviews(document_id, created_at desc);
create table if not exists public.clinical_knowledge_audit (
 id uuid primary key default gen_random_uuid(), document_id uuid references public.clinical_knowledge_documents(id) on delete set null,
 actor_id uuid, action text not null, details jsonb not null default '{}'::jsonb, created_at timestamptz not null default now()
);
create index if not exists idx_ck_audit_document on public.clinical_knowledge_audit(document_id, created_at desc);
insert into public.clinical_knowledge_sources(source_key,name,base_url,source_type,country,trust_tier)
values ('moh_vn','Bộ Y tế Việt Nam','https://moh.gov.vn','government','VN','A'),
('who','World Health Organization','https://www.who.int','intergovernmental','GLOBAL','A')
on conflict(source_key) do update set name=excluded.name,base_url=excluded.base_url,
source_type=excluded.source_type,country=excluded.country,trust_tier=excluded.trust_tier,updated_at=now();
alter table public.clinical_knowledge_sources enable row level security;
alter table public.clinical_knowledge_documents enable row level security;
alter table public.clinical_knowledge_reviewers enable row level security;
alter table public.clinical_knowledge_reviews enable row level security;
alter table public.clinical_knowledge_audit enable row level security;
