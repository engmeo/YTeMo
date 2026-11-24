-- Clinical Evidence Intelligence: vector/hybrid retrieval, KG, source refresh queue and benchmark registry.
create extension if not exists vector with schema extensions;

create table if not exists public.clinical_evidence_embeddings (
  claim_id uuid primary key references public.clinical_evidence_claims(id) on delete cascade,
  embedding extensions.vector(768) not null,
  embedding_model text not null,
  embedding_input_sha256 text not null,
  embedded_at timestamptz not null default now()
);
create index if not exists idx_ck_evidence_embedding_hnsw
  on public.clinical_evidence_embeddings using hnsw (embedding extensions.vector_cosine_ops);

create table if not exists public.clinical_evidence_graph_entities (
  id uuid primary key default gen_random_uuid(),
  entity_type text not null check (entity_type in ('CONDITION','SYMPTOM','MEDICATION','LAB_TEST','PROCEDURE','POPULATION','OUTCOME','GUIDELINE')),
  canonical_name text not null,
  terminology_system text,
  terminology_code text,
  language text not null default 'en',
  created_at timestamptz not null default now(),
  unique(entity_type, canonical_name, terminology_system, terminology_code)
);
create table if not exists public.clinical_evidence_graph_edges (
  id uuid primary key default gen_random_uuid(),
  source_entity_id uuid not null references public.clinical_evidence_graph_entities(id) on delete cascade,
  target_entity_id uuid not null references public.clinical_evidence_graph_entities(id) on delete cascade,
  relation_type text not null check (relation_type in ('HAS_SYMPTOM','TREATED_BY','CONTRAINDICATED_WITH','MONITORED_BY','ASSESSED_BY','APPLIES_TO','HAS_OUTCOME','SUPPORTED_BY')),
  claim_id uuid references public.clinical_evidence_claims(id) on delete set null,
  document_id uuid references public.clinical_knowledge_documents(id) on delete set null,
  assertion_status text not null default 'CANDIDATE' check (assertion_status in ('CANDIDATE','REVIEWED','REJECTED')),
  provenance jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  check(source_entity_id <> target_entity_id)
);
create index if not exists idx_ck_graph_edges_source on public.clinical_evidence_graph_edges(source_entity_id);
create index if not exists idx_ck_graph_edges_target on public.clinical_evidence_graph_edges(target_entity_id);

create table if not exists public.clinical_knowledge_source_sync_runs (
  id uuid primary key default gen_random_uuid(),
  source_id uuid not null references public.clinical_knowledge_sources(id) on delete restrict,
  status text not null default 'QUEUED' check(status in ('QUEUED','RUNNING','SUCCEEDED','PARTIAL','FAILED')),
  started_at timestamptz,
  finished_at timestamptz,
  discovered_count integer not null default 0,
  new_candidate_count integer not null default 0,
  error_summary text,
  created_at timestamptz not null default now()
);
create table if not exists public.clinical_evidence_benchmark_cases (
  id uuid primary key default gen_random_uuid(),
  case_key text not null unique,
  query text not null,
  jurisdiction text not null,
  population text not null,
  scope text not null,
  expected_claim_ids uuid[] not null default '{}',
  excluded_claim_ids uuid[] not null default '{}',
  expected_abstention boolean not null default false,
  provenance jsonb not null default '{}'::jsonb,
  adjudication_status text not null default 'UNREVIEWED' check(adjudication_status in ('UNREVIEWED','PUBLIC_SOURCE_CURATED','EXPERT_ADJUDICATED','RETIRED')),
  reviewer_ids uuid[] not null default '{}',
  last_evaluated_at timestamptz,
  created_at timestamptz not null default now(),
  check(adjudication_status <> 'EXPERT_ADJUDICATED' or cardinality(reviewer_ids) >= 2)
);

alter table public.clinical_evidence_embeddings enable row level security;
alter table public.clinical_evidence_graph_entities enable row level security;
alter table public.clinical_evidence_graph_edges enable row level security;
alter table public.clinical_knowledge_source_sync_runs enable row level security;
alter table public.clinical_evidence_benchmark_cases enable row level security;

create or replace function public.match_clinical_evidence(
  query_embedding extensions.vector(768),
  match_count integer default 30,
  min_similarity double precision default 0.25
)
returns table (
  claim_id uuid, similarity double precision, claim_text text, exact_quote text,
  document_id uuid, title text, publisher text, source_url text, version text,
  source_page_number integer, jurisdiction text, population text, approved_scope text[]
)
language sql stable security invoker set search_path = public, extensions
as $$
  select c.id, 1 - (e.embedding <=> query_embedding) as similarity,
    c.claim_text, c.exact_quote, d.id, d.title, d.publisher, d.source_url, d.version,
    c.source_page_number, d.jurisdiction, c.population, d.approved_scope
  from clinical_evidence_embeddings e
  join clinical_evidence_claims c on c.id=e.claim_id
  join clinical_knowledge_documents d on d.id=c.document_id
  where c.reviewer_status='ACCEPTED'
    and d.status='CLINICAL_APPROVED' and d.is_current=true
    and 1 - (e.embedding <=> query_embedding) >= min_similarity
  order by e.embedding <=> query_embedding
  limit greatest(1, least(match_count, 100));
$$;
