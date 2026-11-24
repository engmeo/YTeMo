alter table public.clinical_evidence_claim_reviews
  add column if not exists source_quote_verified boolean not null default false;

alter table public.clinical_knowledge_document_relations
  add column if not exists review_status text not null default 'UNDER_REVIEW'
    check (review_status in ('UNDER_REVIEW','CONFIRMED','REJECTED'));

-- Independent confirmation for document-version links and evidence-conflict resolution.
create table if not exists public.clinical_knowledge_document_relation_reviews (
  id uuid primary key default gen_random_uuid(),
  relation_id uuid not null references public.clinical_knowledge_document_relations(id) on delete cascade,
  reviewer_id uuid not null,
  decision text not null check (decision in ('CONFIRM','REJECT')),
  rationale text not null,
  created_at timestamptz not null default now(),
  unique(relation_id, reviewer_id)
);

create table if not exists public.clinical_evidence_conflict_reviews (
  id uuid primary key default gen_random_uuid(),
  conflict_id uuid not null references public.clinical_evidence_conflicts(id) on delete cascade,
  reviewer_id uuid not null,
  decision text not null check (decision in ('RESOLVE','UNRESOLVED')),
  rationale text not null,
  created_at timestamptz not null default now(),
  unique(conflict_id, reviewer_id)
);

alter table public.clinical_knowledge_document_relation_reviews enable row level security;
alter table public.clinical_evidence_conflict_reviews enable row level security;
