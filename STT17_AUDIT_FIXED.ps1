[CmdletBinding()]
param(
    [string]$ProjectRoot = "C:\YTeMo"
)

$ErrorActionPreference = "Stop"
$root = (Resolve-Path $ProjectRoot).Path
$backend = Join-Path $root "backend"
$report = Join-Path $root "STT17_AUDIT_REPORT.txt"

if (-not (Test-Path (Join-Path $backend "main.py"))) {
    throw "Cannot find backend\main.py in $root"
}

function Read-TextSafe([string]$Path) {
    if (Test-Path -LiteralPath $Path) {
        return [System.IO.File]::ReadAllText($Path)
    }
    return ""
}

function Has-Pattern([string]$Text, [string]$Pattern) {
    return [regex]::IsMatch(
        $Text,
        $Pattern,
        [System.Text.RegularExpressions.RegexOptions]::IgnoreCase
    )
}

$main = Read-TextSafe (Join-Path $backend "main.py")
$docModule = Read-TextSafe (Join-Path $backend "healthcare_documents.py")
$specialists = Read-TextSafe (Join-Path $backend "healthcare_specialists.py")
$openapi = Read-TextSafe (Join-Path $root "docs\api\openapi.json")
$apiDocs = Read-TextSafe (Join-Path $root "docs\api\API_ENDPOINTS.md")
$integrationDocs = Read-TextSafe (Join-Path $root "docs\API_FRONTEND_INTEGRATION.vi.md")

# Scan only likely frontend source files; do not scan node_modules or build output.
$frontendText = ""
$frontendRoots = @(
    (Join-Path $root "frontend"),
    (Join-Path $root "src")
)
foreach ($frontendRoot in $frontendRoots) {
    if (Test-Path $frontendRoot) {
        $files = Get-ChildItem -LiteralPath $frontendRoot -Recurse -File |
            Where-Object {
                $_.Extension -in @(".html", ".js", ".jsx", ".ts", ".tsx", ".vue") -and
                $_.FullName -notmatch '[\\/](node_modules|dist|build|\.git)[\\/]'
            }
        foreach ($file in $files) {
            try {
                $frontendText += "`n" + [System.IO.File]::ReadAllText($file.FullName)
            } catch {
                # Ignore unreadable/non-text frontend files.
            }
        }
    }
}

$testFiles = @()
if (Test-Path $backend) {
    $testFiles = Get-ChildItem -LiteralPath $backend -Recurse -File -Filter "test_*.py" |
        Where-Object {
            $_.FullName -notmatch '[\\/](\.venv|__pycache__|\.pytest_cache)[\\/]'
        }
}

$healthcareTests = @()
foreach ($file in $testFiles) {
    $testText = Read-TextSafe $file.FullName
    if ($file.Name -match 'healthcare|document|extract' -or
        (Has-Pattern $testText 'extract_medical_document|healthcare/documents/extract|HealthcareAgentService|healthcare/agents/run')) {
        $healthcareTests += $file
    }
}

$checks = New-Object 'System.Collections.Generic.List[string]'
function Add-Check([string]$Name, [bool]$Pass, [string]$Detail) {
    if ($Pass) {
        $status = "FOUND"
    } else {
        $status = "MISSING/PARTIAL"
    }
    $checks.Add("[$status] ${Name} - ${Detail}")
}

Add-Check "Document extraction entrypoint" (Has-Pattern $docModule 'def extract_medical_document') "backend/healthcare_documents.py"
Add-Check "PDF text extraction" (Has-Pattern $docModule 'def _extract_pdf|PdfReader') "Text-based PDF support"
Add-Check "DOCX extraction" (Has-Pattern $docModule 'def _extract_docx|Document\(BytesIO') "DOCX support"
Add-Check "TXT and Markdown extraction" (Has-Pattern $docModule 'utf-8-sig|text/markdown') "TXT/Markdown support"
Add-Check "Document size limit" (Has-Pattern $docModule 'MAX_DOCUMENT_BYTES') "Maximum upload bytes"
Add-Check "Extracted text limit" (Has-Pattern $docModule 'MAX_EXTRACTED_CHARACTERS') "Maximum extracted characters"
Add-Check "Scanned PDF OCR" ((Has-Pattern $docModule 'ocr') -and (Has-Pattern $docModule 'tesseract|easyocr|paddleocr|pytesseract|google.*vision')) "OCR implementation; a scan rejection message alone is not OCR"
Add-Check "Cost specialist" (Has-Pattern $specialists 'class CostIntelligenceAgent') "Cost extraction specialist"
Add-Check "Medication specialist" (Has-Pattern $specialists 'class MedicationSupportAgent') "Medication extraction specialist"
Add-Check "Lab specialist" (Has-Pattern $specialists 'class LabResultAgent') "Lab result specialist"
Add-Check "BHYT specialist" (Has-Pattern $specialists 'class BHYTSupportAgent') "Insurance support specialist"
Add-Check "Evidence trace critic" (Has-Pattern $specialists 'class EvidenceTraceCritic') "Evidence trace validation"
Add-Check "Safety boundary critic" (Has-Pattern $specialists 'class SafetyBoundaryCritic') "Clinical safety boundary"
Add-Check "Document extraction API" (Has-Pattern $main 'post\("/healthcare/documents/extract"\)') "POST /healthcare/documents/extract"
Add-Check "Specialist list API" (Has-Pattern $main 'get\("/healthcare/agents"\)') "GET /healthcare/agents"
Add-Check "Specialist run API" (Has-Pattern $main 'post\("/healthcare/agents/run"\)') "POST /healthcare/agents/run"
Add-Check "OpenAPI extraction route" (Has-Pattern $openapi '/healthcare/documents/extract') "docs/api/openapi.json"
Add-Check "OpenAPI specialist run route" (Has-Pattern $openapi '/healthcare/agents/run') "docs/api/openapi.json"
Add-Check "Frontend calls extraction/specialist API" (Has-Pattern $frontendText 'healthcare/documents/extract|healthcare/agents/run') "frontend/src source scan"
Add-Check "API docs mention extraction/specialist routes" (Has-Pattern ($apiDocs + "`n" + $integrationDocs) 'healthcare/documents/extract|healthcare/agents/run') "API documentation scan"

$gitStatus = "(git status unavailable)"
try {
    $gitOutput = & git -C $root status --short 2>&1
    if ($LASTEXITCODE -eq 0) {
        $gitStatus = ($gitOutput | Out-String).Trim()
        if ([string]::IsNullOrWhiteSpace($gitStatus)) {
            $gitStatus = "(working tree clean)"
        }
    }
} catch {
    $gitStatus = "(git status unavailable)"
}

$python = Join-Path $backend ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) {
    $python = "python"
}

Write-Host ""
Write-Host "===== STT17 AUDIT =====" -ForegroundColor Cyan
$checks | ForEach-Object { Write-Host $_ }
Write-Host ""
Write-Host ("Healthcare-related test files: " + $healthcareTests.Count)

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
$lines += "Y TE MO - STT17 AUDIT"
$lines += "Timestamp: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
$lines += "Project: $root"
$lines += ""
$lines += "1. COMPONENT CHECKS"
$lines += $checks.ToArray()
$lines += ""
$lines += "2. HEALTHCARE-RELATED TEST FILES"
if ($healthcareTests.Count -eq 0) {
    $lines += "No dedicated healthcare/document/extract test file found by filename/content scan."
} else {
    $lines += ($healthcareTests | ForEach-Object {
        $_.FullName.Substring($root.Length + 1)
    })
}
$lines += ""
$lines += "3. GIT STATUS (READ ONLY)"
$lines += $gitStatus
$lines += ""
$lines += "4. BACKEND PYTEST"
$lines += "Exit code: $testExit"
$lines += $testOutput
$lines += ""
$lines += "5. SAFETY"
$lines += "Audit only. No source files, migrations, environment variables, or database were changed."
$lines += "No commit, push, deploy, or Supabase migration was performed."
$lines += "Passing software tests do not establish clinical accuracy."

[System.IO.File]::WriteAllText(
    $report,
    ($lines -join [Environment]::NewLine),
    [System.Text.Encoding]::ASCII
)

Write-Host ""
Write-Host "Backend pytest exit code: $testExit"
Write-Host "Report: $report"
Write-Host "No source changes, commit, push, or deploy."

if ($testExit -ne 0) {
    Write-Warning "Backend regression failed. Review the report before making changes."
}
