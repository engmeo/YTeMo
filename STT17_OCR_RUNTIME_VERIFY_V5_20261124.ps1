$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

$Root = 'C:\YTeMo'
$Backend = Join-Path $Root 'backend'
$Report = Join-Path $Root 'STT17_OCR_RUNTIME_V5_REPORT.txt'
$Log = New-Object System.Collections.Generic.List[string]
$Failed = $false
function Log([string]$s) { $Log.Add(('[' + (Get-Date -Format 'yyyy-MM-dd HH:mm:ss') + '] ' + $s)); Write-Host $s }

try {
    if (-not (Test-Path $Root)) { throw 'Project folder C:\YTeMo was not found.' }
    $Python = Join-Path $Backend '.venv\Scripts\python.exe'
    if (-not (Test-Path $Python)) { throw ('Project Python not found: ' + $Python) }

    Log 'STT17 OCR RUNTIME VERIFY V5 20261124'
    Log ('Project: ' + $Root)
    Log ('Python: ' + $Python)

    $Candidates = @(
        'C:\Program Files\Tesseract-OCR\tesseract.exe',
        'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe',
        (Join-Path $env:LOCALAPPDATA 'Programs\Tesseract-OCR\tesseract.exe')
    )
    $Tess = $null
    foreach ($candidate in $Candidates) { if (Test-Path $candidate) { $Tess = $candidate; break } }
    if (-not $Tess) {
        $cmd = Get-Command tesseract.exe -ErrorAction SilentlyContinue
        if ($cmd) { $Tess = $cmd.Source }
    }
    if (-not $Tess) { throw 'TESSERACT_NOT_DETECTED. V4 output previously showed the executable; if it has moved, install location must be checked.' }

    Log ('TESSERACT_INSTALLED=YES')
    Log ('Tesseract executable: ' + $Tess)
    $TessDir = Split-Path -Parent $Tess
    $env:Path = $TessDir + ';' + $env:Path
    $env:TESSERACT_EXE = $Tess

    $DataCandidates = @(
        (Join-Path $env:LOCALAPPDATA 'Tesseract-OCR\tessdata'),
        (Join-Path $TessDir 'tessdata')
    )
    $DataDir = $null
    foreach ($candidate in $DataCandidates) {
        if ((Test-Path (Join-Path $candidate 'eng.traineddata')) -and (Test-Path (Join-Path $candidate 'vie.traineddata'))) { $DataDir = $candidate; break }
    }
    if (-not $DataDir) {
        $DataDir = Join-Path $env:LOCALAPPDATA 'Tesseract-OCR\tessdata'
        if (-not (Test-Path $DataDir)) { New-Item -ItemType Directory -Path $DataDir -Force | Out-Null }
        foreach ($lang in @('eng','vie')) {
            $dest = Join-Path $DataDir ($lang + '.traineddata')
            if (-not (Test-Path $dest) -or (Get-Item $dest).Length -lt 100000) {
                Log ('Downloading missing language file: ' + $lang)
                $uri = 'https://raw.githubusercontent.com/tesseract-ocr/tessdata_fast/main/' + $lang + '.traineddata'
                Invoke-WebRequest -Uri $uri -OutFile $dest -UseBasicParsing
            }
        }
    }
    $env:TESSDATA_PREFIX = $DataDir
    Log ('TESSDATA_DIR: ' + $DataDir)

    Log 'Checking Python OCR dependencies.'
    & $Python -c "import PIL, pytesseract, fitz; print('PYTHON_IMPORTS=PASS')"
    if ($LASTEXITCODE -ne 0) {
        Log 'Installing missing OCR Python dependencies.'
        & $Python -m pip install 'PyMuPDF>=1.24' 'pytesseract>=0.3.13' 'Pillow>=10'
        if ($LASTEXITCODE -ne 0) { throw 'Could not install Python OCR dependencies.' }
    }

    $Smoke = Join-Path $env:TEMP 'stt17_ocr_v5_smoke_20261124.py'
    @'
import os, io, re
from PIL import Image, ImageDraw, ImageFont
import pytesseract, fitz
pytesseract.pytesseract.tesseract_cmd = os.environ['TESSERACT_EXE']
data = os.environ['TESSDATA_PREFIX']
langs = pytesseract.get_languages(config='--tessdata-dir "' + data + '"')
assert 'eng' in langs and 'vie' in langs, 'Missing language data: ' + repr(langs)
font_path = r'C:\Windows\Fonts\arialbd.ttf'
try:
    font = ImageFont.truetype(font_path, 88)
except Exception:
    font = ImageFont.load_default()
im = Image.new('RGB', (1800, 360), 'white')
d = ImageDraw.Draw(im)
d.text((70, 90), 'DOCUMENT TEST 12345', font=font, fill='black', stroke_width=1)
config = '--oem 3 --psm 6'
t = pytesseract.image_to_string(im, lang='eng', config=config)
digits = ''.join(re.findall(r'\d', t))
assert '12345' in digits, 'Image OCR did not recover test digits: ' + repr(t)
doc = fitz.open()
page = doc.new_page(width=900, height=180)
pix = fitz.Pixmap(fitz.csRGB, im.width, im.height, im.tobytes(), False)
page.insert_image(page.rect, pixmap=pix)
pdf = os.path.join(os.environ['TEMP'], 'stt17_ocr_v5_scanned_test.pdf')
doc.save(pdf)
doc.close()
doc = fitz.open(pdf)
assert not doc[0].get_text().strip(), 'Expected image-only PDF test fixture'
render = doc[0].get_pixmap(matrix=fitz.Matrix(2,2), alpha=False)
page_image = Image.open(io.BytesIO(render.tobytes('png')))
t2 = pytesseract.image_to_string(page_image, lang='eng', config=config)
digits2 = ''.join(re.findall(r'\d', t2))
assert '12345' in digits2, 'Scanned-PDF OCR did not recover test digits: ' + repr(t2)
doc.close()
print('LANGUAGES=PASS(eng,vie)')
print('IMAGE_OCR=PASS')
print('IMAGE_ONLY_PDF_OCR=PASS')
print('OCR_IMAGE_TEXT=' + repr(t))
print('OCR_PDF_TEXT=' + repr(t2))
'@ | Set-Content -Path $Smoke -Encoding ASCII

    Log 'Running tolerant OCR smoke tests (checks stable digits, not exact character recognition).'
    & $Python $Smoke
    if ($LASTEXITCODE -ne 0) { throw 'OCR smoke test failed. Tesseract is installed, but the generated image/PDF test was not recognized reliably.' }

    $Specific = Join-Path $Backend 'test_healthcare_documents_stt17.py'
    if (Test-Path $Specific) {
        Log 'Running STT17-specific tests.'
        & $Python -m pytest -q -p no:cacheprovider $Specific
        if ($LASTEXITCODE -ne 0) { throw 'STT17-specific pytest failed.' }
    }
    Log 'Running full backend regression tests.'
    Push-Location $Backend
    try {
        & $Python -m pytest -q -p no:cacheprovider
        if ($LASTEXITCODE -ne 0) { throw 'Full backend pytest failed.' }
    } finally { Pop-Location }

    Log 'STT17 OCR RUNTIME VERIFY V5 20261124: PASS'
} catch {
    $Failed = $true
    Log ('FAIL: ' + $_.Exception.Message)
} finally {
    $Log | Set-Content -Path $Report -Encoding ASCII
    Write-Host ('Report: ' + $Report)
}
if ($Failed) { Write-Host 'STT17 OCR RUNTIME VERIFY V5 20261124: FAIL' -ForegroundColor Red; exit 1 }
Write-Host 'STT17 OCR RUNTIME VERIFY V5 20261124: PASS' -ForegroundColor Green
exit 0
