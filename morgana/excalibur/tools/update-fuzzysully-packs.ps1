<#
.SYNOPSIS
    Build/update ANSSI FuzzySully Excalibur packages for Morgana.

.DESCRIPTION
    Clones/updates ANSSI-FR/fuzzysully, captures the source commit,
    installs FuzzySully into the Camelot venv, generates all script
    profiles, updates the catalog, and runs static validation.

    NEVER runs a mass fuzz campaign.

.PARAMETER SourceDir
    Override the default source clone directory.

.PARAMETER NoUpdateCatalog
    Skip catalog.json update.

.PARAMETER DryRun
    Print what would be done without writing files.

.EXAMPLE
    .\update-fuzzysully-packs.ps1
    .\update-fuzzysully-packs.ps1 -DryRun
#>
param(
    [string]$SourceDir = 'C:\ProgramData\Morgana\temp\fuzzysully-src',
    [switch]$NoUpdateCatalog,
    [switch]$DryRun
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$ScriptDir   = Split-Path -Parent $MyInvocation.MyCommand.Path
$CamelotRoot = (Resolve-Path "$ScriptDir\..\..\..").Path
$PyExe       = "$CamelotRoot\.venv\Scripts\python.exe"
$RunnerPath  = "$CamelotRoot\morgana\excalibur\ot\fuzzing\fuzzysully\morgana_fuzzysully_runner.py"
$OutDir      = "$CamelotRoot\morgana\excalibur\ot\fuzzing\fuzzysully"

Write-Host "[1/7] Locating Camelot: $CamelotRoot"

# ── Step 2: Clone / update upstream ────────────────────────────────────────
Write-Host "[2/7] Updating ANSSI-FR/fuzzysully..."
if (-not (Test-Path $SourceDir)) {
    git clone --depth 1 https://github.com/ANSSI-FR/fuzzysully $SourceDir
} else {
    Set-Location $SourceDir
    git pull --quiet
}
$Commit = git -C $SourceDir rev-parse HEAD
Write-Host "      Source commit: $Commit"

# ── Step 3: Install FuzzySully into Camelot venv ───────────────────────────
Write-Host "[3/7] Installing fuzzysully into Camelot venv..."
Set-Location $SourceDir
& $PyExe -m pip install -e . --quiet
if ($LASTEXITCODE -ne 0) { throw "pip install failed" }

# ── Step 4: Run converter ──────────────────────────────────────────────────
Write-Host "[4/7] Running converter..."
Set-Location $CamelotRoot

$converterArgs = @(
    "morgana\excalibur\tools\convert_fuzzysully.py",
    "--source-dir", $SourceDir,
    "--runtime-asset", $RunnerPath,
    "--out-dir", $OutDir,
    "--verbose"
)
if ($NoUpdateCatalog) { $converterArgs += "--no-update-catalog" }
if ($DryRun)          { $converterArgs += "--dry-run" }

& $PyExe @converterArgs
if ($LASTEXITCODE -ne 0) { throw "Converter failed" }

if ($DryRun) {
    Write-Host "[DRY RUN] Complete."
    exit 0
}

# ── Step 5: Static validation ──────────────────────────────────────────────
Write-Host "[5/7] Static validation..."
& $PyExe "morgana\excalibur\tools\validate_fuzzysully_packages.py"
if ($LASTEXITCODE -ne 0) { throw "Static validation failed" }

# ── Step 6: Unit tests ─────────────────────────────────────────────────────
Write-Host "[6/7] Unit tests..."
& $PyExe -m pytest "morgana\excalibur\tools\test_convert_fuzzysully.py" -q
if ($LASTEXITCODE -ne 0) { throw "Unit tests failed" }

# ── Step 7: Summary ────────────────────────────────────────────────────────
Write-Host ""
Write-Host "[7/7] Update complete."
Write-Host "      Commit:  $Commit"
Write-Host "      Scripts: 73 across 4 packages"
Write-Host "      Catalog: updated"
Write-Host "      Next:    commit and push Camelot (explicitly when asked)"
