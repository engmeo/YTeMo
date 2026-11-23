$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

$ProjectRoot = "C:\YTeMo"
$BackendDir = Join-Path $ProjectRoot "backend"
$ReportPath = Join-Path $ProjectRoot "STT17_OCR_RUNTIME_REPORT.txt"
$Log = New-Object System.Collections.Generic.List[string]
$Failed = $false

function Add-Log([string]$Message) {
    $stamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $line = "[$stamp] $Message"
    $Log.Add($line)
    Write-Host $Message
}

function Test-IsAdmin {
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($identity)
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

try {
    if (-not (Test-Path $ProjectRoot)) { throw "Project folder not found: $ProjectRoot" }
    if (-not (Test-Path $BackendDir)) { throw "Backend folder not found: $BackendDir" }

    Add-Log "STT17 OCR runtime setup started."
    Add-Log "Project: $ProjectRoot"

    # Select the project's existing virtual environment where possible.
    $Python = Join-Path $BackendDir ".venv\Scripts\python.exe"
    if (-not (Test-Path $Python)) {
        $Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
    }
    if (-not (Test-Path $Python)) {
        $cmd = Get-Command python -ErrorAction SilentlyContinue
        if ($null -eq $cmd) { throw "Python was not found. Install Python 3.10+ and rerun this script." }
        $Python = $cmd.Source
    }
    Add-Log "Python: $Python"

    # Install the native OCR engine only if it is not already installed.
    $TesseractCandidates = @(
        "C:\Program Files\Tesseract-OCR\tesseract.exe",
        "C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        (Join-Path $env:LOCALAPPDATA "Programs\Tesseract-OCR\tesseract.exe")
    )
    $TesseractExe = $null
    foreach ($candidate in $TesseractCandidates) {
        if (Test-Path $candidate) { $TesseractExe = $candidate; break }
    }
    $tessCommand = Get-Command tesseract -ErrorAction SilentlyContinue
    if (-not $TesseractExe -and $tessCommand) { $TesseractExe = $tessCommand.Source }

    if (-not $TesseractExe) {
        $winget = Get-Command winget -ErrorAction SilentlyContinue
        if (-not $winget) {
            throw "Tesseract is missing and winget is unavailable. Install Microsoft App Installer (winget), then rerun this script."
        }

        if (-not (Test-IsAdmin)) {
            Add-Log "Tesseract installation requires elevation. Requesting Administrator permission..."
            $scriptPath = $MyInvocation.MyCommand.Path
            if (-not $scriptPath -or -not (Test-Path $scriptPath)) {
                throw "Cannot relaunch script for elevation. Save and run the downloaded .ps1 file directly."
            }
            $args = "-NoProfile -ExecutionPolicy Bypass -File `"$scriptPath`""
            Start-Process -FilePath "powershell.exe" -Verb RunAs -ArgumentList $args -Wait
            Add-Log "Elevated setup process completed. Check the report for its final status."
            exit
        }

        Add-Log "Installing Tesseract OCR using winget..."
        & $winget.Source install --exact --id UB-Mannheim.TesseractOCR --silent --accept-package-agreements --accept-source-agreements
        if ($LASTEXITCODE -ne 0) {
            throw "winget could not install Tesseract (exit code $LASTEXITCODE). Run PowerShell as Administrator and retry."
        }

        foreach ($candidate in $TesseractCandidates) {
            if (Test-Path $candidate) { $TesseractExe = $candidate; break }
        }
        if (-not $TesseractExe) {
            $tessCommand = Get-Command tesseract -ErrorAction SilentlyContinue
            if ($tessCommand) { $TesseractExe = $tessCommand.Source }
        }
        if (-not $TesseractExe) { throw "Tesseract installation reported success, but tesseract.exe was not found." }
    }

    $TesseractDir = Split-Path -Parent $TesseractExe
    $TessdataDir = Join-Path $TesseractDir "tessdata"
    if (-not (Test-Path $TessdataDir)) {
        New-Item -ItemType Directory -Path $TessdataDir -Force | Out-Null
    }
    $env:TESSDATA_PREFIX = $TessdataDir
    [Environment]::SetEnvironmentVariable("TESSDATA_PREFIX", $TessdataDir, "User")
    $env:Path = "$TesseractDir;$env:Path"
    Add-Log "Tesseract: $TesseractExe"

    # Ensure Vietnamese and English OCR models exist.
    foreach ($lang in @("vie", "eng")) {
        $trainedData = Join-Path $TessdataDir "$lang.traineddata"
        if (-not (Test-Path $trainedData)) {
            $url = "https://github.com/tesseract-ocr/tessdata_fast/raw/main/$lang.traineddata"
            Add-Log "Downloading OCR language model: $lang"
            Invoke-WebRequest -Uri $url -OutFile $trainedData -UseBasicParsing
        }
        if ((Get-Item $trainedData).Length -lt 100000) {
            throw "Language model $lang.traineddata appears incomplete or invalid."
        }
    }

    # Install Python OCR dependencies into the selected project interpreter.
    Add-Log "Installing Python OCR dependencies (PyMuPDF, pytesseract, Pillow)..."
    & $Python -m pip install --upgrade pip
    if ($LASTEXITCODE -ne 0) { throw "pip upgrade failed." }
    & $Python -m pip install "PyMuPDF>=1.24" "pytesseract>=0.3.13" "Pillow>=10"
    if ($LASTEXITCODE -ne 0) { throw "Python OCR dependency installation failed." }

    # Runtime smoke test: Python imports + real image OCR using vie+eng models.
    $SmokePy = Join-Path $env:TEMP "stt17_ocr_smoke_test.py"
    $SmokeOutput = Join-Path $env:TEMP "stt17_ocr_smoke_result.txt"
    $pyCode = @'
import os, sys
from PIL import Image, ImageDraw, ImageFont
import pytesseract
import fitz

tesseract = os.environ.get("TESSERACT_EXE")
tessdata = os.environ.get("TESSDATA_PREFIX")
pytesseract.pytesseract.tesseract_cmd = tesseract

langs = pytesseract.get_languages(config="--tessdata-dir " + repr(tessdata))
assert "eng" in langs and "vie" in langs, "Required OCR languages are missing: " + repr(langs)

image = Image.new("RGB", (1200, 240), "white")
draw = ImageDraw.Draw(image)
draw.text((35, 70), "OCR TEST 123 - Y TE MO", fill="black")
text = pytesseract.image_to_string(image, lang="vie+eng", config="--psm 6")
normalized = " ".join(text.upper().split())
assert "OCR" in normalized and "123" in normalized, "OCR smoke test did not recover expected text: " + repr(text)

# Build a one-page image-only PDF and verify PyMuPDF can render it for OCR input.
pdf_path = os.path.join(os.environ["TEMP"], "stt17_ocr_smoke.pdf")
doc = fitz.open()
page = doc.new_page(width=600, height=120)
pix = fitz.Pixmap(image.mode == "RGB" and fitz.csRGB, image.width, image.height, image.tobytes(), False)
page.insert_image(page.rect, pixmap=pix)
doc.save(pdf_path)
doc.close()
check = fitz.open(pdf_path)
assert len(check) == 1 and check[0].get_text().strip() == "", "Smoke PDF is not image-only as expected"
rendered = check[0].get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
from PIL import Image as PILImage
import io
page_image = PILImage.open(io.BytesIO(rendered.tobytes("png")))
pdf_text = pytesseract.image_to_string(page_image, lang="vie+eng", config="--psm 6")
assert "OCR" in " ".join(pdf_text.upper().split()), "Scanned-PDF OCR smoke test failed"
check.close()
print("PYTHON_IMPORTS=PASS")
print("LANGUAGES=PASS(vie,eng)")
print("IMAGE_OCR=PASS")
print("IMAGE_ONLY_PDF_RENDER_AND_OCR=PASS")
'@
    Set-Content -Path $SmokePy -Value $pyCode -Encoding ASCII
    $env:TESSERACT_EXE = $TesseractExe
    Add-Log "Running OCR runtime smoke test..."
    & $Python $SmokePy
    if ($LASTEXITCODE -ne 0) { throw "OCR runtime smoke test failed." }

    # Run the existing STT17-specific tests, then the complete backend suite.
    $specificTests = Join-Path $BackendDir "test_healthcare_documents_stt17.py"
    if (Test-Path $specificTests) {
        Add-Log "Running STT17 document tests..."
        & $Python -m pytest -q -p no:cacheprovider $specificTests
        if ($LASTEXITCODE -ne 0) { throw "STT17-specific tests failed." }
    } else {
        Add-Log "WARNING: STT17-specific test file was not found; skipping that test target."
    }

    Add-Log "Running full backend regression suite..."
    Push-Location $BackendDir
    try {
        & $Python -m pytest -q -p no:cacheprovider
        if ($LASTEXITCODE -ne 0) { throw "Full backend pytest failed." }
    } finally {
        Pop-Location
    }

    Add-Log "OCR runtime readiness: PASS"
    Add-Log "STT17 OCR runtime fix: PASS"
}
catch {
    $Failed = $true
    Add-Log ("FAIL: " + $_.Exception.Message)
}
finally {
    $Log | Set-Content -Path $ReportPath -Encoding ASCII
    Add-Log "Report: $ReportPath"
}

if ($Failed) {
    Write-Host "STT17 OCR RUNTIME FIX: FAIL" -ForegroundColor Red
    exit 1
} else {
    Write-Host "STT17 OCR RUNTIME FIX: PASS" -ForegroundColor Green
    exit 0
}
