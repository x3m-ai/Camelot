[CmdletBinding()]
param(
    [string]$SourceDir = "C:\ProgramData\Morgana\temp\medusa-source",
    [switch]$ValidateJs,
    [switch]$DryRun,
    [switch]$Publish
)

$ErrorActionPreference = "Stop"
$ToolsDir = $PSScriptRoot
$ExcaliburDir = Split-Path $ToolsDir -Parent
$OutputDir = Join-Path $ExcaliburDir "mobile\medusa"
$CamelotDir = Split-Path (Split-Path $ExcaliburDir -Parent) -Parent
$AllowedPattern = '^(morgana/excalibur/catalog\.json|morgana/excalibur/catalog-classification\.json|morgana/excalibur/mobile/medusa/|morgana/excalibur/tools/(convert_medusa\.py|medusa_compiler\.py|medusa_module_parser\.py|medusa_risk\.py|medusa_risk_overrides\.json|test_medusa_module_parser\.py|test_medusa_runtime\.py|test_medusa_import\.py|update-medusa-packs\.ps1)|morgana/excalibur/PACKAGES\.md|morgana/excalibur/README\.md)'
function Step([string]$Message) { Write-Host ""; Write-Host "[STEP] $Message" -ForegroundColor Cyan }
function Fail([string]$Message) { Write-Host "[FAIL] $Message" -ForegroundColor Red; exit 1 }

Write-Host "=== MORGANA MEDUSA PROVIDER BUILD ===" -ForegroundColor Magenta

Step "Compile MEDUSA tooling"
& python -m py_compile `
    (Join-Path $ToolsDir "convert_medusa.py") (Join-Path $ToolsDir "medusa_compiler.py") `
    (Join-Path $ToolsDir "medusa_module_parser.py") (Join-Path $ToolsDir "medusa_risk.py") `
    (Join-Path $ToolsDir "test_medusa_module_parser.py") (Join-Path $ToolsDir "test_medusa_runtime.py") `
    (Join-Path $ToolsDir "test_medusa_import.py")
if ($LASTEXITCODE -ne 0) { Fail "Python compilation failed" }

Step "Run MEDUSA parser + compiler/runtime unit tests"
$env:MEDUSA_SOURCE = $SourceDir
$env:PYTHONPATH = $ToolsDir
Push-Location $CamelotDir
try {
    & python -m unittest morgana.excalibur.tools.test_medusa_module_parser morgana.excalibur.tools.test_medusa_runtime
    if ($LASTEXITCODE -ne 0) { Fail "MEDUSA unit tests failed" }
} finally { Pop-Location }

Step "Convert complete pinned MEDUSA corpus"
$Args = @((Join-Path $ToolsDir "convert_medusa.py"), "--source", $SourceDir, "--out-dir", $OutputDir)
if ($DryRun) { $Args += "--dry-run" }
& python @Args
if ($LASTEXITCODE -ne 0) { Fail "MEDUSA conversion failed" }
if ($DryRun) { Write-Host "[OK] Dry run completed" -ForegroundColor Green; exit 0 }

Step "Enrich catalog facets (dynamic providers/specialties/risk)"
& python (Join-Path $ToolsDir "enrich_catalog.py")
if ($LASTEXITCODE -ne 0) { Fail "Catalog enrichment failed" }

Step "Statically validate every generated Script/package"
$ValidateArgs = @((Join-Path $ToolsDir "test_medusa_import.py"))
if ($ValidateJs) { $ValidateArgs += "--validate-js" }
& python @ValidateArgs
if ($LASTEXITCODE -ne 0) { Fail "MEDUSA static validation failed" }
Write-Host "[OK] Full MEDUSA static validation passed" -ForegroundColor Green

if ($Publish) {
    Step "Publish reviewed MEDUSA paths"
    Push-Location $CamelotDir
    try {
        & git diff --cached --quiet
        if ($LASTEXITCODE -eq 1) { Fail "Changes are already staged" }
        $Unrelated = @(& git status --porcelain | ForEach-Object { $_.Substring(3).Replace('\','/') } | Where-Object { $_ -notmatch $AllowedPattern })
        if ($Unrelated.Count) { Fail "Unrelated changes exist: $($Unrelated -join ', ')" }
        & git add -- morgana/excalibur/catalog.json morgana/excalibur/catalog-classification.json `
            morgana/excalibur/mobile/medusa morgana/excalibur/PACKAGES.md morgana/excalibur/README.md `
            morgana/excalibur/tools/convert_medusa.py morgana/excalibur/tools/medusa_compiler.py `
            morgana/excalibur/tools/medusa_module_parser.py morgana/excalibur/tools/medusa_risk.py `
            morgana/excalibur/tools/medusa_risk_overrides.json `
            morgana/excalibur/tools/test_medusa_module_parser.py morgana/excalibur/tools/test_medusa_runtime.py `
            morgana/excalibur/tools/test_medusa_import.py morgana/excalibur/tools/update-medusa-packs.ps1
        $Unexpected = @(& git diff --cached --name-only | Where-Object { $_ -notmatch $AllowedPattern })
        if ($Unexpected.Count) { Fail "Unexpected staged paths: $($Unexpected -join ', ')" }
        & git commit -m "feat: publish complete MEDUSA mobile instrumentation provider"
        if ($LASTEXITCODE -ne 0) { Fail "Commit failed" }
        & git push
        if ($LASTEXITCODE -ne 0) { Fail "Push failed" }
    } finally { Pop-Location }
}

$Report = Get-Content (Join-Path $OutputDir "conversion-report.json") -Raw -Encoding UTF8 | ConvertFrom-Json
Write-Host ""
Write-Host "Source commit: $($Report.source_commit)"
Write-Host "Modules:       $($Report.valid_android_modules + $Report.valid_ios_modules) ($($Report.valid_android_modules) Android / $($Report.valid_ios_modules) iOS)"
Write-Host "Snippets:      $($Report.standalone_scripts)"
Write-Host "Published:     $($Report.executable_scripts + $Report.executable_snippets)"
Write-Host "Manual:        $($Report.manual_scripts)"
Write-Host "Packages:      $($Report.packages)"
Write-Host "Reconciled:    $($Report.source_reconciled)"
Write-Host "Runtime:       executor architecture only; full corpus left for operator mobile labs"
