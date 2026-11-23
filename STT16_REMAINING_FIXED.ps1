$ErrorActionPreference = 'Stop'
$root = (Get-Location).Path
$mainPath = Join-Path $root 'backend\main.py'
$migration = Join-Path $root 'supabase\migrations\202611240002_healthcare_document_storage.sql'

if (-not (Test-Path $mainPath)) { throw 'Khong tim thay backend\main.py. Hay chay script tai C:\YTeMo.' }
if (-not (Test-Path $migration)) { throw "Khong tim thay migration STT16: $migration. Script khong tu tao migration moi." }

# Migration da ton tai la dieu kien binh thuong: doc de tham chieu, khong tao de, khong throw.
$sql = Get-Content -LiteralPath $migration -Raw
$requiredSql = @('healthcare_documents', 'healthcare-documents', 'storage.buckets', 'auth.uid()')
$missingSql = @($requiredSql | Where-Object { $sql -notmatch [regex]::Escape($_) })
if ($missingSql.Count -gt 0) {
    Write-Warning "Migration hien co chua thay cac chuoi: $($missingSql -join ', '). Script van patch backend; can doi chieu SQL truoc khi apply migration."
} else {
    Write-Host '[PASS] Da doc va giu nguyen migration STT16.' -ForegroundColor Green
}

$main = Get-Content -LiteralPath $mainPath -Raw
if ($main.Contains('STT16_PERSISTENT_STORAGE')) {
    Write-Host '[PASS] Backend da co patch STT16_PERSISTENT_STORAGE; khong chen lap.' -ForegroundColor Green
} else {
    # Backup truoc moi thay doi.
    $stamp = Get-Date -Format 'yyyyMMdd_HHmmss'
    $backupDir = Join-Path $root ".stt16_backup_$stamp"
    New-Item -ItemType Directory -Path $backupDir | Out-Null
    Copy-Item -LiteralPath $mainPath -Destination (Join-Path $backupDir 'main.py')

    # Match route bang decorator chinh xac va ket thuc truoc decorator tiep theo.
    $routePattern = '(?ms)^@app\.post\("/healthcare/documents/extract"\)\s*.*?(?=^@app\.(?:get|post|put|patch|delete)\()'
    $routeMatches = [regex]::Matches($main, $routePattern)
    if ($routeMatches.Count -ne 1) {
        throw "Can dung 1 route POST /healthcare/documents/extract; tim thay $($routeMatches.Count). Da backup, main.py chua bi sua."
    }

    $replacement = @'
# STT16_PERSISTENT_STORAGE: upload file bytes and owner-scoped metadata.
@app.post("/healthcare/documents/extract")
async def extract_healthcare_document(
    file: UploadFile = File(...),
    user=Depends(get_current_user),
):
    try:
        data = await file.read(MAX_DOCUMENT_BYTES + 1)
        if len(data) > MAX_DOCUMENT_BYTES:
            raise HTTPException(status_code=413, detail="File vượt giới hạn 10 MB.")
        extracted = extract_medical_document(file.filename or "document", data)
    except DocumentExtractionError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    finally:
        await file.close()

    document_id = str(__import__("uuid").uuid4())
    storage_path = f"{user.id}/{document_id}/{extracted.filename}"
    try:
        db_client.storage.from_("healthcare-documents").upload(
            storage_path, data,
            {"content-type": extracted.media_type, "upsert": "false"},
        )
        row = {
            "id": document_id,
            "user_id": str(user.id),
            "filename": extracted.filename,
            "media_type": extracted.media_type,
            "byte_size": len(data),
            "storage_path": storage_path,
            "extraction_status": extracted.extraction_status,
        }
        db_client.table("healthcare_documents").insert(row).execute()
    except Exception as exc:
        try:
            db_client.storage.from_("healthcare-documents").remove([storage_path])
        except Exception:
            pass
        print("HEALTHCARE DOCUMENT UPLOAD ERROR:", repr(exc), flush=True)
        raise HTTPException(status_code=503, detail="Không thể lưu hồ sơ y tế. Kiểm tra migration và Storage bucket.") from exc

    document = extracted.to_dict()
    document.update({"id": document_id, "persisted": True, "byte_size": len(data)})
    return {
        "document": document,
        "next_step": "Gửi document.text đến POST /healthcare/agents/run để chạy các Specialist Agents.",
    }

@app.get("/healthcare/documents")
def list_healthcare_documents(user=Depends(get_current_user)):
    try:
        result = db_client.table("healthcare_documents").select(
            "id,filename,media_type,byte_size,extraction_status,created_at"
        ).eq("user_id", str(user.id)).order("created_at", desc=True).execute()
        return {"documents": result.data or []}
    except Exception as exc:
        print("HEALTHCARE DOCUMENT LIST ERROR:", repr(exc), flush=True)
        raise HTTPException(status_code=503, detail="Không thể đọc danh sách hồ sơ.") from exc

@app.delete("/healthcare/documents/{document_id}")
def delete_healthcare_document(document_id: str, user=Depends(get_current_user)):
    try:
        found = db_client.table("healthcare_documents").select(
            "id,storage_path"
        ).eq("id", document_id).eq("user_id", str(user.id)).limit(1).execute()
        if not found.data:
            raise HTTPException(status_code=404, detail="Không tìm thấy hồ sơ.")
        storage_path = found.data[0]["storage_path"]
        db_client.storage.from_("healthcare-documents").remove([storage_path])
        db_client.table("healthcare_documents").delete().eq(
            "id", document_id
        ).eq("user_id", str(user.id)).execute()
        return {"deleted": True, "id": document_id}
    except HTTPException:
        raise
    except Exception as exc:
        print("HEALTHCARE DOCUMENT DELETE ERROR:", repr(exc), flush=True)
        raise HTTPException(status_code=503, detail="Không thể xóa hồ sơ.") from exc

'@
    $match = $routeMatches[0]
    $main = $main.Remove($match.Index, $match.Length).Insert($match.Index, $replacement)
    Set-Content -LiteralPath $mainPath -Value $main -Encoding UTF8
    Write-Host "[PASS] Da cap nhat route upload va tao API list/delete. Backup: $backupDir" -ForegroundColor Green
}

$python = Join-Path $root 'backend\.venv\Scripts\python.exe'
if (-not (Test-Path $python)) { $python = (Get-Command python -ErrorAction Stop).Source }
Push-Location (Join-Path $root 'backend')
try {
    & $python -m py_compile main.py
    if ($LASTEXITCODE -ne 0) { throw 'Python compile that bai.' }
    Write-Host '[PASS] Python compile.' -ForegroundColor Green
    & $python -m pytest -q
    if ($LASTEXITCODE -ne 0) { throw 'Regression tests that bai. Khong commit/push/deploy.' }
} finally {
    Pop-Location
}

Write-Host 'STT16 BACKEND PATCH + REGRESSION: PASS' -ForegroundColor Green
Write-Host "Migration duoc giu nguyen: $migration"
Write-Host 'Can apply migration tren Supabase truoc khi test upload luu tru that.' -ForegroundColor Yellow
Write-Host 'Khong commit, push hoac deploy.'
