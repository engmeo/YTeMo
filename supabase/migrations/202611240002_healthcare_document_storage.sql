-- Private medical-document storage. Backend uses SUPABASE_SECRET_KEY; never expose it to clients.
create table if not exists public.healthcare_documents (
  id uuid primary key,
  user_id uuid not null references auth.users(id) on delete cascade,
  filename text not null,
  media_type text not null,
  byte_size bigint not null check (byte_size > 0 and byte_size <= 10485760),
  storage_path text not null unique,
  extraction_status text not null default 'stored',
  created_at timestamptz not null default now()
);
create index if not exists healthcare_documents_user_created_idx
  on public.healthcare_documents(user_id, created_at desc);
alter table public.healthcare_documents enable row level security;
drop policy if exists healthcare_documents_select_own on public.healthcare_documents;
create policy healthcare_documents_select_own on public.healthcare_documents
  for select to authenticated using (auth.uid() = user_id);
drop policy if exists healthcare_documents_delete_own on public.healthcare_documents;
create policy healthcare_documents_delete_own on public.healthcare_documents
  for delete to authenticated using (auth.uid() = user_id);
insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values ('healthcare-documents', 'healthcare-documents', false, 10485760,
  array['application/pdf','application/vnd.openxmlformats-officedocument.wordprocessingml.document','text/plain','text/markdown'])
on conflict (id) do update set public = false, file_size_limit = 10485760,
  allowed_mime_types = excluded.allowed_mime_types;
