[CmdletBinding()]
param(
    [string]$LolbasDir = "C:\ProgramData\Morgana\temp\lolbas",
    [string]$GtfobinsDir = "C:\ProgramData\Morgana\temp\gtfobins",
    [int]$MaxPerPack = 400,
    [switch]$DryRun,
    [switch]$SmokeImport,
    [switch]$Publish
)

$ErrorActionPreference = "Stop"
$ToolsDir = $PSScriptRoot
$ExcaliburDir = Split-Path $ToolsDir -Parent
$OutputDir = Join-Path $ExcaliburDir "lotl"
$CamelotDir = Split-Path (Split-Path $ExcaliburDir -Parent) -Parent
$LolbasRepository = "https://github.com/LOLBAS-Project/LOLBAS.git"
$GtfobinsRepository = "https://github.com/GTFOBins/GTFOBins.github.io.git"
$AllowedPattern = '^(morgana/excalibur/catalog\.json|morgana/excalibur/lotl/|morgana/excalibur/tools/(convert_lotl\.py|convert_lolbas\.py|convert_gtfobins\.py|test_convert_lotl\.py|test_lotl_import\.py|update-lotl-packs\.ps1|lotl_risk_overrides\.json))'

function Write-Step([string]$Message) { Write-Host ""; Write-Host "[STEP] $Message" -ForegroundColor Cyan }
function Write-OK([string]$Message) { Write-Host "[OK] $Message" -ForegroundColor Green }
function Stop-Pipeline([string]$Message) { Write-Host "[FAIL] $Message" -ForegroundColor Red; exit 1 }

function Update-Checkout([string]$Repository, [string]$Directory) {
    $Parent = Split-Path $Directory -Parent
    if (-not (Test-Path $Parent)) { New-Item -ItemType Directory -Path $Parent -Force | Out-Null }
    if (-not (Test-Path (Join-Path $Directory ".git"))) {
        & git clone $Repository $Directory
    } else {
        & git -C $Directory fetch --prune
        if ($LASTEXITCODE -eq 0) { & git -C $Directory pull --ff-only }
    }
    if ($LASTEXITCODE -ne 0) { Stop-Pipeline "Could not update $Repository" }
}

Write-Host "=== MORGANA LIVING-OFF-THE-LAND BUILD ===" -ForegroundColor Magenta
Write-Step "Update LOLBAS and GTFOBins source checkouts"
Update-Checkout $LolbasRepository $LolbasDir
Update-Checkout $GtfobinsRepository $GtfobinsDir
$LolbasSha = (& git -C $LolbasDir rev-parse HEAD).Trim()
$GtfobinsSha = (& git -C $GtfobinsDir rev-parse HEAD).Trim()
Write-OK "LOLBAS: $LolbasSha"
Write-OK "GTFOBins: $GtfobinsSha"

Write-Step "Compile converters and run compact fixture tests"
Push-Location $CamelotDir
try {
    & python -m py_compile `
        (Join-Path $ToolsDir "convert_lotl.py") `
        (Join-Path $ToolsDir "convert_lolbas.py") `
        (Join-Path $ToolsDir "convert_gtfobins.py") `
        (Join-Path $ToolsDir "test_convert_lotl.py") `
        (Join-Path $ToolsDir "test_lotl_import.py")
    if ($LASTEXITCODE -ne 0) { Stop-Pipeline "Python compilation failed" }
    & python -m unittest morgana.excalibur.tools.test_convert_lotl -v
    if ($LASTEXITCODE -ne 0) { Stop-Pipeline "LOTL converter tests failed" }
} finally { Pop-Location }

Write-Step "Convert complete source corpus"
$Arguments = @(
    (Join-Path $ToolsDir "convert_lotl.py"),
    "--lolbas-dir", $LolbasDir,
    "--gtfobins-dir", $GtfobinsDir,
    "--out-dir", $OutputDir,
    "--max-per-pack", $MaxPerPack
)
if ($DryRun) { $Arguments += "--dry-run" }
& python @Arguments
if ($LASTEXITCODE -ne 0) { Stop-Pipeline "LOTL conversion failed" }
if ($DryRun) { Write-OK "Dry run completed without output or catalog changes"; exit 0 }

Write-Step "Statically validate every generated package and catalog entry"
& python (Join-Path $ToolsDir "test_lotl_import.py") --all --validate-only
if ($LASTEXITCODE -ne 0) { Stop-Pipeline "LOTL static validation failed" }
& python (Join-Path $ToolsDir "test_catalog_metadata.py")
if ($LASTEXITCODE -ne 0) { Stop-Pipeline "Catalog metadata validation failed" }
Write-OK "All generated content passed static validation"

if ($SmokeImport) {
    Write-Step "Smoke-import one representative pack per provider without execution"
    & python (Join-Path $ToolsDir "test_lotl_import.py") --provider lolbas
    if ($LASTEXITCODE -ne 0) { Stop-Pipeline "LOLBAS smoke import failed" }
    & python (Join-Path $ToolsDir "test_lotl_import.py") --provider gtfobins
    if ($LASTEXITCODE -ne 0) { Stop-Pipeline "GTFOBins smoke import failed" }
    Write-OK "Representative smoke imports passed; no Script was executed"
}

if ($Publish) {
    Write-Step "Publish reviewed LOTL paths"
    Push-Location $CamelotDir
    try {
        & git diff --cached --quiet
        if ($LASTEXITCODE -eq 1) { Stop-Pipeline "Changes are already staged" }
        $Unrelated = @(& git status --porcelain | ForEach-Object { $_.Substring(3).Replace('\','/') } | Where-Object { $_ -notmatch $AllowedPattern })
        if ($Unrelated.Count -gt 0) { Stop-Pipeline "Unrelated changes exist: $($Unrelated -join ', ')" }
        & git add -- morgana/excalibur/catalog.json morgana/excalibur/lotl `
            morgana/excalibur/tools/convert_lotl.py morgana/excalibur/tools/convert_lolbas.py `
            morgana/excalibur/tools/convert_gtfobins.py morgana/excalibur/tools/test_convert_lotl.py `
            morgana/excalibur/tools/test_lotl_import.py morgana/excalibur/tools/update-lotl-packs.ps1 `
            morgana/excalibur/tools/lotl_risk_overrides.json
        $Unexpected = @(& git diff --cached --name-only | Where-Object { $_ -notmatch $AllowedPattern })
        if ($Unexpected.Count -gt 0) { Stop-Pipeline "Unexpected staged paths: $($Unexpected -join ', ')" }
        & git commit -m "feat: publish LOLBAS and GTFOBins packs"
        if ($LASTEXITCODE -ne 0) { Stop-Pipeline "Commit failed" }
        & git push
        if ($LASTEXITCODE -ne 0) { Stop-Pipeline "Push failed" }
    } finally { Pop-Location }
}

$Report = Get-Content (Join-Path $OutputDir "conversion-report.json") -Raw | ConvertFrom-Json
Write-Host ""
Write-Host "LOLBAS" -ForegroundColor Cyan
Write-Host "Source commit: $($Report.lolbas.source_commit)"
Write-Host "Objects:       $($Report.lolbas.source_objects)"
Write-Host "Commands:      $($Report.lolbas.source_entries)"
Write-Host "Raw variants:  $($Report.lolbas.raw_variants)"
Write-Host "Published:     $($Report.lolbas.published)"
Write-Host "Skipped:       $($Report.lolbas.skipped)"
Write-Host "Duplicates:    $($Report.lolbas.duplicates)"
Write-Host "Packs:         $($Report.lolbas.packs)"
Write-Host ""
Write-Host "GTFOBins" -ForegroundColor Cyan
Write-Host "Source commit:    $($Report.gtfobins.source_commit)"
Write-Host "Bins:             $($Report.gtfobins.metrics.bin_files_scanned)"
Write-Host "Functions:        $($Report.gtfobins.metrics.function_definitions)"
Write-Host "Direct snippets:  $($Report.gtfobins.metrics.direct_snippet_entries)"
Write-Host "Context variants: $($Report.gtfobins.context_expansions)"
Write-Host "Raw variants:     $($Report.gtfobins.raw_variants)"
Write-Host "Published:        $($Report.gtfobins.published)"
Write-Host "Skipped:          $($Report.gtfobins.skipped)"
Write-Host "Duplicates:       $($Report.gtfobins.duplicates)"
Write-Host "Packs:            $($Report.gtfobins.packs)"
Write-Host ""
Write-Host "COMBINED" -ForegroundColor Cyan
Write-Host "Scripts:           $($Report.combined.published_scripts)"
Write-Host "Packs:             $($Report.combined.packs)"
Write-Host "ATT&CK techniques: $($Report.combined.unique_tcodes)"
Write-Host "Windows:           $($Report.combined.windows)"
Write-Host "Linux:             $($Report.combined.linux)"
Write-Host "Validation:        $($Report.combined.validation)"
Write-Host "Smoke imports:     $(if ($SmokeImport) { 'LOLBAS PASS / GTFOBins PASS' } else { 'not requested' })"
Write-Host "Runtime execution: representative only / left for operator validation"