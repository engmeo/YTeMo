$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

$Root = 'C:\YTeMo'
$Backend = Join-Path $Root 'backend'
$Report = Join-Path $Root 'STT17_OCR_RUNTIME_REPORT.txt'
$Log = New-Object System.Collections.Generic.List[string]
$Failed = $false
function Log([string]$s) { $Log.Add(('[' + (Get-Date -Format 'yyyy-MM-dd HH:mm:ss') + '] ' + $s)); Write-Host $s }
function Find-Tesseract {
    $paths = @(
        'C:\Program Files\Tesseract-OCR\tesseract.exe',
        'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe',
        (Join-Path $env:LOCALAPPDATA 'Programs\Tesseract-OCR\tesseract.exe')
    )
    foreach ($p in $paths) { if (Test-Path $p) { return $p } }
    $c = Get-Command tesseract.exe -ErrorAction SilentlyContinue
    if ($c) { return $c.Source }
    return $null
}
try {
    if (-not (Test-Path $Root)) { throw "Project folder not found: $Root" }
    if (-not (Test-Path $Backend)) { throw "Backend folder not found: $Backend" }
    Log 'STT17 OCR RUNTIME FIX V3 20261124 - DIRECT INSTALLER MODE'
    Log ('Project: ' + $Root)

    $Python = Join-Path $Backend '.venv\Scripts\python.exe'
    if (-not (Test-Path $Python)) { $Python = Join-Path $Root '.venv\Scripts\python.exe' }
    if (-not (Test-Path $Python)) { $pc = Get-Command python.exe -ErrorAction SilentlyContinue; if ($pc) { $Python = $pc.Source } }
    if (-not (Test-Path $Python)) { throw 'Could not find project Python interpreter.' }
    Log ('Python: ' + $Python)

    $Tess = Find-Tesseract
    if (-not $Tess) {
        $Installer = Join-Path $env:TEMP 'tesseract-ocr-w64-setup-5.5.3.20260724.exe'
        $Url = 'https://digi.bib.uni-mannheim.de/tesseract/tesseract-ocr-w64-setup-5.5.3.20260724.exe'
        Log 'Tesseract is not installed. Downloading the Windows installer directly; WinGet is NOT used.'
        Invoke-WebRequest -Uri $Url -OutFile $Installer -UseBasicParsing
        if (-not (Test-Path $Installer) -or (Get-Item $Installer).Length -lt 10000000) { throw 'Installer download failed or file is too small.' }
        Log 'Launching the Tesseract installer. Approve the Windows UAC prompt if shown, then finish the installer.'
        $p = Start-Process -FilePath $Installer -Verb RunAs -Wait -PassThru
        Log ('Installer process exit code: ' + $p.ExitCode)
        $Tess = Find-Tesseract
        if (-not $Tess) { throw 'Installer finished but tesseract.exe was not found. Check whether installation was cancelled or choose the default install folder.' }
    }
    Log ('Tesseract executable: ' + $Tess)

    $TessDir = Split-Path -Parent $Tess
    $DataDir = Join-Path $env:LOCALAPPDATA 'Tesseract-OCR\tessdata'
    if (-not (Test-Path $DataDir)) { New-Item -ItemType Directory -Path $DataDir -Force | Out-Null }
    foreach ($lang in @('eng','vie')) {
        $dest = Join-Path $DataDir ($lang + '.traineddata')
        if (-not (Test-Path $dest) -or (Get-Item $dest).Length -lt 100000) {
            $u = 'https://raw.githubusercontent.com/tesseract-ocr/tessdata_fast/main/' + $lang + '.traineddata'
            Log ('Downloading language data: ' + $lang)
            Invoke-WebRequest -Uri $u -OutFile $dest -UseBasicParsing
        }
        if ((Get-Item $dest).Length -lt 100000) { throw ('Language data invalid: ' + $lang) }
    }
    $env:TESSDATA_PREFIX = $DataDir
    $env:TESSERACT_EXE = $Tess
    [Environment]::SetEnvironmentVariable('TESSDATA_PREFIX', $DataDir, 'User')
    $env:Path = $TessDir + ';' + $env:Path

    Log 'Installing Python OCR packages into the project virtual environment.'
    & $Python -m pip install 'PyMuPDF>=1.24' 'pytesseract>=0.3.13' 'Pillow>=10'
    if ($LASTEXITCODE -ne 0) { throw 'pip could not install OCR packages.' }

    $Smoke = Join-Path $env:TEMP 'stt17_ocr_v3_20261124_smoke.py'
    @'
import os, io
from PIL import Image, ImageDraw
import pytesseract, fitz
pytesseract.pytesseract.tesseract_cmd = os.environ['TESSERACT_EXE']
data = os.environ['TESSDATA_PREFIX']
langs = pytesseract.get_languages(config='--tessdata-dir ' + data)
assert 'eng' in langs and 'vie' in langs, 'vie/eng language data unavailable: ' + repr(langs)
im = Image.new('RGB', (1400, 260), 'white')
d = ImageDraw.Draw(im)
d.text((40, 80), 'OCR TEST 123 Y TE MO', fill='black')
t = pytesseract.image_to_string(im, lang='vie+eng', config='--psm 6')
assert 'OCR' in t.upper() and '123' in t, 'Image OCR failed: ' + repr(t)
doc = fitz.open()
page = doc.new_page(width=700, height=130)
pix = fitz.Pixmap(fitz.csRGB, im.width, im.height, im.tobytes(), False)
page.insert_image(page.rect, pixmap=pix)
pdf = os.path.join(os.environ['TEMP'], 'stt17_ocr_v3_20261124_scan.pdf')
doc.save(pdf); doc.close()
doc = fitz.open(pdf)
assert not doc[0].get_text().strip(), 'Test PDF unexpectedly contains embedded text'
render = doc[0].get_pixmap(matrix=fitz.Matrix(2,2), alpha=False)
page_im = Image.open(io.BytesIO(render.tobytes('png')))
t2 = pytesseract.image_to_string(page_im, lang='vie+eng', config='--psm 6')
assert 'OCR' in t2.upper() and '123' in t2, 'Image-only PDF OCR failed: ' + repr(t2)
doc.close()
print('PYTHON_IMPORTS=PASS')
print('LANGUAGES=PASS(vie,eng)')
print('IMAGE_OCR=PASS')
print('IMAGE_ONLY_PDF_RENDER_AND_OCR=PASS')
'@ | Set-Content -Path $Smoke -Encoding ASCII
    Log 'Running OCR image and scanned-PDF smoke tests.'
    & $Python $Smoke
    if ($LASTEXITCODE -ne 0) { throw 'OCR smoke test failed.' }

    $Specific = Join-Path $Backend 'test_healthcare_documents_stt17.py'
    if (Test-Path $Specific) {
        Log 'Running STT17-specific tests.'
        & $Python -m pytest -q -p no:cacheprovider $Specific
        if ($LASTEXITCODE -ne 0) { throw 'STT17-specific pytest failed.' }
    }
    Log 'Running full backend regression tests.'
    Push-Location $Backend
    try { & $Python -m pytest -q -p no:cacheprovider; if ($LASTEXITCODE -ne 0) { throw 'Full backend pytest failed.' } }
    finally { Pop-Location }
    Log 'STT17 OCR RUNTIME FIX V3 20261124: PASS'
} catch {
    $Failed = $true
    Log ('FAIL: ' + $_.Exception.Message)
} finally {
    $Log | Set-Content -Path $Report -Encoding ASCII
    Write-Host ('Report: ' + $Report)
}
if ($Failed) { Write-Host 'STT17 OCR RUNTIME FIX V3 20261124: FAIL' -ForegroundColor Red; exit 1 }
Write-Host 'STT17 OCR RUNTIME FIX V3 20261124: PASS' -ForegroundColor Green
exit 0
