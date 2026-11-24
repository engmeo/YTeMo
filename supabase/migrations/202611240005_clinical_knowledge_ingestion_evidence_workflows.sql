-- Controlled Clinical Knowledge ingestion, immutable source snapshots, page provenance,
-- claim-level appraisal/review, and auditable document version relations.
alter table public.clinical_knowledge_sources
  add column if not exists discovery_url text,
  add column if not exists fetch_enabled boolean not null default true;

alter table public.clinical_knowledge_documents
  add column if not exists canonical_url text,
  add column if not exists original_storage_path text unique,
  add column if not exists original_sha256 text,
  add column if not exists original_byte_size bigint,
  add column if not exists media_type text,
  add column if not exists fetched_at timestamptz,
  add column if not exists extraction_status text not null default 'NOT_STARTED',
  add column if not exists extraction_report jsonb not null default '{}'::jsonb,
  add column if not exists page_count integer,
  add column if not exists is_current boolean not null default true,
  add column if not exists identity_verified_at timestamptz,
  add column if not exists identity_verified_by uuid,
  add column if not exists superseded_by uuid references public.clinical_knowledge_documents(id);

create table if not exists public.clinical_knowledge_discovery_candidates (
  id uuid primary key default gen_random_uuid(),
  source_id uuid not null references public.clinical_knowledge_sources(id) on delete restrict,
  discovery_url text not null,
  canonical_url text not null,
  link_text text not null default '',
  status text not null default 'DISCOVERED'
    check (status in ('DISCOVERED','INGESTED','REJECTED','DUPLICATE','FAILED')),
  document_id uuid references public.clinical_knowledge_documents(id) on delete set null,
  discovered_at timestamptz not null default now(),
  reviewed_at timestamptz,
  reviewed_by uuid,
  unique(source_id, canonical_url)
);

create table if not exists public.clinical_knowledge_document_pages (
  id uuid primary key default gen_random_uuid(),
  document_id uuid not null references public.clinical_knowledge_documents(id) on delete cascade,
  page_number integer not null check (page_number > 0),
  page_text text not null default '',
  text_sha256 text not null,
  extraction_status text not null,
  extraction_method text not null,
  quality_report jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  unique(document_id, page_number)
);
create index if not exists idx_ck_pages_document_page
  on public.clinical_knowledge_document_pages(document_id, page_number);

alter table public.clinical_evidence_claims
  add column if not exists source_page_number integer,
  add column if not exists exact_quote text,
  add column if not exists extraction_method text not null default 'MANUAL',
  add column if not exists appraisal_framework text,
  add column if not exists appraisal jsonb not null default '{}'::jsonb,
  add column if not exists required_reviewers integer not null default 2,
  add column if not exists approved_scope text[] not null default '{}',
  add column if not exists jurisdiction text,
  add column if not exists reviewed_at timestamptz,
  add column if not exists created_by uuid;

create table if not exists public.clinical_evidence_claim_reviews (
  id uuid primary key default gen_random_uuid(),
  claim_id uuid not null references public.clinical_evidence_claims(id) on delete cascade,
  reviewer_id uuid not null,
  reviewer_role text not null,
  decision text not null check (decision in ('ACCEPTED','REJECTED','NEEDS_REVISION')),
  appraisal_framework text not null,
  appraisal jsonb not null default '{}'::jsonb,
  rationale text not null,
  has_conflict_of_interest boolean not null default false,
  created_at timestamptz not null default now()
);
create unique index if not exists uq_ck_claim_reviewer_decision
  on public.clinical_evidence_claim_reviews(claim_id, reviewer_id);

create table if not exists public.clinical_knowledge_document_relations (
  id uuid primary key default gen_random_uuid(),
  predecessor_document_id uuid not null references public.clinical_knowledge_documents(id) on delete restrict,
  successor_document_id uuid not null references public.clinical_knowledge_documents(id) on delete restrict,
  relation_type text not null check (relation_type in ('SUPERSEDES','UPDATE_OF','CORRECTION_OF','TRANSLATION_OF')),
  rationale text not null,
  verified_by uuid not null,
  created_at timestamptz not null default now(),
  check (predecessor_document_id <> successor_document_id),
  unique(predecessor_document_id, successor_document_id, relation_type)
);

alter table public.clinical_knowledge_discovery_candidates enable row level security;
alter table public.clinical_knowledge_document_pages enable row level security;
alter table public.clinical_evidence_claim_reviews enable row level security;
alter table public.clinical_knowledge_document_relations enable row level security;

-- Private source originals. Uploads use content-addressed paths and upsert=false.
-- This prevents accidental replacement through the application API; it is not
-- a legal/WORM retention lock against privileged project administrators.
insert into storage.buckets(id,name,public,file_size_limit,allowed_mime_types)
values ('clinical-knowledge-originals','clinical-knowledge-originals',false,26214400,
  array['application/pdf','text/html','application/xhtml+xml'])
on conflict(id) do update set public=false,file_size_limit=26214400,
  allowed_mime_types=excluded.allowed_mime_types;

comment on table public.clinical_knowledge_document_pages is
  'Page-level extracted text and quality diagnostics; quality metrics do not certify clinical correctness.';
comment on column public.clinical_knowledge_documents.original_sha256 is
  'SHA-256 of fetched original bytes; integrity marker, not proof of publisher authenticity.';
comment on column public.clinical_knowledge_documents.original_storage_path is
  'Private, content-addressed storage path. Application never overwrites an existing original.';

-- Official landing pages are discovery starting points, not pre-approved documents.
update public.clinical_knowledge_sources set discovery_url='https://moh.gov.vn/', fetch_enabled=true where source_key='moh_vn';
update public.clinical_knowledge_sources set discovery_url='https://www.who.int/publications/who-guidelines', fetch_enabled=true where source_key='who';
update public.clinical_knowledge_sources set discovery_url='https://www.escardio.org/Guidelines', fetch_enabled=true where source_key='esc';
update public.clinical_knowledge_sources set discovery_url='https://kdigo.org/guidelines/', fetch_enabled=true where source_key='kdigo';
update public.clinical_knowledge_sources set discovery_url='https://ginasthma.org/', fetch_enabled=true where source_key='gina';
update public.clinical_knowledge_sources set discovery_url='https://goldcopd.org/', fetch_enabled=true where source_key='gold';
update public.clinical_knowledge_sources set discovery_url='https://diabetes.org/', fetch_enabled=true where source_key='ada';
update public.clinical_knowledge_sources set discovery_url='https://dav.gov.vn/', fetch_enabled=true where source_key='dav_vn';
