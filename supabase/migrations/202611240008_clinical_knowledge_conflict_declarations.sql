alter table public.clinical_evidence_conflict_reviews
  add column if not exists has_conflict_of_interest boolean not null default false;
alter table public.clinical_knowledge_document_relation_reviews
  add column if not exists has_conflict_of_interest boolean not null default false;
