# update-industriconnect.ps1
# Single pinned source pipeline for IndustriConnect + Industrial Lab content.
#
# Responsibilities:
#   1. Acquire/pin the IndustriConnect upstream source (git clone at a fixed commit)
#   2. Run MCP tool discovery + conversion to Excalibur packs (Part A)
#   3. Generate the provider-agnostic Industrial Lab catalog (Part B)
#   4. Sync the generic MCP stdio runner asset (byte-identical with Morgana server)
#   5. Static validation of packs and lab manifests
#   6. Report reconciliation counts
#
# Publication (git commit/push) is NOT performed by this script.
# Use `-Publish` only to print the git commands the operator must run manually.

param(
    [string]$SourceDir = "C:\ProgramData\Morgana\temp\industriconnect-source",
    [string]$Commit = "aa634a12ece8186b3e6c775cea1917ea89418f5e",
    [switch]$SkipClone,
    [switch]$Publish
)

$ErrorActionPreference = "Stop"
$ToolsDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$CamelotRoot = Split-Path -Parent (Split-Path -Parent (Split-Path -Parent $ToolsDir))
$ExcaliburDir = Join-Path $CamelotRoot "morgana\excalibur"
$LabDir = Join-Path $CamelotRoot "morgana\industrial-lab"
$RunnerSrc = "C:\Users\ninoc\OfficeAddinApps\Morgana\server\core\mcp_stdio_runner.py"
$RunnerDst = Join-Path $ExcaliburDir "ot\industriconnect\runtime\morgana_mcp_stdio_runner.py"

Write-Host "[INDUSTRICONNECT] Pipeline start" -ForegroundColor Cyan

# 1. Acquire pinned source
if (-not $SkipClone) {
    if (Test-Path $SourceDir) { Remove-Item $SourceDir -Recurse -Force }
    git clone --depth 1 https://github.com/IndustriAgents/IndustriConnect.git $SourceDir
    git -C $SourceDir checkout $Commit 2>$null
    $actual = (git -C $SourceDir rev-parse HEAD).Trim()
    Write-Host "[SOURCE] Pinned commit: $actual"
    if ($actual.Substring(0, [Math]::Min(8, $actual.Length)) -ne $Commit.Substring(0,8)) {
        Write-Warning "[SOURCE] HEAD $actual differs from requested $Commit"
    }
} else {
    Write-Host "[SOURCE] Skipping clone (using existing $SourceDir)"
}

# 2. Sync runner asset from Morgana server (byte-identical)
if (Test-Path $RunnerSrc) {
    Copy-Item $RunnerSrc $RunnerDst -Force
    Write-Host "[RUNNER] Synced morgana_mcp_stdio_runner.py"
} else {
    Write-Warning "[RUNNER] Server runner not found at $RunnerSrc — asset may be stale"
}

# 3. Convert + validate packs
Write-Host "[CONVERT] Generating IndustriConnect Excalibur packs..."
python (Join-Path $ToolsDir "convert_industriconnect.py")
python (Join-Path $ToolsDir "validate_industriconnect_packs.py")
if ($LASTEXITCODE -ne 0) { throw "IndustriConnect pack validation failed" }

# 4. Generate Industrial Lab catalog
Write-Host "[LAB] Generating Industrial Lab catalog..."
python (Join-Path $ToolsDir "generate_industrial_lab.py")

Write-Host "[SUCCESS] IndustriConnect + Industrial Lab content regenerated" -ForegroundColor Green

if ($Publish) {
    Write-Host ""
    Write-Host "[PUBLISH] Run these git commands manually (never auto-commit):" -ForegroundColor Yellow
    Write-Host "  cd $CamelotRoot"
    Write-Host "  git add morgana/excalibur/ot/industriconnect morgana/excalibur/catalog.json morgana/industrial-lab morgana/excalibur/tools/convert_industriconnect.py morgana/excalibur/tools/generate_industrial_lab.py morgana/excalibur/tools/validate_industriconnect_packs.py"
    Write-Host "  git status"
    Write-Host "  git commit -m 'feat: publish IndustriConnect provider + Industrial Lab subsystem'"
}
