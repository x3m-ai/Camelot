[CmdletBinding()]
param(
    [string]$CalderaOtDir = "C:\ProgramData\Morgana\temp\caldera-ot",
    [switch]$DryRun,
    [switch]$SmokeImport,
    [switch]$Publish
)

$ErrorActionPreference = "Stop"
$ToolsDir = $PSScriptRoot
$ExcaliburDir = Split-Path $ToolsDir -Parent
$OutputDir = Join-Path $ExcaliburDir "ot"
$CamelotDir = Split-Path (Split-Path $ExcaliburDir -Parent) -Parent
$Repository = "https://github.com/mitre/caldera-ot.git"
$AllowedPattern = '^(morgana/excalibur/catalog\.json|morgana/excalibur/ot/|morgana/excalibur/tools/(catalog_guidance\.py|convert_caldera_ot\.py|test_catalog_metadata\.py|test_convert_caldera_ot\.py|test_caldera_ot_import\.py|update-caldera-ot-packs\.ps1|caldera_ot_risk_overrides\.json))'

function Write-Step([string]$Message) { Write-Host ""; Write-Host "[STEP] $Message" -ForegroundColor Cyan }
function Write-OK([string]$Message) { Write-Host "[OK] $Message" -ForegroundColor Green }
function Write-Warn([string]$Message) { Write-Host "[WARN] $Message" -ForegroundColor Yellow }
function Stop-Pipeline([string]$Message) { Write-Host "[FAIL] $Message" -ForegroundColor Red; exit 1 }

Write-Host "=== MITRE CALDERA for OT Pack Update Pipeline ===" -ForegroundColor Magenta
Write-Host "Camelot:    $CamelotDir"
Write-Host "CALDERA OT: $CalderaOtDir"

if ($Publish) {
    Write-Step "Verify the Camelot worktree is safe to publish"
    Push-Location $CamelotDir
    try {
        & git diff --cached --quiet
        if ($LASTEXITCODE -eq 1) { Stop-Pipeline "Refusing -Publish because changes are already staged." }
        if ($LASTEXITCODE -ne 0) { Stop-Pipeline "Could not inspect staged changes." }
        $Unrelated = @(& git status --porcelain | ForEach-Object { $_.Substring(3).Replace('\', '/') } | Where-Object { $_ -notmatch $AllowedPattern })
        if ($Unrelated.Count -gt 0) { Stop-Pipeline "Refusing -Publish because unrelated changes exist: $($Unrelated -join ', ')" }
    } finally {
        Pop-Location
    }
    Write-OK "No pre-staged or unrelated changes"
}

Write-Step "Clone or update the recursive official checkout"
$Parent = Split-Path $CalderaOtDir -Parent
if (-not (Test-Path $Parent)) { New-Item -ItemType Directory -Path $Parent -Force | Out-Null }
if (-not (Test-Path (Join-Path $CalderaOtDir ".git"))) {
    & git clone --recursive $Repository $CalderaOtDir
    if ($LASTEXITCODE -ne 0) { Stop-Pipeline "Recursive clone failed." }
} else {
    & git -C $CalderaOtDir fetch --prune
    if ($LASTEXITCODE -ne 0) { Stop-Pipeline "Fetch failed." }
    & git -C $CalderaOtDir pull --ff-only
    if ($LASTEXITCODE -ne 0) { Stop-Pipeline "Fast-forward update failed." }
    & git -C $CalderaOtDir submodule sync --recursive
    if ($LASTEXITCODE -ne 0) { Stop-Pipeline "Submodule sync failed." }
    & git -C $CalderaOtDir submodule update --init --recursive
    if ($LASTEXITCODE -ne 0) { Stop-Pipeline "Submodule update failed." }
}
$UmbrellaSha = (& git -C $CalderaOtDir rev-parse HEAD).Trim()
if (-not $UmbrellaSha) { Stop-Pipeline "Could not determine the umbrella SHA." }
Write-OK "Umbrella SHA: $UmbrellaSha"
foreach ($Plugin in @("bacnet", "dnp3", "modbus", "profinet", "iec61850", "gems")) {
    $PluginSha = (& git -C (Join-Path $CalderaOtDir $Plugin) rev-parse HEAD).Trim()
    if (-not $PluginSha) { Stop-Pipeline "Could not determine $Plugin SHA." }
    Write-Host "  $($Plugin.PadRight(10)) $PluginSha"
}

Write-Step "Run fixture-only unit and Python static checks"
Push-Location $CamelotDir
try {
    & python -m unittest morgana.excalibur.tools.test_convert_caldera_ot -v
    if ($LASTEXITCODE -ne 0) { Stop-Pipeline "Converter unit tests failed." }
    & python -m py_compile `
        (Join-Path $ToolsDir "convert_caldera_ot.py") `
        (Join-Path $ToolsDir "test_convert_caldera_ot.py") `
        (Join-Path $ToolsDir "test_caldera_ot_import.py")
    if ($LASTEXITCODE -ne 0) { Stop-Pipeline "Python static compilation failed." }
} finally {
    Pop-Location
}
Write-OK "Unit and static checks passed"

Write-Step "Verify deterministic conversion in isolated temporary outputs"
$ScratchRoot = Split-Path $CalderaOtDir -Parent
$First = Join-Path $ScratchRoot "caldera-ot-determinism-a"
$Second = Join-Path $ScratchRoot "caldera-ot-determinism-b"
Remove-Item $First, $Second -Recurse -Force -ErrorAction SilentlyContinue
& python (Join-Path $ToolsDir "convert_caldera_ot.py") --caldera-ot-dir $CalderaOtDir --out-dir $First --no-update-catalog
if ($LASTEXITCODE -ne 0) { Stop-Pipeline "First determinism conversion failed." }
& python (Join-Path $ToolsDir "convert_caldera_ot.py") --caldera-ot-dir $CalderaOtDir --out-dir $Second --no-update-catalog
if ($LASTEXITCODE -ne 0) { Stop-Pipeline "Second determinism conversion failed." }
$FirstHashes = Get-ChildItem $First -Recurse -File | ForEach-Object { "$(($_.FullName.Substring($First.Length)).Replace('\', '/')) $((Get-FileHash $_.FullName -Algorithm SHA256).Hash)" }
$SecondHashes = Get-ChildItem $Second -Recurse -File | ForEach-Object { "$(($_.FullName.Substring($Second.Length)).Replace('\', '/')) $((Get-FileHash $_.FullName -Algorithm SHA256).Hash)" }
if (Compare-Object $FirstHashes $SecondHashes) { Stop-Pipeline "Determinism check failed." }
Remove-Item $First, $Second -Recurse -Force
Write-OK "Determinism check passed"

Write-Step "Convert the pinned official content"
$Arguments = @(
    (Join-Path $ToolsDir "convert_caldera_ot.py"),
    "--caldera-ot-dir", $CalderaOtDir,
    "--out-dir", $OutputDir
)
if ($DryRun) { $Arguments += "--dry-run" }
& python @Arguments
if ($LASTEXITCODE -ne 0) { Stop-Pipeline "CALDERA OT conversion failed." }
if ($DryRun) { Write-OK "Dry run completed without replacing output or catalog."; exit 0 }

Write-Step "Run static validation over every generated pack"
& python (Join-Path $ToolsDir "test_caldera_ot_import.py") --all --validate-only
if ($LASTEXITCODE -ne 0) { Stop-Pipeline "Generated pack validation failed." }
Write-OK "All generated packs passed static validation"

Write-Step "Validate package decision metadata"
& python (Join-Path $ToolsDir "test_catalog_metadata.py")
if ($LASTEXITCODE -ne 0) { Stop-Pipeline "Catalog metadata validation failed." }
Write-OK "All catalog packages include operator guidance"

if ($SmokeImport) {
    Write-Step "Import the smallest all-observe pack into loopback Morgana"
    & python (Join-Path $ToolsDir "test_caldera_ot_import.py")
    if ($LASTEXITCODE -ne 0) { Stop-Pipeline "Optional loopback smoke import failed." }
    Write-OK "Optional safe smoke import passed"
} else {
    Write-Warn "Morgana import skipped. Use -SmokeImport explicitly to enable it."
}

if ($Publish) {
    Write-Step "Publish only the reviewed CALDERA OT paths"
    Push-Location $CamelotDir
    try {
        & git add -- morgana/excalibur/catalog.json morgana/excalibur/ot `
            morgana/excalibur/tools/catalog_guidance.py `
            morgana/excalibur/tools/convert_caldera_ot.py `
            morgana/excalibur/tools/test_catalog_metadata.py `
            morgana/excalibur/tools/test_convert_caldera_ot.py `
            morgana/excalibur/tools/test_caldera_ot_import.py `
            morgana/excalibur/tools/update-caldera-ot-packs.ps1 `
            morgana/excalibur/tools/caldera_ot_risk_overrides.json
        if ($LASTEXITCODE -ne 0) { Stop-Pipeline "Could not stage approved OT paths." }
        $Staged = @(& git diff --cached --name-only)
        $Unexpected = @($Staged | Where-Object { $_ -notmatch $AllowedPattern })
        if ($Unexpected.Count -gt 0) { Stop-Pipeline "Unexpected staged paths: $($Unexpected -join ', ')" }
        if ($Staged.Count -eq 0) { Write-Warn "No OT changes to publish." }
        else {
            & git commit -m "feat: publish MITRE CALDERA for OT packs"
            if ($LASTEXITCODE -ne 0) { Stop-Pipeline "Commit failed." }
            & git push
            if ($LASTEXITCODE -ne 0) { Stop-Pipeline "Push failed." }
            Write-OK "OT packs published"
        }
    } finally {
        Pop-Location
    }
} else {
    Write-Warn "Publish skipped. Rerun with -Publish only after explicit approval."
}

Write-Host ""
Write-Host "=== Pipeline complete ===" -ForegroundColor Magenta
Write-Host "Umbrella SHA: $UmbrellaSha"
Write-Host "Report:       $(Join-Path $OutputDir 'conversion-report.json')"