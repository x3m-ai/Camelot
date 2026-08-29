[CmdletBinding()]
param(
    [string]$SourceDir = "C:\ProgramData\Morgana\temp\ics-scada-fuzzer",
    [string]$BuildRoot = "C:\ProgramData\Morgana\temp\ics-fuzzer-build",
    [string]$BuildDistro = "MorganaICSBuild",
    [switch]$DryRun,
    [switch]$SmokeImport,
    [switch]$Publish
)

$ErrorActionPreference = "Stop"
$ToolsDir = $PSScriptRoot
$ExcaliburDir = Split-Path $ToolsDir -Parent
$OutputDir = Join-Path $ExcaliburDir "ot\fuzzing\ics-scada-fuzzer"
$CamelotDir = Split-Path (Split-Path $ExcaliburDir -Parent) -Parent
$Repository = "https://github.com/ridpath/ics-scada-fuzzer.git"
$AllowedPattern = '^(morgana/excalibur/catalog\.json|morgana/excalibur/ot/fuzzing/ics-scada-fuzzer/|morgana/excalibur/tools/(convert_ics_scada_fuzzer\.py|test_convert_ics_scada_fuzzer\.py|test_ics_scada_fuzzer_import\.py|update-ics-scada-fuzzer\.ps1|ics_scada_fuzzer_mapping\.json))'
$BuildCommand = "gcc -O2 -pthread -static -no-pie -Wl,--build-id=none -s -o ics-fuzzer-linux-amd64 ics_fuzzer.c -lpcap -lcrypto -lz"
function Step([string]$Message) { Write-Host ""; Write-Host "[STEP] $Message" -ForegroundColor Cyan }
function Fail([string]$Message) { Write-Host "[FAIL] $Message" -ForegroundColor Red; exit 1 }

Write-Host "=== MORGANA ICS-SCADA-FUZZER BUILD ===" -ForegroundColor Magenta
Step "Clone or update pinned upstream"
if (-not (Test-Path (Split-Path $SourceDir -Parent))) { New-Item -ItemType Directory -Path (Split-Path $SourceDir -Parent) -Force | Out-Null }
if (-not (Test-Path (Join-Path $SourceDir ".git"))) { & git clone $Repository $SourceDir } else { & git -C $SourceDir fetch --prune; if ($LASTEXITCODE -eq 0) { & git -C $SourceDir pull --ff-only } }
if ($LASTEXITCODE -ne 0) { Fail "Source update failed" }
$SourceSha = (& git -C $SourceDir rev-parse HEAD).Trim()

Step "Prepare reusable Alpine WSL1 build environment"
$Distros = @(& wsl.exe --list --quiet 2>$null | ForEach-Object { $_.Trim([char]0).Trim() })
if ($Distros -notcontains $BuildDistro) {
    New-Item -ItemType Directory -Path $BuildRoot -Force | Out-Null
    $Index = Invoke-WebRequest -UseBasicParsing "https://dl-cdn.alpinelinux.org/alpine/latest-stable/releases/x86_64/"
    $ArchiveName = [regex]::Matches($Index.Content, 'alpine-minirootfs-[0-9.]+-x86_64\.tar\.gz') | ForEach-Object { $_.Value } | Sort-Object -Unique | Select-Object -Last 1
    if (-not $ArchiveName) { Fail "Could not discover Alpine minirootfs" }
    $Archive = Join-Path $BuildRoot $ArchiveName
    if (-not (Test-Path $Archive)) { Invoke-WebRequest -UseBasicParsing "https://dl-cdn.alpinelinux.org/alpine/latest-stable/releases/x86_64/$ArchiveName" -OutFile $Archive }
    $RootFs = Join-Path $BuildRoot "rootfs-wsl1"
    if (Test-Path $RootFs) { Remove-Item $RootFs -Recurse -Force }
    New-Item -ItemType Directory -Path $RootFs -Force | Out-Null
    & wsl.exe --import $BuildDistro $RootFs $Archive --version 1
    if ($LASTEXITCODE -ne 0) { Fail "WSL builder import failed" }
}
& wsl.exe -d $BuildDistro -- sh -lc "printf 'nameserver 1.1.1.1\nnameserver 8.8.8.8\n' > /etc/resolv.conf; apk update >/dev/null; apk add --no-cache build-base libpcap-dev openssl-dev openssl-libs-static zlib-dev zlib-static linux-headers >/dev/null"
if ($LASTEXITCODE -ne 0) { Fail "Build dependency installation failed" }

Step "Compile and verify static Linux amd64 asset"
$LinuxSource = "/mnt/c/ProgramData/Morgana/temp/ics-scada-fuzzer"
$LinuxOutput = "/mnt/c/ProgramData/Morgana/temp/ics-fuzzer-build/output"
& wsl.exe -d $BuildDistro -- sh -lc "set -e; mkdir -p '$LinuxOutput'; cd '$LinuxSource'; $BuildCommand; mv ics-fuzzer-linux-amd64 '$LinuxOutput/ics-fuzzer-linux-amd64'; test \`$(readelf -l '$LinuxOutput/ics-fuzzer-linux-amd64' 2>/dev/null | grep -c INTERP) -eq 0; test \`$(readelf -d '$LinuxOutput/ics-fuzzer-linux-amd64' 2>/dev/null | grep -c NEEDED) -eq 0"
if ($LASTEXITCODE -ne 0) { Fail "Static build or dependency verification failed" }
$Binary = Join-Path $BuildRoot "output\ics-fuzzer-linux-amd64"
$CompilerVersion = (& wsl.exe -d $BuildDistro -- gcc --version | Select-Object -First 1).Trim()

Step "Compile converter and run compact tests"
Push-Location $CamelotDir
try {
    & python -m py_compile (Join-Path $ToolsDir "convert_ics_scada_fuzzer.py") (Join-Path $ToolsDir "test_convert_ics_scada_fuzzer.py") (Join-Path $ToolsDir "test_ics_scada_fuzzer_import.py")
    if ($LASTEXITCODE -ne 0) { Fail "Python compilation failed" }
    & python -m unittest morgana.excalibur.tools.test_convert_ics_scada_fuzzer -v
    if ($LASTEXITCODE -ne 0) { Fail "Converter tests failed" }
} finally { Pop-Location }

Step "Generate all five protocol packages and 120 profiles"
$Arguments = @((Join-Path $ToolsDir "convert_ics_scada_fuzzer.py"), "--source-dir", $SourceDir, "--binary", $Binary, "--out-dir", $OutputDir, "--compiler", "gcc", "--compiler-version", $CompilerVersion, "--build-command", $BuildCommand)
if ($DryRun) { $Arguments += "--dry-run" }
& python @Arguments
if ($LASTEXITCODE -ne 0) { Fail "Conversion failed" }
if ($DryRun) { Write-Host "[OK] Dry run complete" -ForegroundColor Green; exit 0 }

Step "Validate every profile, asset, package, and catalog entry"
& python (Join-Path $ToolsDir "test_ics_scada_fuzzer_import.py") --all --validate-only
if ($LASTEXITCODE -ne 0) { Fail "Static validation failed" }
& python (Join-Path $ToolsDir "test_catalog_metadata.py")
if ($LASTEXITCODE -ne 0) { Fail "Catalog validation failed" }
Write-Host "[OK] Full static validation passed" -ForegroundColor Green

if ($SmokeImport) {
    Step "Smoke-import Modbus package without execution"
    & python (Join-Path $ToolsDir "test_ics_scada_fuzzer_import.py") --protocol modbus
    if ($LASTEXITCODE -ne 0) { Fail "Smoke import failed" }
}

if ($Publish) {
    Step "Publish reviewed ICS fuzzing paths"
    Push-Location $CamelotDir
    try {
        & git diff --cached --quiet
        if ($LASTEXITCODE -eq 1) { Fail "Changes are already staged" }
        $Unrelated = @(& git status --porcelain | ForEach-Object { $_.Substring(3).Replace('\','/') } | Where-Object { $_ -notmatch $AllowedPattern })
        if ($Unrelated.Count) { Fail "Unrelated changes exist: $($Unrelated -join ', ')" }
        & git add -- morgana/excalibur/catalog.json morgana/excalibur/ot/fuzzing/ics-scada-fuzzer `
            morgana/excalibur/tools/convert_ics_scada_fuzzer.py morgana/excalibur/tools/test_convert_ics_scada_fuzzer.py `
            morgana/excalibur/tools/test_ics_scada_fuzzer_import.py morgana/excalibur/tools/update-ics-scada-fuzzer.ps1 `
            morgana/excalibur/tools/ics_scada_fuzzer_mapping.json
        $Unexpected = @(& git diff --cached --name-only | Where-Object { $_ -notmatch $AllowedPattern })
        if ($Unexpected.Count) { Fail "Unexpected staged paths: $($Unexpected -join ', ')" }
        & git commit -m "feat: publish ICS-SCADA-Fuzzer packs"
        if ($LASTEXITCODE -ne 0) { Fail "Commit failed" }
        & git push
        if ($LASTEXITCODE -ne 0) { Fail "Push failed" }
    } finally { Pop-Location }
}

$Report = Get-Content (Join-Path $OutputDir "conversion-report.json") -Raw -Encoding UTF8 | ConvertFrom-Json
Write-Host ""
Write-Host "Source commit: $SourceSha"
Write-Host "Generated:     $($Report.generated_profiles)"
Write-Host "Stateful:      $($Report.stateful_profiles)"
Write-Host "Stateless:     $($Report.stateless_profiles)"
Write-Host "Replay:        $($Report.replay_profiles)"
Write-Host "Scripts:       $($Report.total_scripts)"
Write-Host "Packages:      $($Report.packages)"
Write-Host "Validation:    $($Report.validation)"
Write-Host "Runtime tests: representative only / exhaustive fuzzing left for operator labs"