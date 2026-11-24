-- Backend accesses document metadata with the server-side Supabase secret key.
-- Browser roles remain governed by existing table grants and owner-scoped policies.
grant all on table public.healthcare_documents to service_role;
revoke all on table public.healthcare_documents from public, anon;
