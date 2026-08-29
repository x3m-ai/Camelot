[CmdletBinding()]
param(
    [string]$CacheRoot = "C:\ProgramData\Morgana\temp\frida-mobile",
    [switch]$RefreshCodeShare,
    [switch]$RefreshGitHub,
    [switch]$DryRun,
    [switch]$SmokeImport,
    [switch]$Publish
)

$ErrorActionPreference = "Stop"
$ToolsDir = $PSScriptRoot
$ExcaliburDir = Split-Path $ToolsDir -Parent
$OutputDir = Join-Path $ExcaliburDir "mobile\frida"
$Registry = Join-Path $OutputDir "source-registry.json"
$CamelotDir = Split-Path (Split-Path $ExcaliburDir -Parent) -Parent
$AllowedPattern = '^(morgana/excalibur/catalog\.json|morgana/excalibur/mobile/frida/|morgana/excalibur/tools/(convert_frida_mobile\.py|frida_sources\.py|frida_codeshare\.py|frida_github\.py|frida_classifier\.py|frida_dedup\.py|test_convert_frida_mobile\.py|test_frida_mobile_import\.py|update-frida-mobile-packs\.ps1|frida_mobile_mapping_overrides\.json))'
function Step([string]$Message) { Write-Host ""; Write-Host "[STEP] $Message" -ForegroundColor Cyan }
function Fail([string]$Message) { Write-Host "[FAIL] $Message" -ForegroundColor Red; exit 1 }

Write-Host "=== MORGANA FRIDA MOBILE BUILD ===" -ForegroundColor Magenta
Step "Enumerate Frida CodeShare with cache/resume"
$CrawlerArgs = @((Join-Path $ToolsDir "frida_codeshare.py"), "--cache-dir", (Join-Path $CacheRoot "codeshare"), "--workers", "6")
if ($RefreshCodeShare) { $CrawlerArgs += "--refresh" }
& python @CrawlerArgs
if ($LASTEXITCODE -ne 0) { Fail "CodeShare enumeration failed" }

Step "Compile ingestion, converter, and validation tooling"
& python -m py_compile `
    (Join-Path $ToolsDir "convert_frida_mobile.py") (Join-Path $ToolsDir "frida_sources.py") `
    (Join-Path $ToolsDir "frida_codeshare.py") (Join-Path $ToolsDir "frida_github.py") `
    (Join-Path $ToolsDir "frida_classifier.py") (Join-Path $ToolsDir "frida_dedup.py") `
    (Join-Path $ToolsDir "test_convert_frida_mobile.py") (Join-Path $ToolsDir "test_frida_mobile_import.py")
if ($LASTEXITCODE -ne 0) { Fail "Python compilation failed" }
Push-Location $CamelotDir
try { & python -m unittest morgana.excalibur.tools.test_convert_frida_mobile -v } finally { Pop-Location }
if ($LASTEXITCODE -ne 0) { Fail "Frida converter tests failed" }

Step "Convert complete CodeShare and curated repository corpus"
$Arguments = @(
    (Join-Path $ToolsDir "convert_frida_mobile.py"),
    "--codeshare-cache", (Join-Path $CacheRoot "codeshare"),
    "--source-registry", $Registry,
    "--cache-root", $CacheRoot,
    "--out-dir", $OutputDir
)
if ($RefreshGitHub) { $Arguments += "--refresh-github" }
if ($DryRun) { $Arguments += "--dry-run" }
& python @Arguments
if ($LASTEXITCODE -ne 0) { Fail "Frida conversion failed" }
if ($DryRun) { Write-Host "[OK] Dry run completed" -ForegroundColor Green; exit 0 }

Step "Statically validate every generated Script/package/catalog entry"
& python (Join-Path $ToolsDir "test_frida_mobile_import.py") --all --validate-only --validate-js
if ($LASTEXITCODE -ne 0) { Fail "Frida static validation failed" }
& python (Join-Path $ToolsDir "test_catalog_metadata.py")
if ($LASTEXITCODE -ne 0) { Fail "Catalog metadata validation failed" }
Write-Host "[OK] Full static validation passed" -ForegroundColor Green

if ($SmokeImport) {
    Step "Smoke-import one representative Frida package without execution"
    & python (Join-Path $ToolsDir "test_frida_mobile_import.py")
    if ($LASTEXITCODE -ne 0) { Fail "Frida package import failed" }
}

if ($Publish) {
    Step "Publish reviewed Frida Mobile paths"
    Push-Location $CamelotDir
    try {
        & git diff --cached --quiet
        if ($LASTEXITCODE -eq 1) { Fail "Changes are already staged" }
        $Unrelated = @(& git status --porcelain | ForEach-Object { $_.Substring(3).Replace('\','/') } | Where-Object { $_ -notmatch $AllowedPattern })
        if ($Unrelated.Count) { Fail "Unrelated changes exist: $($Unrelated -join ', ')" }
        & git add -- morgana/excalibur/catalog.json morgana/excalibur/mobile/frida `
            morgana/excalibur/tools/convert_frida_mobile.py morgana/excalibur/tools/frida_sources.py `
            morgana/excalibur/tools/frida_codeshare.py morgana/excalibur/tools/frida_github.py `
            morgana/excalibur/tools/frida_classifier.py morgana/excalibur/tools/frida_dedup.py `
            morgana/excalibur/tools/test_convert_frida_mobile.py morgana/excalibur/tools/test_frida_mobile_import.py `
            morgana/excalibur/tools/update-frida-mobile-packs.ps1 morgana/excalibur/tools/frida_mobile_mapping_overrides.json
        $Unexpected = @(& git diff --cached --name-only | Where-Object { $_ -notmatch $AllowedPattern })
        if ($Unexpected.Count) { Fail "Unexpected staged paths: $($Unexpected -join ', ')" }
        & git commit -m "feat: publish Frida mobile emulation packs"
        if ($LASTEXITCODE -ne 0) { Fail "Commit failed" }
        & git push
        if ($LASTEXITCODE -ne 0) { Fail "Push failed" }
    } finally { Pop-Location }
}

$Report = Get-Content (Join-Path $OutputDir "conversion-report.json") -Raw -Encoding UTF8 | ConvertFrom-Json
Write-Host ""
Write-Host "Sources:       $($Report.sources_discovered)"
Write-Host "Source units:  $($Report.source_units_discovered)"
Write-Host "Published:     $($Report.published)"
Write-Host "Exact dupes:   $($Report.exact_duplicates)"
Write-Host "Normalized:    $($Report.normalized_duplicates)"
Write-Host "Derivatives:   $($Report.meaningful_derivatives_retained)"
Write-Host "Malformed:     $($Report.malformed)"
Write-Host "Unsupported:   $($Report.unsupported)"
Write-Host "Packages:      $($Report.packages)"
Write-Host "Validation:    $($Report.validation)"
Write-Host "Runtime tests: executor architecture only; full corpus left for operator labs"