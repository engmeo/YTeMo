-- Evidence-grade Clinical Knowledge foundation (additive migration).
-- Does not ingest, approve, or clinically validate any document.
alter table public.clinical_knowledge_documents
  add column if not exists knowledge_domain text,
  add column if not exists jurisdiction text,
  add column if not exists target_population text,
  add column if not exists evidence_level text,
  add column if not exists recommendation_strength text,
  add column if not exists official_identifier text,
  add column if not exists source_locator text,
  add column if not exists limitations text,
  add column if not exists source_domain_matched boolean not null default false;

-- A host match is not document authentication. Retire the misleading legacy flag.
update public.clinical_knowledge_documents set source_verified = false;
comment on column public.clinical_knowledge_documents.source_verified is
  'Legacy field retained for compatibility; must remain false. Domain match is not document-level verification.';
comment on column public.clinical_knowledge_documents.source_domain_matched is
  'Only indicates URL hostname matches a registered source domain; not proof of document authenticity or clinical validity.';
comment on column public.clinical_knowledge_documents.status is
  'CLINICAL_APPROVED requires human review evidence; high-impact domains require two independent reviewers.';

alter table public.clinical_knowledge_reviewers
  add column if not exists credential_type text,
  add column if not exists credential_identifier text,
  add column if not exists credential_verified boolean not null default false,
  add column if not exists credential_verified_at timestamptz,
  add column if not exists credential_verified_by uuid;

alter table public.clinical_knowledge_reviews
  add column if not exists source_document_verified boolean not null default false,
  add column if not exists version_current boolean not null default false,
  add column if not exists license_cleared boolean not null default false,
  add column if not exists evidence_assessment text not null default '',
  add column if not exists limitations text not null default '';

create unique index if not exists uq_ck_one_approval_per_reviewer
  on public.clinical_knowledge_reviews(document_id, reviewer_id)
  where decision = 'APPROVED';

create table if not exists public.clinical_knowledge_domains (
  domain_key text primary key,
  name text not null,
  description text not null,
  risk_level text not null check (risk_level in ('LOW','MODERATE','HIGH','CRITICAL')),
  required_reviewers integer not null default 1 check (required_reviewers >= 1),
  is_active boolean not null default true,
  created_at timestamptz not null default now()
);

insert into public.clinical_knowledge_domains(domain_key,name,description,risk_level,required_reviewers) values
('national_guidelines','Vietnam National Clinical Guidelines','Hướng dẫn chẩn đoán, điều trị, quy trình kỹ thuật và văn bản chuyên môn do cơ quan có thẩm quyền Việt Nam ban hành/công nhận.','HIGH',2),
('who_guidelines','WHO Clinical Guidelines','Khuyến nghị lâm sàng và y tế công cộng có quy trình phát triển hướng dẫn và thẩm định bằng chứng.','HIGH',2),
('specialty_guidelines','International Specialty Guidelines','Hướng dẫn của hội chuyên ngành; phải đánh giá khả năng áp dụng tại Việt Nam và xung đột với quy định trong nước.','HIGH',2),
('medication','Medication Knowledge & Pharmacovigilance','Tờ hướng dẫn sử dụng được phê duyệt tại Việt Nam, thông tin thuốc, chống chỉ định, tương tác, cảnh báo và cảnh giác dược.','CRITICAL',2),
('health_education','Reviewed Health Education','Tài liệu giáo dục sức khỏe đã được biên tập/thẩm định, có đối tượng và mục đích sử dụng rõ ràng.','MODERATE',1),
('diagnostics','Diagnostics & Clinical Reference','Tiêu chí chẩn đoán, xét nghiệm, chẩn đoán hình ảnh, khoảng tham chiếu theo phòng xét nghiệm và quy trình theo dõi.','HIGH',2),
('prevention_public_health','Prevention & Public Health','Tiêm chủng, sàng lọc, dự phòng, dinh dưỡng, sức khỏe bà mẹ-trẻ em và y tế công cộng.','MODERATE',1)
on conflict(domain_key) do update set name=excluded.name,description=excluded.description,
  risk_level=excluded.risk_level,required_reviewers=excluded.required_reviewers;

create table if not exists public.clinical_terminology_systems (
  terminology_key text primary key,
  name text not null,
  purpose text not null,
  official_url text,
  licensing_notes text not null default '',
  implementation_status text not null default 'PLANNED'
    check (implementation_status in ('PLANNED','EVALUATING','LICENSE_CLEARED','IMPLEMENTED')),
  created_at timestamptz not null default now()
);

insert into public.clinical_terminology_systems(terminology_key,name,purpose,official_url,licensing_notes) values
('ICD10','ICD-10','Phân loại bệnh tật; duy trì tương thích dữ liệu và quy định đang dùng tại Việt Nam.','https://www.who.int/standards/classifications/classification-of-diseases','Kiểm tra phiên bản và điều kiện sử dụng theo nguồn phát hành.'),
('ICD11','ICD-11','Phân loại bệnh tật quốc tế thế hệ mới và khả năng liên thông.','https://icd.who.int/','Đánh giá triển khai, mapping và yêu cầu phiên bản.'),
('ATC','ATC/DDD','Phân loại thuốc theo giải phẫu-điều trị-hóa học; không thay thế dữ liệu kê đơn/nhãn thuốc.','https://www.whocc.no/atc_ddd_index/','Kiểm tra điều kiện sử dụng và cập nhật của WHOCC.'),
('LOINC','LOINC','Mã hóa xét nghiệm và quan sát lâm sàng.','https://loinc.org/','Xác nhận điều khoản và phiên bản trước khi phân phối.'),
('SNOMED_CT','SNOMED CT','Thuật ngữ lâm sàng có ngữ nghĩa chi tiết.','https://www.snomed.org/','Phải xác minh quyền thành viên, lãnh thổ và giấy phép trước khi sử dụng.'),
('UCUM','UCUM','Chuẩn biểu diễn đơn vị đo lường trong y tế.','https://ucum.org/','Kiểm tra bản phát hành và điều khoản áp dụng.')
on conflict(terminology_key) do update set name=excluded.name,purpose=excluded.purpose,
  official_url=excluded.official_url,licensing_notes=excluded.licensing_notes;

create table if not exists public.clinical_evidence_claims (
  id uuid primary key default gen_random_uuid(),
  document_id uuid not null references public.clinical_knowledge_documents(id) on delete cascade,
  claim_text text not null,
  claim_type text not null check (claim_type in ('DIAGNOSIS','SCREENING','TREATMENT','MEDICATION_SAFETY','PROGNOSIS','PREVENTION','PUBLIC_HEALTH','OTHER')),
  population text not null,
  intervention text,
  comparator text,
  outcomes text[] not null default '{}',
  effect_estimate text,
  certainty text,
  recommendation_strength text,
  source_locator text not null,
  reviewer_status text not null default 'UNREVIEWED'
    check (reviewer_status in ('UNREVIEWED','ACCEPTED','REJECTED','NEEDS_REVISION')),
  created_at timestamptz not null default now(),
  reviewed_at timestamptz,
  reviewed_by uuid
);
create index if not exists idx_ck_claims_document on public.clinical_evidence_claims(document_id);

create table if not exists public.clinical_evidence_conflicts (
  id uuid primary key default gen_random_uuid(),
  topic_key text not null,
  jurisdiction text not null,
  population text not null,
  claim_ids uuid[] not null,
  conflict_summary text not null,
  resolution_status text not null default 'OPEN'
    check (resolution_status in ('OPEN','UNDER_REVIEW','RESOLVED','UNRESOLVED')),
  resolution_rationale text,
  resolved_by uuid,
  resolved_at timestamptz,
  created_at timestamptz not null default now()
);

alter table public.clinical_knowledge_domains enable row level security;
alter table public.clinical_terminology_systems enable row level security;
alter table public.clinical_evidence_claims enable row level security;
alter table public.clinical_evidence_conflicts enable row level security;
