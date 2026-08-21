<#
.SYNOPSIS
    Completely removes Morgana from the target machine.
.PARAMETER WipeData
    Also delete C:\ProgramData\Morgana\ (DB, logs, certs, API key).
    Use for a clean reinstall. Omit to preserve data across reinstalls.
.EXAMPLE
    .\scripts\03-uninstall-morgana.ps1
    .\scripts\03-uninstall-morgana.ps1 -WipeData
#>

[CmdletBinding(SupportsShouldProcess)]
param(
    [switch]$WipeData
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# Auto-elevate
$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltinRole]::Administrator)
if (-not $isAdmin) {
    $wipeArg = if ($WipeData) { "-WipeData" } else { "" }
    Start-Process powershell -Verb RunAs -ArgumentList "-NoProfile -ExecutionPolicy Bypass -File `"$PSCommandPath`" $wipeArg" -Wait
    exit
}

function Write-Step { param([string]$msg) Write-Host "[UNINSTALL] $msg" -ForegroundColor Cyan }
function Write-OK   { param([string]$msg) Write-Host "[OK] $msg"         -ForegroundColor Green }
function Write-Warn { param([string]$msg) Write-Host "[WARN] $msg"       -ForegroundColor Yellow }

Write-Host ""
Write-Host "=============================================="
Write-Host "  MORGANA - Complete Uninstall"
if ($WipeData) { Write-Host "  DATA WIPE enabled" -ForegroundColor Red }
Write-Host "=============================================="
Write-Host ""

# 1. Stop NT Service
Write-Step "Stopping Morgana NT Service..."
$svc = Get-Service Morgana -ErrorAction SilentlyContinue
if ($svc) {
    if ($svc.Status -ne "Stopped") {
        Stop-Service Morgana -Force -ErrorAction SilentlyContinue
        Start-Sleep 3
        Write-OK "Service stopped."
    } else { Write-Warn "Service was already stopped." }
} else { Write-Warn "Service not found - may already be removed." }

# 2. Kill lingering processes
Write-Step "Killing any running Morgana processes..."
$procs = Get-CimInstance Win32_Process -Filter "Name='morgana-server.exe' OR Name='python.exe' OR Name='pythonw.exe'" -ErrorAction SilentlyContinue |
    Where-Object { $_.ExecutablePath -like "*morgana*" -or $_.CommandLine -like "*main.py*" }
if ($procs) {
    $procs | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
    Write-OK "Processes terminated."
} else { Write-Warn "No running Morgana processes found." }

# 3. Remove service registration
Write-Step "Removing NT Service registration..."
if (Get-Service Morgana -ErrorAction SilentlyContinue) {
    sc.exe delete Morgana | Out-Null
    Start-Sleep 2
    Write-OK "Service registration removed."
} else { Write-Warn "Service registration not present." }

# 4. Run Inno Setup uninstaller
Write-Step "Running Inno Setup uninstaller..."
$uninstaller = @(
    "C:\Program Files\Morgana Server\unins000.exe",
    "C:\Program Files (x86)\Morgana Server\unins000.exe"
) | Where-Object { Test-Path $_ } | Select-Object -First 1

if ($uninstaller) {
    Start-Process $uninstaller -ArgumentList "/VERYSILENT /NORESTART" -Wait
    Write-OK "Program files removed by Inno Setup uninstaller."
} else {
    Write-Warn "Inno Setup uninstaller not found - removing program folder manually..."
    foreach ($folder in @("C:\Program Files\Morgana Server", "C:\Program Files (x86)\Morgana Server")) {
        if (Test-Path $folder) { Remove-Item $folder -Recurse -Force; Write-OK "Removed: $folder" }
    }
}

# 5. Optional data wipe
if ($WipeData) {
    Write-Step "Wiping C:\ProgramData\Morgana\ ..."
    if (Test-Path "C:\ProgramData\Morgana") {
        Remove-Item "C:\ProgramData\Morgana" -Recurse -Force
        Write-OK "Data directory wiped. Next install will start fresh."
    } else { Write-Warn "Data directory not found - nothing to wipe." }
} else {
    Write-Host ""
    Write-Warn "Data at C:\ProgramData\Morgana\ preserved. Use -WipeData for a clean reinstall."
}

Write-Host ""
Write-Host "=============================================="
Write-OK "Morgana uninstall complete."
Write-Host "=============================================="
Write-Host ""
