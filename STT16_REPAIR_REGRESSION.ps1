$ErrorActionPreference = 'Stop'
$root = (Get-Location).Path
$mainPath = Join-Path $root 'backend\main.py'
$openapiPath = Join-Path $root 'docs\api\openapi.json'

if (-not (Test-Path -LiteralPath $mainPath)) { throw 'Khong tim thay backend\main.py. Hay chay tai C:\YTeMo.' }
if (-not (Test-Path -LiteralPath $openapiPath)) { throw 'Khong tim thay docs\api\openapi.json.' }

$stamp = Get-Date -Format 'yyyyMMdd_HHmmss'
$backupDir = Join-Path $root ".stt16_repair_backup_$stamp"
New-Item -ItemType Directory -Path $backupDir | Out-Null
Copy-Item -LiteralPath $mainPath -Destination (Join-Path $backupDir 'main.py')
Copy-Item -LiteralPath $openapiPath -Destination (Join-Path $backupDir 'openapi.json')

# Python's UTF-8 decoder (used by the AST regression tests) rejects a UTF-8 BOM.
$mainText = [System.IO.File]::ReadAllText($mainPath)
$mainText = $mainText.TrimStart([char]0xFEFF)
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText($mainPath, $mainText, $utf8NoBom)
Write-Host '[PASS] Da loai UTF-8 BOM khoi backend/main.py.' -ForegroundColor Green

# Add the two routes implemented by the STT16 patch to the checked-in OpenAPI contract.
$py = @'
import json
from pathlib import Path

p = Path(r"docs/api/openapi.json")
data = json.loads(p.read_text(encoding="utf-8-sig"))
paths = data.setdefault("paths", {})

def operation(summary, operation_id):
    return {
        "summary": summary,
        "operationId": operation_id,
        "responses": {
            "200": {"description": "Successful Response"},
            "401": {"description": "Authentication required"},
            "503": {"description": "Storage service unavailable"}
        },
        "security": [{"HTTPBearer": []}]
    }

paths.setdefault("/healthcare/documents", {})["get"] = operation(
    "List Healthcare Documents", "list_healthcare_documents_healthcare_documents_get"
)
paths.setdefault("/healthcare/documents/{document_id}", {})["delete"] = operation(
    "Delete Healthcare Document", "delete_healthcare_document_healthcare_documents__document_id__delete"
)

# Write UTF-8 without BOM; preserve all existing OpenAPI paths and components.
p.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
'@
$pyFile = Join-Path $env:TEMP "stt16_repair_openapi_$stamp.py"
[System.IO.File]::WriteAllText($pyFile, $py, $utf8NoBom)
try {
    $python = Join-Path $root 'backend\.venv\Scripts\python.exe'
    if (-not (Test-Path $python)) { $python = (Get-Command python -ErrorAction Stop).Source }
    & $python $pyFile
    if ($LASTEXITCODE -ne 0) { throw 'Khong cap nhat duoc OpenAPI contract.' }
} finally {
    Remove-Item -LiteralPath $pyFile -Force -ErrorAction SilentlyContinue
}
Write-Host '[PASS] Da dong bo OpenAPI voi 2 route GET/DELETE moi.' -ForegroundColor Green

Push-Location (Join-Path $root 'backend')
try {
    & $python -m py_compile main.py
    if ($LASTEXITCODE -ne 0) { throw 'Python compile that bai.' }
    Write-Host '[PASS] Python compile.' -ForegroundColor Green
    & $python -m pytest -q
    if ($LASTEXITCODE -ne 0) {
        throw 'Regression van con loi. Bao luu backup; khong commit/push/deploy.'
    }
} finally {
    Pop-Location
}
Write-Host 'STT16 REGRESSION REPAIR: PASS' -ForegroundColor Green
Write-Host "Backup: $backupDir"
Write-Host 'Khong commit, push hoac deploy.'
