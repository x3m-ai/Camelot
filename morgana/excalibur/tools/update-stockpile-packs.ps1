[CmdletBinding()]
param(
    [string]$StockpileDir = "C:\ProgramData\Morgana\temp\stockpile",
    [switch]$DryRun,
    [switch]$SmokeImport,
    [switch]$AllowLargeReduction,
    [switch]$Publish
)

$ErrorActionPreference = "Stop"

$ToolsDir = $PSScriptRoot
$ExcaliburDir = Split-Path $ToolsDir -Parent
$StockpileOutputDir = Join-Path $ExcaliburDir "stockpile"
$CamelotDir = Split-Path (Split-Path $ExcaliburDir -Parent) -Parent
$StockpileRepository = "https://github.com/mitre/stockpile.git"
$Today = Get-Date -Format "yyyy-MM-dd"
$PublishPaths = @(
    "morgana/excalibur/README.md",
    "morgana/excalibur/stockpile/README.md",
    "morgana/excalibur/stockpile/conversion-report.json",
    "morgana/excalibur/stockpile/stockpile-c2-v1.json",
    "morgana/excalibur/stockpile/stockpile-collection-v1.json",
    "morgana/excalibur/stockpile/stockpile-credaccess-v1.json",
    "morgana/excalibur/stockpile/stockpile-discovery-v1.json",
    "morgana/excalibur/stockpile/stockpile-evasion-v1.json",
    "morgana/excalibur/stockpile/stockpile-exec-v1.json",
    "morgana/excalibur/stockpile/stockpile-exfil-v1.json",
    "morgana/excalibur/stockpile/stockpile-impact-v1.json",
    "morgana/excalibur/stockpile/stockpile-lateral-v1.json",
    "morgana/excalibur/stockpile/stockpile-persist-v1.json",
    "morgana/excalibur/stockpile/stockpile-privesc-v1.json",
    "morgana/excalibur/catalog.json",
    "morgana/excalibur/tools/catalog_guidance.py",
    "morgana/excalibur/tools/convert_stockpile.py",
    "morgana/excalibur/tools/test_catalog_metadata.py",
    "morgana/excalibur/tools/test_convert_stockpile.py",
    "morgana/excalibur/tools/test_stockpile_import.py",
    "morgana/excalibur/tools/update-stockpile-packs.ps1"
)

function Write-Step([string]$Message) { Write-Host ""; Write-Host "[STEP] $Message" -ForegroundColor Cyan }
function Write-OK([string]$Message) { Write-Host "[OK] $Message" -ForegroundColor Green }
function Write-Warn([string]$Message) { Write-Host "[WARN] $Message" -ForegroundColor Yellow }
function Stop-Pipeline([string]$Message) { Write-Host "[FAIL] $Message" -ForegroundColor Red; exit 1 }

Write-Host "=== MITRE Stockpile Pack Update Pipeline ===" -ForegroundColor Magenta
Write-Host "Camelot:   $CamelotDir"
Write-Host "Stockpile: $StockpileDir"
if ($DryRun) { Write-Host "Mode:      DRY RUN" -ForegroundColor Yellow }
if ($Publish) { Write-Host "Publish:   ENABLED" -ForegroundColor Yellow }

Write-Step "Clone or update MITRE Stockpile"
$StockpileParent = Split-Path $StockpileDir -Parent
if (-not (Test-Path $StockpileParent)) {
    New-Item -ItemType Directory -Path $StockpileParent -Force | Out-Null
}
if (-not (Test-Path (Join-Path $StockpileDir ".git"))) {
    & git clone --depth=1 $StockpileRepository $StockpileDir
    if ($LASTEXITCODE -ne 0) { Stop-Pipeline "Stockpile clone failed" }
} else {
    & git -C $StockpileDir pull --ff-only
    if ($LASTEXITCODE -ne 0) { Stop-Pipeline "Stockpile update failed" }
}
$SourceCommit = (& git -C $StockpileDir rev-parse HEAD).Trim()
if ($LASTEXITCODE -ne 0 -or -not $SourceCommit) { Stop-Pipeline "Could not determine Stockpile commit" }
Write-OK "Stockpile commit: $SourceCommit"

Write-Step "Verify Python and PyYAML"
& python -c "import yaml; print(yaml.__version__)"
if ($LASTEXITCODE -ne 0) { Stop-Pipeline "PyYAML is required: python -m pip install pyyaml" }
Write-OK "Python dependencies available"

Write-Step "Run Stockpile converter unit tests"
Push-Location $CamelotDir
try {
    & python -m unittest morgana.excalibur.tools.test_convert_stockpile -v
    if ($LASTEXITCODE -ne 0) { Stop-Pipeline "Stockpile converter unit tests failed" }
} finally {
    Pop-Location
}
Write-OK "Converter unit tests passed"

Write-Step "Convert Stockpile abilities"
$ConverterArgs = @(
    (Join-Path $ToolsDir "convert_stockpile.py"),
    "--stockpile-dir", $StockpileDir,
    "--out-dir", $StockpileOutputDir
)
if ($DryRun) { $ConverterArgs += "--dry-run" }
if ($AllowLargeReduction) { $ConverterArgs += "--allow-large-reduction" }
& python @ConverterArgs
if ($LASTEXITCODE -ne 0) { Stop-Pipeline "Stockpile conversion failed" }
Write-OK "Conversion completed"

if ($DryRun) {
    Write-Host ""
    Write-Host "[OK] Dry run complete. No packs, catalog entries, commits, or pushes were written." -ForegroundColor Green
    exit 0
}

Write-Step "Validate generated packs"
& python (Join-Path $ToolsDir "test_stockpile_import.py") --all --validate-only
if ($LASTEXITCODE -ne 0) { Stop-Pipeline "Static pack validation failed" }
Write-OK "All generated packs passed static validation"

Write-Step "Validate package decision metadata"
& python (Join-Path $ToolsDir "test_catalog_metadata.py")
if ($LASTEXITCODE -ne 0) { Stop-Pipeline "Catalog metadata validation failed" }
Write-OK "All catalog packages include operator guidance"

if ($SmokeImport) {
    Write-Step "Smoke import Discovery pack into local Morgana"
    & python (Join-Path $ToolsDir "test_stockpile_import.py") --pack stockpile-discovery-v1
    if ($LASTEXITCODE -ne 0) { Stop-Pipeline "Morgana smoke import failed" }
    Write-OK "Discovery pack imported successfully"
} else {
    Write-Warn "Morgana smoke import skipped. Use -SmokeImport to enable it."
}

if ($Publish) {
    Write-Step "Publish Stockpile packs to Camelot"
    Push-Location $CamelotDir
    try {
        & git diff --cached --quiet
        if ($LASTEXITCODE -eq 1) {
            Stop-Pipeline "Camelot already has staged changes. Commit or unstage them before -Publish."
        }
        if ($LASTEXITCODE -ne 0) { Stop-Pipeline "Could not inspect the Camelot index" }

        & git add -- $PublishPaths
        if ($LASTEXITCODE -ne 0) { Stop-Pipeline "Could not stage Stockpile publication files" }
        $Status = & git status --porcelain -- $PublishPaths
        if ($Status) {
            & git commit -m "feat: update MITRE Stockpile packs ($Today)"
            if ($LASTEXITCODE -ne 0) { Stop-Pipeline "Camelot commit failed" }
            & git push
            if ($LASTEXITCODE -ne 0) { Stop-Pipeline "Camelot push failed" }
            Write-OK "Camelot pushed. The CDN catalog is now live."
        } else {
            Write-Warn "No Stockpile changes to publish."
        }
    } finally {
        Pop-Location
    }
} else {
    Write-Warn "Publish skipped. Review changes, then rerun with -Publish only when explicitly approved."
}

$PackCount = (Get-ChildItem $StockpileOutputDir -Filter "stockpile-*-v1.json").Count
Write-Host ""
Write-Host "=== Pipeline complete ===" -ForegroundColor Magenta
Write-Host "Source commit: $SourceCommit"
Write-Host "Packs:         $PackCount"
Write-Host "Report:        $(Join-Path $StockpileOutputDir 'conversion-report.json')"
Write-Host "Morgana UI:    Scripts -> Excalibur Packs -> Refresh catalog"
Write-Host ""
Write-Host "After the initial Morgana category/prefix support is deployed, future pack updates require only Camelot publication." -ForegroundColor Green
