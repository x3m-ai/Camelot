[CmdletBinding()]
param(
    [string]$LibraryDir = "C:\ProgramData\Morgana\temp\adversary_emulation_library",
    [string]$EmuDir = "C:\ProgramData\Morgana\temp\emu",
    [string]$Plan = "all",
    [string]$MicroPlan = "all",
    [switch]$DryRun,
    [switch]$SmokeImport,
    [switch]$Publish
)

$ErrorActionPreference = "Stop"
$ToolsDir = $PSScriptRoot
$ExcaliburDir = Split-Path $ToolsDir -Parent
$OutputDir = Join-Path $ExcaliburDir "ctid"
$CamelotDir = Split-Path (Split-Path $ExcaliburDir -Parent) -Parent
$LibraryRepository = "https://github.com/center-for-threat-informed-defense/adversary_emulation_library.git"
$EmuRepository = "https://github.com/mitre/emu.git"
$AllowedPattern = '^(morgana/excalibur/catalog\.json|morgana/excalibur/ctid/|morgana/excalibur/tools/(convert_ctid_emu\.py|ctid_plan_overrides\.json|test_convert_ctid_emu\.py|test_ctid_emu_import\.py|test_catalog_metadata\.py|update-ctid-emu-packs\.ps1))'

function Write-Step([string]$Message) { Write-Host ""; Write-Host "[STEP] $Message" -ForegroundColor Cyan }
function Write-OK([string]$Message) { Write-Host "[OK] $Message" -ForegroundColor Green }
function Write-Warn([string]$Message) { Write-Host "[WARN] $Message" -ForegroundColor Yellow }
function Stop-Pipeline([string]$Message) { Write-Host "[FAIL] $Message" -ForegroundColor Red; exit 1 }

function Update-Checkout([string]$Repository, [string]$Directory) {
    $Parent = Split-Path $Directory -Parent
    if (-not (Test-Path $Parent)) { New-Item -ItemType Directory -Path $Parent -Force | Out-Null }
    if (-not (Test-Path (Join-Path $Directory ".git"))) {
        & git clone $Repository $Directory
        if ($LASTEXITCODE -ne 0) { Stop-Pipeline "Clone failed: $Repository" }
    } else {
        & git -C $Directory fetch --prune
        if ($LASTEXITCODE -ne 0) { Stop-Pipeline "Fetch failed: $Directory" }
        & git -C $Directory pull --ff-only
        if ($LASTEXITCODE -ne 0) { Stop-Pipeline "Fast-forward update failed: $Directory" }
    }
}

Write-Host "=== CTID Threat-Informed Emulation Pack Pipeline ===" -ForegroundColor Magenta
Write-Host "Camelot: $CamelotDir"
Write-Host "Library: $LibraryDir"
Write-Host "Emu:     $EmuDir"
Write-Host "Plan:    $Plan"
Write-Host "Micro:   $MicroPlan"

if ($Publish) {
    Write-Step "Verify Camelot worktree is safe to publish"
    Push-Location $CamelotDir
    try {
        & git diff --cached --quiet
        if ($LASTEXITCODE -eq 1) { Stop-Pipeline "Refusing -Publish because changes are already staged." }
        if ($LASTEXITCODE -ne 0) { Stop-Pipeline "Could not inspect staged changes." }
        $Unrelated = @(
            & git status --porcelain |
                ForEach-Object { $_.Substring(3).Replace('\', '/') } |
                Where-Object { $_ -notmatch $AllowedPattern }
        )
        if ($Unrelated.Count -gt 0) {
            Stop-Pipeline "Refusing -Publish because unrelated changes exist: $($Unrelated -join ', ')"
        }
    } finally {
        Pop-Location
    }
    Write-OK "No pre-staged or unrelated changes"
}

Write-Step "Clone or update canonical CTID library"
Update-Checkout $LibraryRepository $LibraryDir
$LibrarySha = (& git -C $LibraryDir rev-parse HEAD).Trim()
Write-OK "CTID library SHA: $LibrarySha"

Write-Step "Clone or update MITRE Emu reference"
Update-Checkout $EmuRepository $EmuDir
$EmuSha = (& git -C $EmuDir rev-parse HEAD).Trim()
Write-OK "MITRE Emu SHA: $EmuSha"

Write-Step "Run fixture-only converter tests"
Push-Location $CamelotDir
try {
    & python -m unittest morgana.excalibur.tools.test_convert_ctid_emu -v
    if ($LASTEXITCODE -ne 0) { Stop-Pipeline "CTID converter tests failed." }
    & python -m py_compile `
        (Join-Path $ToolsDir "convert_ctid_emu.py") `
        (Join-Path $ToolsDir "test_convert_ctid_emu.py") `
        (Join-Path $ToolsDir "test_ctid_emu_import.py")
    if ($LASTEXITCODE -ne 0) { Stop-Pipeline "CTID Python compilation failed." }
} finally {
    Pop-Location
}
Write-OK "Unit and static checks passed"

Write-Step "Convert selected full and micro plans"
$Arguments = @(
    (Join-Path $ToolsDir "convert_ctid_emu.py"),
    "--library-dir", $LibraryDir,
    "--emu-dir", $EmuDir,
    "--out-dir", $OutputDir,
    "--plan", $Plan,
    "--micro-plan", $MicroPlan,
    "--plan-type", "both"
)
if ($DryRun) { $Arguments += "--dry-run" }
& python @Arguments
if ($LASTEXITCODE -ne 0) { Stop-Pipeline "CTID conversion failed." }
if ($DryRun) { Write-OK "Dry run completed without replacing output or catalog."; exit 0 }

Write-Step "Validate generated CTID package flows"
& python (Join-Path $ToolsDir "test_ctid_emu_import.py") --all --validate-only
if ($LASTEXITCODE -ne 0) { Stop-Pipeline "CTID package validation failed." }

Write-Step "Validate complete catalog decision metadata"
& python (Join-Path $ToolsDir "test_catalog_metadata.py")
if ($LASTEXITCODE -ne 0) { Stop-Pipeline "Catalog metadata validation failed." }
Write-OK "Generated packages and catalog metadata passed validation"

if ($SmokeImport) {
    Write-Step "Import CTID packages into loopback Morgana without execution"
    & python (Join-Path $ToolsDir "test_ctid_emu_import.py") --all
    if ($LASTEXITCODE -ne 0) { Stop-Pipeline "CTID loopback import failed." }
    Write-OK "Package import completed; no Chain was executed"
} else {
    Write-Warn "Morgana import skipped. Use -SmokeImport explicitly to import without execution."
}

if ($Publish) {
    Write-Step "Publish only reviewed CTID paths"
    Push-Location $CamelotDir
    try {
        & git add -- `
            morgana/excalibur/catalog.json `
            morgana/excalibur/ctid `
            morgana/excalibur/tools/convert_ctid_emu.py `
            morgana/excalibur/tools/ctid_plan_overrides.json `
            morgana/excalibur/tools/test_convert_ctid_emu.py `
            morgana/excalibur/tools/test_ctid_emu_import.py `
            morgana/excalibur/tools/test_catalog_metadata.py `
            morgana/excalibur/tools/update-ctid-emu-packs.ps1
        if ($LASTEXITCODE -ne 0) { Stop-Pipeline "Could not stage CTID publication files." }
        $Staged = @(& git diff --cached --name-only)
        $Unexpected = @($Staged | Where-Object { $_ -notmatch $AllowedPattern })
        if ($Unexpected.Count -gt 0) { Stop-Pipeline "Unexpected staged paths: $($Unexpected -join ', ')" }
        if ($Staged.Count -eq 0) {
            Write-Warn "No CTID changes to publish."
        } else {
            & git commit -m "feat: publish CTID threat-informed emulation pilots"
            if ($LASTEXITCODE -ne 0) { Stop-Pipeline "Camelot commit failed." }
            & git push
            if ($LASTEXITCODE -ne 0) { Stop-Pipeline "Camelot push failed." }
            Write-OK "CTID packages published"
        }
    } finally {
        Pop-Location
    }
} else {
    Write-Warn "Publish skipped. Use -Publish only after explicit approval."
}

Write-Host ""
Write-Host "=== CTID pipeline complete ===" -ForegroundColor Magenta
Write-Host "CTID SHA: $LibrarySha"
Write-Host "Emu SHA: $EmuSha"
Write-Host "Report: $(Join-Path $OutputDir 'conversion-report.json')"
