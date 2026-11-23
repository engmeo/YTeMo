[CmdletBinding()]
param(
    [string]$ProjectRoot = "C:\YTeMo"
)

$ErrorActionPreference = "Stop"
$root = (Resolve-Path $ProjectRoot).Path
$backend = Join-Path $root "backend"
$report = Join-Path $root "STT17_AUDIT_REPORT.txt"

if (-not (Test-Path (Join-Path $backend "main.py"))) {
    throw "Khong tim thay backend\main.py trong $root"
}

function Read-TextSafe([string]$Path) {
    if (Test-Path $Path) { return [System.IO.File]::ReadAllText($Path) }
    return ""
}
function Has-Pattern([string]$Text, [string]$Pattern) {
    return [regex]::IsMatch($Text, $Pattern, [System.Text.RegularExpressions.RegexOptions]::IgnoreCase)
}

$main = Read-TextSafe (Join-Path $backend "main.py")
$docModule = Read-TextSafe (Join-Path $backend "healthcare_documents.py")
$specialists = Read-TextSafe (Join-Path $backend "healthcare_specialists.py")
$openapi = Read-TextSafe (Join-Path $root "docs\api\openapi.json")
$apiDocs = Read-TextSafe (Join-Path $root "docs\api\API_ENDPOINTS.md")
$integrationDocs = Read-TextSafe (Join-Path $root "docs\API_FRONTEND_INTEGRATION.vi.md")
$frontendFiles = @()
$frontendRoot = Join-Path $root "frontend"
if (Test-Path $frontendRoot) {
    $frontendFiles = Get-ChildItem $frontendRoot -Recurse -File |
        Where-Object { $_.FullName -notmatch '\\(node_modules|dist|build|\.git)\\' -and $_.Length -lt 5MB }
}
$frontendText = ($frontendFiles | ForEach-Object {
    try { [System.IO.File]::ReadAllText($_.FullName) } catch { "" }
}) -join "`n"

$testFiles = Get-ChildItem $backend -Recurse -File -Filter "test_*.py" |
    Where-Object { $_.FullName -notmatch '\\(\.venv|__pycache__|\.pytest_cache)\\' }
$healthcareTests = @()
foreach ($f in $testFiles) {
    $t = Read-TextSafe $f.FullName
    if ($f.Name -match 'healthcare|document|extract' -or
        (Has-Pattern $t 'extract_medical_document|healthcare/documents/extract|HealthcareAgentService|healthcare/agents/run')) {
        $healthcareTests += $f
    }
}

$checks = [System.Collections.Generic.List[string]]::new()
function Add-Check([string]$Name, [bool]$Pass, [string]$Detail) {
    $status = if ($Pass) { "FOUND" } else { "MISSING/PARTIAL" }
    $checks.Add("[$status] $Name — $Detail")
}

Add-Check "Bộ đọc tài liệu" (Has-Pattern $docModule 'def extract_medical_document') "healthcare_documents.py"
Add-Check "PDF text extraction" (Has-Pattern $docModule 'def _extract_pdf|PdfReader') "PDF có lớp text"
Add-Check "DOCX extraction" (Has-Pattern $docModule 'def _extract_docx|Document\(BytesIO') "DOCX paragraphs/tables"
Add-Check "TXT/Markdown extraction" (Has-Pattern $docModule 'utf-8-sig|text/markdown') "TXT và Markdown"
Add-Check "Giới hạn kích thước và nội dung" ((Has-Pattern $docModule 'MAX_DOCUMENT_BYTES') -and (Has-Pattern $docModule 'MAX_EXTRACTED_CHARACTERS')) "Giới hạn bytes/ký tự"
Add-Check "OCR PDF scan" ((Has-Pattern $docModule 'ocr') -and (Has-Pattern $docModule 'tesseract|easyocr|paddleocr|vision')) "Cần xác minh OCR thực sự hoạt động; chỉ có từ khóa chưa đủ"
Add-Check "Cost Agent" (Has-Pattern $specialists 'class CostIntelligenceAgent') "Trích xuất khoản tiền"
Add-Check "Medication Agent" (Has-Pattern $specialists 'class MedicationSupportAgent') "Trích xuất thuốc/liều"
Add-Check "Lab Agent" (Has-Pattern $specialists 'class LabResultAgent') "Trích xuất xét nghiệm"
Add-Check "BHYT Agent" (Has-Pattern $specialists 'class BHYTSupportAgent') "Trích xuất thông tin BHYT"
Add-Check "Evidence trace critic" (Has-Pattern $specialists 'class EvidenceTraceCritic') "Kiểm tra trích dẫn theo dòng nguồn"
Add-Check "Safety critic" (Has-Pattern $specialists 'class SafetyBoundaryCritic') "Chặn khuyến nghị lâm sàng"
Add-Check "API upload/extract" (Has-Pattern $main 'post\("/healthcare/documents/extract"\)') "POST /healthcare/documents/extract"
Add-Check "API specialist execution" (Has-Pattern $main 'post\("/healthcare/agents/run"\)') "POST /healthcare/agents/run"
Add-Check "API specialist list" (Has-Pattern $main 'get\("/healthcare/agents"\)') "GET /healthcare/agents"
Add-Check "OpenAPI document extract" (Has-Pattern $openapi '/healthcare/documents/extract') "docs/api/openapi.json"
Add-Check "Frontend integration" (Has-Pattern $frontendText 'healthcare/documents/extract|healthcare/agents/run') "Frontend gọi API đọc/trích xuất"
Add-Check "API documentation" ((Has-Pattern $apiDocs 'healthcare/documents/extract|healthcare/agents/run') -or (Has-Pattern $integrationDocs 'healthcare/documents/extract|healthcare/agents/run')) "Tài liệu API"

$gitStatus = "Khong doc duoc git status"
try {
    $gitStatus = (& git -C $root status --short 2>&1 | Out-String).Trim()
    if (-not $gitStatus) { $gitStatus = "(working tree sach)" }
} catch {}

$python = Join-Path $backend ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) { $python = "python" }

$testOutput = ""
$testExit = 999
Push-Location $backend
try {
    $testOutput = (& $python -m pytest -q -p no:cacheprovider 2>&1 | Out-String)
    $testExit = $LASTEXITCODE
} finally {
    Pop-Location
}

$lines = @()
$lines += "Y TE MO — STT17 AUDIT"
$lines += "Thoi diem: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
$lines += "Project: $root"
$lines += ""
$lines += "1. KIEM TRA THANH PHAN"
$lines += $checks
$lines += ""
$lines += "2. TEST FILE CO LIEN QUAN"
if ($healthcareTests.Count -eq 0) {
    $lines += "Khong tim thay test file healthcare/document/extract rieng."
} else {
    $lines += ($healthcareTests | ForEach-Object { $_.FullName.Substring($root.Length + 1) })
}
$lines += ""
$lines += "3. GIT STATUS (CHI DOC)"
$lines += $gitStatus
$lines += ""
$lines += "4. BACKEND REGRESSION"
$lines += "Exit code: $testExit"
$lines += $testOutput
$lines += ""
$lines += "5. KET LUAN"
$lines += "Day la audit chi doc. Script khong sua source, migration, env; khong commit/push/deploy."
$lines += "Khong xem ket qua test la bang chung cho do chinh xac y khoa."
[System.IO.File]::WriteAllText($report, ($lines -join [Environment]::NewLine), [System.Text.UTF8Encoding]::new($false))

Write-Host "`n===== STT17 AUDIT =====" -ForegroundColor Cyan
$checks | ForEach-Object { Write-Host $_ }
Write-Host "`nHealthcare test files: $($healthcareTests.Count)"
Write-Host "Backend pytest exit code: $testExit"
Write-Host "Report: $report"
Write-Host "Khong sua source / migration; khong commit, push, deploy."
if ($testExit -ne 0) {
    Write-Warning "Backend regression co test that bai. Xem report truoc khi sua."
}
