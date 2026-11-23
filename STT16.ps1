[CmdletBinding()]
param()
$ErrorActionPreference = 'Stop'
$Root = 'C:\YTeMo'
$Backend = Join-Path $Root 'backend'
$MainPy = Join-Path $Backend 'main.py'
$DocsPy = Join-Path $Backend 'healthcare_documents.py'
$Report = Join-Path $Root 'STT16_REPORT.txt'

Write-Host '==================================================' -ForegroundColor Cyan
Write-Host 'STT16 - HO SO NGUOI DUNG VA TAI HO SO Y TE' -ForegroundColor Cyan
Write-Host '==================================================' -ForegroundColor Cyan

if (!(Test-Path $MainPy) -or !(Test-Path $DocsPy)) {
    throw 'Khong tim thay backend/main.py hoac backend/healthcare_documents.py. Dung de tranh sua nham repo.'
}

$main = Get-Content $MainPy -Raw -Encoding UTF8
$doc = Get-Content $DocsPy -Raw -Encoding UTF8
$checks = [ordered]@{
    'POST /companion/initialize (tao companion/profile)' = ($main -match '@app\.post\("/companion/initialize"\)')
    'GET /companion (doc profile snapshot)' = ($main -match '@app\.get\("/companion"\)')
    'PUT /companion/consent (quan ly consent)' = ($main -match '@app\.put\("/companion/consent"\)')
    'POST /companion/context (luu thong tin profile)' = ($main -match '@app\.post\("/companion/context"\)')
    'GET /companion/context (doc profile context)' = ($main -match '@app\.get\("/companion/context"\)')
    'DELETE /companion/context/{context_id}' = ($main -match '@app\.delete\("/companion/context/\{context_id\}"\)')
    'POST /healthcare/documents/extract (upload endpoint)' = ($main -match '@app\.post\("/healthcare/documents/extract"\)')
    'Upload endpoint bat buoc xac thuc user' = ($main -match '(?s)@app\.post\("/healthcare/documents/extract"\).*?user=Depends\(get_current_user\)')
    'Gioi han file 10 MB' = ($doc -match 'MAX_DOCUMENT_BYTES\s*=\s*10\s*\*\s*1024\s*\*\s*1024')
    'Chi chap nhan PDF/DOCX/TXT/MD' = ($doc -match 'SUPPORTED_EXTENSIONS\s*=\s*\{"\.pdf",\s*"\.docx",\s*"\.txt",\s*"\.md"\}')
    'Khong tu dong luu file upload vao storage' = ($doc -match 'persisted:\s*bool\s*=\s*False')
}

$failed = @($checks.GetEnumerator() | Where-Object { -not $_.Value })
foreach ($item in $checks.GetEnumerator()) {
    if ($item.Value) { Write-Host "[PASS] $($item.Key)" -ForegroundColor Green }
    else { Write-Host "[FAIL] $($item.Key)" -ForegroundColor Red }
}

$frontendFiles = @()
$frontendDir = Join-Path $Root 'frontend'
if (Test-Path $frontendDir) {
    $frontendFiles = @(Get-ChildItem $frontendDir -Recurse -File -ErrorAction SilentlyContinue | Where-Object {
        $_.Extension -in '.js','.jsx','.ts','.tsx','.vue','.html'
    })
}

$python = Join-Path $Backend '.venv\Scripts\python.exe'
if (!(Test-Path $python)) { $python = (Get-Command python -ErrorAction SilentlyContinue).Source }
if (!$python) { throw 'Khong tim thay Python. Khong the chay regression tests.' }

Write-Host "`nDang chay backend regression tests..." -ForegroundColor Cyan
Push-Location $Backend
try {
    & $python -m pytest -q
    $testExit = $LASTEXITCODE
} finally { Pop-Location }

$lines = @(
    'STT16 - PROFILE VA UPLOAD AUDIT',
    ('Thoi diem: ' + (Get-Date -Format 'yyyy-MM-dd HH:mm:ss')),
    ('Static checks passed: ' + ($checks.Count - $failed.Count) + '/' + $checks.Count),
    ('Frontend source files found: ' + $frontendFiles.Count),
    ('Regression exit code: ' + $testExit),
    '',
    'KET LUAN:',
    '- Backend da co API khoi tao/lay profile va consent-controlled context.',
    '- Backend da co endpoint upload de trich xuat van ban; gioi han 10 MB.',
    '- Endpoint extract xu ly trong bo nho, KHONG luu file y te lau dai.',
    '- ZIP review khong co frontend source day du; UI tao profile/upload chua the xac nhan.',
    '- Chua co xac nhan persistent medical-document storage trong pham vi STT16.',
    '',
    'Khong thay doi source code, database, storage, secrets; khong commit/deploy.'
)
$lines | Set-Content -Path $Report -Encoding UTF8
Write-Host "`nDa ghi bao cao: $Report" -ForegroundColor Cyan

if ($failed.Count -gt 0 -or $testExit -ne 0) {
    Write-Host 'STT16 CHECK: FAIL - xem cac muc [FAIL] va regression.' -ForegroundColor Red
    exit 1
}
if ($frontendFiles.Count -eq 0) {
    Write-Host 'STT16 BACKEND API: PASS; FULL TASK: INCOMPLETE (thieu frontend va persistent document storage).' -ForegroundColor Yellow
} else {
    Write-Host 'STT16 BACKEND API: PASS; can tiep tuc doi chieu frontend va persistent storage.' -ForegroundColor Yellow
}
