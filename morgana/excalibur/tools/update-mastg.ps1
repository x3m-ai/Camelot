[CmdletBinding()]
param(
    [string]$MastgSource = "C:\ProgramData\Morgana\temp\mastg",
    [string]$PlaygroundSource = "C:\ProgramData\Morgana\temp\MASTG-Hacking-Playground",
    [switch]$DryRun,
    [switch]$Publish
)

$ErrorActionPreference = "Stop"
$ToolsDir = $PSScriptRoot
$ExcaliburDir = Split-Path $ToolsDir -Parent
$OutputDir = Join-Path $ExcaliburDir "mobile\mastg"
$MobileLabDir = Join-Path (Split-Path $ExcaliburDir -Parent) "mobile-lab"
$CamelotDir = Split-Path (Split-Path $ExcaliburDir -Parent) -Parent
$AllowedPattern = '^(morgana/excalibur/catalog\.json|morgana/excalibur/catalog-classification\.json|morgana/excalibur/mobile/mastg/|morgana/excalibur/tools/(mastg_parser\.py|convert_mastg\.py|test_mastg_parser\.py|test_mastg_import\.py|update-mastg\.ps1)|morgana/mobile-lab/(catalog\.json|mastg-coverage\.json|owasp-playground-apps\.json|templates/android-mastg-playground-lab\.json|templates/ios-mastg-playground-lab\.json))'

function Step([string]$Message) { Write-Host ""; Write-Host "[STEP] $Message" -ForegroundColor Cyan }
function Fail([string]$Message) { Write-Host "[FAIL] $Message" -ForegroundColor Red; exit 1 }

Write-Host "=== MORGANA OWASP MASTG + HACKING PLAYGROUND BUILD ===" -ForegroundColor Magenta

Step "Compile MASTG tooling"
& python -m py_compile `
    (Join-Path $ToolsDir "mastg_parser.py") `
    (Join-Path $ToolsDir "convert_mastg.py") `
    (Join-Path $ToolsDir "test_mastg_parser.py") `
    (Join-Path $ToolsDir "test_mastg_import.py")
if ($LASTEXITCODE -ne 0) { Fail "Python compilation failed" }

Step "Run MASTG parser unit tests"
$env:PYTHONPATH = $ToolsDir
& python -m unittest test_mastg_parser
if ($LASTEXITCODE -ne 0) { Fail "MASTG parser unit tests failed" }

Step "Convert complete pinned MASTG + Hacking Playground corpus"
$Args = @((Join-Path $ToolsDir "convert_mastg.py"), "--mastg-source", $MastgSource, "--playground-source", $PlaygroundSource, "--out-dir", $OutputDir)
if ($DryRun) { $Args += "--dry-run" }
& python @Args
if ($LASTEXITCODE -ne 0) { Fail "MASTG conversion failed" }
if ($DryRun) { Write-Host "[OK] Dry run completed" -ForegroundColor Green; exit 0 }

Step "Enrich catalog facets"
& python (Join-Path $ToolsDir "enrich_catalog.py")
if ($LASTEXITCODE -ne 0) { Fail "Catalog enrichment failed" }

Step "Statically validate every generated MASTG package"
& python (Join-Path $ToolsDir "test_mastg_import.py")
if ($LASTEXITCODE -ne 0) { Fail "MASTG static validation failed" }
Write-Host "[OK] Full MASTG static validation passed" -ForegroundColor Green

if ($Publish) {
    Step "Publish reviewed MASTG paths"
    Push-Location $CamelotDir
    try {
        & git diff --cached --quiet
        if ($LASTEXITCODE -eq 1) { Fail "Changes are already staged" }
        $Unrelated = @(& git status --porcelain | ForEach-Object { $_.Substring(3).Replace('\','/') } | Where-Object { $_ -notmatch $AllowedPattern })
        if ($Unrelated.Count) { Fail "Unrelated changes exist: $($Unrelated -join ', ')" }
        & git add -- morgana/excalibur/catalog.json morgana/excalibur/catalog-classification.json `
            morgana/excalibur/mobile/mastg `
            morgana/excalibur/tools/mastg_parser.py morgana/excalibur/tools/convert_mastg.py `
            morgana/excalibur/tools/test_mastg_parser.py morgana/excalibur/tools/test_mastg_import.py `
            morgana/excalibur/tools/update-mastg.ps1 `
            morgana/mobile-lab/catalog.json morgana/mobile-lab/mastg-coverage.json `
            morgana/mobile-lab/owasp-playground-apps.json `
            morgana/mobile-lab/templates/android-mastg-playground-lab.json `
            morgana/mobile-lab/templates/ios-mastg-playground-lab.json
        & git commit -m "feat: publish complete OWASP MASTG + Hacking Playground integration"
        if ($LASTEXITCODE -ne 0) { Fail "Commit failed" }
        & git push
        if ($LASTEXITCODE -ne 0) { Fail "Push failed" }
    } finally { Pop-Location }
}

$Report = Get-Content (Join-Path $OutputDir "mastg-conversion-report.json") -Raw -Encoding UTF8 | ConvertFrom-Json
Write-Host ""
Write-Host "Tests:           $($Report.tests.candidates) (android $($Report.tests.android), ios $($Report.tests.ios))"
Write-Host "Demos:           $($Report.demos.candidates) (frida $($Report.demos.executable_frida))"
Write-Host "References:       knowledge $($Report.references.knowledge), techniques $($Report.references.techniques), tools $($Report.references.tools)"
Write-Host "Playground:       $($Report.playground.candidates) candidates ($($Report.playground.apps) apps, $($Report.playground.backends) backends)"
Write-Host "Tests reconciled: $($Report.reconciliation.tests.android.reconciled -and $Report.reconciliation.tests.ios.reconciled)"
Write-Host "Demos reconciled: $($Report.reconciliation.demos.android.reconciled -and $Report.reconciliation.demos.ios.reconciled)"
