-- Use explicit pending-second-review states; do not overload AI_REVIEWED/UNREVIEWED.
alter table public.clinical_knowledge_documents
  drop constraint if exists clinical_knowledge_documents_status_check;
alter table public.clinical_knowledge_documents
  add constraint clinical_knowledge_documents_status_check
  check (status in (
    'DISCOVERED','SOURCE_VERIFIED','PROCESSING','AI_REVIEWED',
    'CLINICAL_REVIEW_PENDING_SECOND','CLINICAL_APPROVED','SUPERSEDED','REJECTED'
  ));

alter table public.clinical_evidence_claims
  drop constraint if exists clinical_evidence_claims_reviewer_status_check;
alter table public.clinical_evidence_claims
  add constraint clinical_evidence_claims_reviewer_status_check
  check (reviewer_status in (
    'UNREVIEWED','PENDING_SECOND_REVIEW','ACCEPTED','REJECTED','NEEDS_REVISION'
  ));

comment on column public.clinical_knowledge_documents.status is
  'AI_REVIEWED is reserved for AI assistance; CLINICAL_REVIEW_PENDING_SECOND means one required human approval has been recorded and an independent reviewer is still needed.';
