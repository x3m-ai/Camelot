[CmdletBinding()]
param(
    [string]$CoreSource = "C:\ProgramData\Morgana\temp\drozer-source",
    [string]$ModulesSource = "C:\ProgramData\Morgana\temp\drozer-modules-source",
    [switch]$DryRun,
    [switch]$Publish
)

$ErrorActionPreference = "Stop"
$ToolsDir = $PSScriptRoot
$ExcaliburDir = Split-Path $ToolsDir -Parent
$OutputDir = Join-Path $ExcaliburDir "mobile\drozer"
$CamelotDir = Split-Path (Split-Path $ExcaliburDir -Parent) -Parent
$AllowedPattern = '^(morgana/excalibur/catalog\.json|morgana/excalibur/catalog-classification\.json|morgana/excalibur/mobile/drozer/|morgana/excalibur/tools/(convert_drozer\.py|drozer_module_parser\.py|drozer_risk\.py|test_drozer_module_parser\.py|test_drozer_import\.py|update-drozer\.ps1))'

function Step([string]$Message) { Write-Host ""; Write-Host "[STEP] $Message" -ForegroundColor Cyan }
function Fail([string]$Message) { Write-Host "[FAIL] $Message" -ForegroundColor Red; exit 1 }

Write-Host "=== MORGANA DROZER PROVIDER BUILD ===" -ForegroundColor Magenta

Step "Compile Drozer tooling"
& python -m py_compile `
    (Join-Path $ToolsDir "convert_drozer.py") `
    (Join-Path $ToolsDir "drozer_module_parser.py") `
    (Join-Path $ToolsDir "drozer_risk.py") `
    (Join-Path $ToolsDir "test_drozer_module_parser.py") `
    (Join-Path $ToolsDir "test_drozer_import.py")
if ($LASTEXITCODE -ne 0) { Fail "Python compilation failed" }

Step "Run Drozer parser unit tests"
$env:PYTHONPATH = $ToolsDir
Push-Location $CamelotDir
try {
    & python -m unittest morgana.excalibur.tools.test_drozer_module_parser
    if ($LASTEXITCODE -ne 0) { Fail "Drozer parser unit tests failed" }
} finally { Pop-Location }

Step "Convert complete pinned Drozer corpus (core + drozer-modules)"
$Args = @((Join-Path $ToolsDir "convert_drozer.py"), "--core-source", $CoreSource, "--modules-source", $ModulesSource, "--out-dir", $OutputDir)
if ($DryRun) { $Args += "--dry-run" }
& python @Args
if ($LASTEXITCODE -ne 0) { Fail "Drozer conversion failed" }
if ($DryRun) { Write-Host "[OK] Dry run completed" -ForegroundColor Green; exit 0 }

Step "Enrich catalog facets (dynamic providers/specialties/risk)"
& python (Join-Path $ToolsDir "enrich_catalog.py")
if ($LASTEXITCODE -ne 0) { Fail "Catalog enrichment failed" }

Step "Statically validate every generated Drozer Script/package"
& python (Join-Path $ToolsDir "test_drozer_import.py")
if ($LASTEXITCODE -ne 0) { Fail "Drozer static validation failed" }
Write-Host "[OK] Full Drozer static validation passed" -ForegroundColor Green

if ($Publish) {
    Step "Publish reviewed Drozer paths"
    Push-Location $CamelotDir
    try {
        & git diff --cached --quiet
        if ($LASTEXITCODE -eq 1) { Fail "Changes are already staged" }
        $Unrelated = @(& git status --porcelain | ForEach-Object { $_.Substring(3).Replace('\','/') } | Where-Object { $_ -notmatch $AllowedPattern })
        if ($Unrelated.Count) { Fail "Unrelated changes exist: $($Unrelated -join ', ')" }
        & git add -- morgana/excalibur/catalog.json morgana/excalibur/catalog-classification.json `
            morgana/excalibur/mobile/drozer `
            morgana/excalibur/tools/convert_drozer.py morgana/excalibur/tools/drozer_module_parser.py `
            morgana/excalibur/tools/drozer_risk.py `
            morgana/excalibur/tools/test_drozer_module_parser.py morgana/excalibur/tools/test_drozer_import.py `
            morgana/excalibur/tools/update-drozer.ps1
        $Unexpected = @(& git diff --cached --name-only | Where-Object { $_ -notmatch $AllowedPattern })
        if ($Unexpected.Count) { Fail "Unexpected staged paths: $($Unexpected -join ', ')" }
        & git commit -m "feat: publish complete Drozer Android application-security provider"
        if ($LASTEXITCODE -ne 0) { Fail "Commit failed" }
        & git push
        if ($LASTEXITCODE -ne 0) { Fail "Push failed" }
    } finally { Pop-Location }
}

$Report = Get-Content (Join-Path $OutputDir "drozer-conversion-report.json") -Raw -Encoding UTF8 | ConvertFrom-Json
Write-Host ""
Write-Host "Core candidates:     $($Report.core.candidates) (executable $($Report.core.executable))"
Write-Host "External candidates: $($Report.external.candidates) (executable $($Report.external.executable))"
Write-Host "Published scripts:   $($Report.published_scripts)"
Write-Host "Packages:            $($Report.packages)"
Write-Host "Namespaces:          $($Report.namespaces -join ', ')"
Write-Host "Core reconciled:     $($Report.reconciliation.core_reconciled)"
Write-Host "External reconciled: $($Report.reconciliation.external_reconciled)"
Write-Host "Silent loss:         $($Report.reconciliation.silent_loss)"
Write-Host "Runtime:             single generic drozer_runner asset over pinned isolated runtime"
