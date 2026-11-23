$ErrorActionPreference = 'Stop'
$root = (Get-Location).Path
if (-not (Test-Path (Join-Path $root 'backend\main.py'))) { throw 'Hay chay script tai thu muc goc repository C:\YTeMo.' }
$stamp = Get-Date -Format 'yyyyMMdd_HHmmss'
$backup = Join-Path $root ".stt16_backup_$stamp"
New-Item -ItemType Directory -Path $backup | Out-Null
Copy-Item (Join-Path $root 'backend\main.py') $backup
$migDir = Join-Path $root 'supabase\migrations'
New-Item -ItemType Directory -Force -Path $migDir | Out-Null
$migration = Join-Path $migDir '202611240002_healthcare_document_storage.sql'
if (Test-Path $migration) { throw "Migration da ton tai: $migration. Dung de tranh ghi de." }
$sql = @'
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
'@
Set-Content -Path $migration -Value $sql -Encoding UTF8
$mainPath = Join-Path $root 'backend\main.py'
$main = (Get-Content $mainPath -Raw) -replace "`r`n", "`n"
if ($main -match '/healthcare/documents\"\]') { throw 'Khong the xac dinh trang thai route an toan; dung de tranh patch trung.' }
if ($main.Contains('healthcare_documents_user_created_idx') -or $main.Contains('STT16_PERSISTENT_STORAGE')) { throw 'Co dau vet STT16 storage patch truoc do; khong patch lap.' }
$main = $main.Replace('import os', "import os`nimport uuid`nfrom pathlib import Path")
$old = @'
@app.post("/healthcare/documents/extract")
async def extract_healthcare_document(
    file: UploadFile = File(...),
    user=Depends(get_current_user),
):
    # Read one byte beyond the limit so oversized uploads are rejected early.
    try:
        data = await file.read(MAX_DOCUMENT_BYTES + 1)
        if len(data) > MAX_DOCUMENT_BYTES:
            raise HTTPException(status_code=413, detail="File vượt giới hạn 10 MB.")
        extracted = extract_medical_document(file.filename or "document", data)
        return {
            "document": extracted.to_dict(),
            "next_step": "Gửi document.text đến POST /healthcare/agents/run để chạy các Specialist Agents.",
        }
    except DocumentExtractionError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    finally:
        await file.close()
'@
$new = @'
# STT16_PERSISTENT_STORAGE: private bucket + owner-scoped metadata.
@app.post("/healthcare/documents/extract")
async def extract_healthcare_document(file: UploadFile = File(...), user=Depends(get_current_user)):
    data = await file.read(MAX_DOCUMENT_BYTES + 1)
    await file.close()
    if len(data) > MAX_DOCUMENT_BYTES:
        raise HTTPException(status_code=413, detail="File vượt giới hạn 10 MB.")
    try:
        extracted = extract_medical_document(file.filename or "document", data)
    except DocumentExtractionError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    document_id = str(uuid.uuid4())
    safe_name = Path(extracted.filename).name
    storage_path = f"{user.id}/{document_id}/{safe_name}"
    try:
        db_client.storage.from_("healthcare-documents").upload(
            storage_path, data, {"content-type": extracted.media_type, "upsert": "false"}
        )
        row = {
            "id": document_id, "user_id": str(user.id), "filename": safe_name,
            "media_type": extracted.media_type, "byte_size": len(data),
            "storage_path": storage_path, "extraction_status": extracted.extraction_status,
        }
        db_client.table("healthcare_documents").insert(row).execute()
    except Exception as exc:
        try:
            db_client.storage.from_("healthcare-documents").remove([storage_path])
        except Exception:
            pass
        print("HEALTHCARE DOCUMENT STORAGE ERROR:", repr(exc), flush=True)
        raise HTTPException(status_code=503, detail="Không thể lưu hồ sơ y tế. Kiểm tra migration và Storage bucket.") from exc
    result = extracted.to_dict()
    result.update({"id": document_id, "persisted": True, "byte_size": len(data)})
    return {"document": result, "next_step": "Gửi document.text đến POST /healthcare/agents/run để chạy các Specialist Agents."}

@app.get("/healthcare/documents")
def list_healthcare_documents(user=Depends(get_current_user)):
    try:
        result = (db_client.table("healthcare_documents").select(
            "id,filename,media_type,byte_size,extraction_status,created_at"
        ).eq("user_id", str(user.id)).order("created_at", desc=True).execute())
        return {"documents": result.data or []}
    except Exception as exc:
        print("HEALTHCARE DOCUMENT LIST ERROR:", repr(exc), flush=True)
        raise HTTPException(status_code=503, detail="Không thể đọc danh sách hồ sơ.") from exc

@app.delete("/healthcare/documents/{document_id}")
def delete_healthcare_document(document_id: str, user=Depends(get_current_user)):
    try:
        found = (db_client.table("healthcare_documents").select("id,storage_path")
                 .eq("id", document_id).eq("user_id", str(user.id)).limit(1).execute())
        if not found.data:
            raise HTTPException(status_code=404, detail="Không tìm thấy hồ sơ.")
        path = found.data[0]["storage_path"]
        db_client.storage.from_("healthcare-documents").remove([path])
        db_client.table("healthcare_documents").delete().eq("id", document_id).eq("user_id", str(user.id)).execute()
        return {"deleted": True, "id": document_id}
    except HTTPException:
        raise
    except Exception as exc:
        print("HEALTHCARE DOCUMENT DELETE ERROR:", repr(exc), flush=True)
        raise HTTPException(status_code=503, detail="Không thể xóa hồ sơ.") from exc
'@
if (-not $main.Contains($old)) { throw 'Khong tim thay dung endpoint extract goc; da tao backup nhung khong sua main.py.' }
$main = $main.Replace($old, $new)
Set-Content -Path $mainPath -Value $main -Encoding UTF8
$python = Join-Path $root 'backend\.venv\Scripts\python.exe'
if (-not (Test-Path $python)) { $python = (Get-Command python -ErrorAction Stop).Source }
Push-Location (Join-Path $root 'backend')
try {
  & $python -m py_compile main.py
  if ($LASTEXITCODE -ne 0) { throw 'Python compile that bai.' }
  & $python -m pytest -q
  if ($LASTEXITCODE -ne 0) { throw 'Regression tests that bai; xem backup de rollback.' }
} finally { Pop-Location }
Write-Host 'STT16 PERSISTENT BACKEND PATCH: PASS' -ForegroundColor Green
Write-Host "Backup: $backup"
Write-Host "Migration: $migration"
Write-Host 'CAN LAM TIEP: Apply migration trong Supabase SQL Editor; sau do kiem tra upload/list/delete tren staging. Khong co commit/push/deploy.' -ForegroundColor Yellow
Write-Host 'Frontend khong duoc patch boi ZIP hien tai khong co ma nguon frontend day du.' -ForegroundColor Yellow
