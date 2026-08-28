[CmdletBinding()]
param(
    [string]$SourceDir = "C:\ProgramData\Morgana\temp\loldrivers",
    [int]$MaxPerPack = 400,
    [switch]$DryRun,
    [switch]$SmokeImport,
    [switch]$Publish
)

$ErrorActionPreference = "Stop"
$ToolsDir = $PSScriptRoot
$ExcaliburDir = Split-Path $ToolsDir -Parent
$OutputDir = Join-Path $ExcaliburDir "loldrivers"
$CamelotDir = Split-Path (Split-Path $ExcaliburDir -Parent) -Parent
$Repository = "https://github.com/magicsword-io/LOLDrivers.git"
$AllowedPattern = '^(morgana/excalibur/catalog\.json|morgana/excalibur/loldrivers/|morgana/excalibur/tools/(convert_loldrivers\.py|test_convert_loldrivers\.py|test_loldrivers_import\.py|update-loldrivers-packs\.ps1|loldrivers_overrides\.json))'

function Write-Step([string]$Message) { Write-Host ""; Write-Host "[STEP] $Message" -ForegroundColor Cyan }
function Write-OK([string]$Message) { Write-Host "[OK] $Message" -ForegroundColor Green }
function Stop-Pipeline([string]$Message) { Write-Host "[FAIL] $Message" -ForegroundColor Red; exit 1 }

Write-Host "=== MORGANA LOLDRIVERS BUILD ===" -ForegroundColor Magenta
Write-Step "Update LOLDrivers metadata without LFS binary materialization"
$env:GIT_LFS_SKIP_SMUDGE = "1"
if (-not (Test-Path (Split-Path $SourceDir -Parent))) { New-Item -ItemType Directory -Path (Split-Path $SourceDir -Parent) -Force | Out-Null }
if (-not (Test-Path (Join-Path $SourceDir ".git"))) {
    & git clone --filter=blob:none $Repository $SourceDir
} else {
    & git -C $SourceDir fetch --prune
    if ($LASTEXITCODE -eq 0) { & git -C $SourceDir pull --ff-only }
}
if ($LASTEXITCODE -ne 0) { Stop-Pipeline "LOLDrivers source update failed" }
$SourceSha = (& git -C $SourceDir rev-parse HEAD).Trim()
Write-OK "LOLDrivers: $SourceSha"

Write-Step "Compile converter and run compact fixture tests"
Push-Location $CamelotDir
try {
    & python -m py_compile (Join-Path $ToolsDir "convert_loldrivers.py") (Join-Path $ToolsDir "test_convert_loldrivers.py") (Join-Path $ToolsDir "test_loldrivers_import.py")
    if ($LASTEXITCODE -ne 0) { Stop-Pipeline "Python compilation failed" }
    & python -m unittest morgana.excalibur.tools.test_convert_loldrivers -v
    if ($LASTEXITCODE -ne 0) { Stop-Pipeline "Converter tests failed" }
} finally { Pop-Location }

Write-Step "Convert complete LOLDrivers metadata corpus"
$Arguments = @((Join-Path $ToolsDir "convert_loldrivers.py"), "--source-dir", $SourceDir, "--out-dir", $OutputDir, "--max-per-pack", $MaxPerPack)
if ($DryRun) { $Arguments += "--dry-run" }
& python @Arguments
if ($LASTEXITCODE -ne 0) { Stop-Pipeline "Conversion failed" }
if ($DryRun) { Write-OK "Dry run completed without output/catalog changes"; exit 0 }

Write-Step "Statically validate every generated Script, package, and catalog entry"
& python (Join-Path $ToolsDir "test_loldrivers_import.py") --all --validate-only
if ($LASTEXITCODE -ne 0) { Stop-Pipeline "Static package validation failed" }
& python (Join-Path $ToolsDir "test_catalog_metadata.py")
if ($LASTEXITCODE -ne 0) { Stop-Pipeline "Catalog metadata validation failed" }

Write-Step "Parse every generated PowerShell command"
$ParserFailures = 0
Get-ChildItem $OutputDir -Recurse -Filter "*.json" | Where-Object { $_.Directory.Name -in @("vulnerable", "malicious", "detection") } | ForEach-Object {
    $Package = Get-Content $_.FullName -Raw -Encoding UTF8 | ConvertFrom-Json
    foreach ($Script in $Package.scripts) {
        $Tokens = $null; $Errors = $null
        [System.Management.Automation.Language.Parser]::ParseInput([string]$Script.command, [ref]$Tokens, [ref]$Errors) | Out-Null
        if (@($Errors).Count) { $ParserFailures += @($Errors).Count; Write-Host "[FAIL] $($Script.name): $($Errors[0].Message)" }
    }
}
if ($ParserFailures -ne 0) { Stop-Pipeline "$ParserFailures PowerShell parser errors" }
Write-OK "All generated content passed static validation"

if ($SmokeImport) {
    Write-Step "Smoke-import one vulnerable and one malicious package without execution"
    & python (Join-Path $ToolsDir "test_loldrivers_import.py") --category vulnerable
    if ($LASTEXITCODE -ne 0) { Stop-Pipeline "Vulnerable package smoke import failed" }
    & python (Join-Path $ToolsDir "test_loldrivers_import.py") --category malicious
    if ($LASTEXITCODE -ne 0) { Stop-Pipeline "Malicious package smoke import failed" }
    Write-OK "Representative imports passed; no Script executed"
}

if ($Publish) {
    Write-Step "Publish reviewed LOLDrivers paths"
    Push-Location $CamelotDir
    try {
        & git diff --cached --quiet
        if ($LASTEXITCODE -eq 1) { Stop-Pipeline "Changes are already staged" }
        $Unrelated = @(& git status --porcelain | ForEach-Object { $_.Substring(3).Replace('\','/') } | Where-Object { $_ -notmatch $AllowedPattern })
        if ($Unrelated.Count) { Stop-Pipeline "Unrelated changes exist: $($Unrelated -join ', ')" }
        & git add -- morgana/excalibur/catalog.json morgana/excalibur/loldrivers `
            morgana/excalibur/tools/convert_loldrivers.py morgana/excalibur/tools/test_convert_loldrivers.py `
            morgana/excalibur/tools/test_loldrivers_import.py morgana/excalibur/tools/update-loldrivers-packs.ps1 `
            morgana/excalibur/tools/loldrivers_overrides.json
        $Unexpected = @(& git diff --cached --name-only | Where-Object { $_ -notmatch $AllowedPattern })
        if ($Unexpected.Count) { Stop-Pipeline "Unexpected staged paths: $($Unexpected -join ', ')" }
        & git commit -m "feat: publish LOLDrivers driver-security packs"
        if ($LASTEXITCODE -ne 0) { Stop-Pipeline "Commit failed" }
        & git push
        if ($LASTEXITCODE -ne 0) { Stop-Pipeline "Push failed" }
    } finally { Pop-Location }
}

$Report = Get-Content (Join-Path $OutputDir "conversion-report.json") -Raw -Encoding UTF8 | ConvertFrom-Json
Write-Host ""
Write-Host "Source commit:       $($Report.source_commit)"
Write-Host "YAML objects:        $($Report.yaml_objects)"
Write-Host "Sample associations: $($Report.sample_associations)"
Write-Host "Unique samples:      $($Report.unique_samples)"
Write-Host "Candidate variants:  $($Report.candidate_variants)"
Write-Host "Published:           $($Report.published)"
Write-Host "Packs:               $($Report.packs)"
Write-Host "Validation:          $($Report.validation)"
Write-Host "Runtime validation:  representative only / exhaustive corpus left for operator lab"