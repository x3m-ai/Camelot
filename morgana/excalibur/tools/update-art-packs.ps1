[CmdletBinding()]
param(
    [string]$AtomicsDir = "C:\ProgramData\Morgana\temp\atomic-red-team\atomics",
    [switch]$SkipMorganaCommit,
    [switch]$DryRun
)

$ErrorActionPreference = "Continue"

$CAMELOT_DIR  = Split-Path (Split-Path (Split-Path $PSScriptRoot -Parent) -Parent) -Parent
$MORGANA_DIR  = Join-Path (Split-Path $CAMELOT_DIR -Parent) "Morgana"
$ATOMICS_REPO = Split-Path $AtomicsDir -Parent
$TOOLS_DIR    = $PSScriptRoot
$ART_DIR      = Join-Path (Split-Path $TOOLS_DIR -Parent) "art"
$TODAY        = Get-Date -Format "yyyy-MM-dd"

function Write-Step([string]$msg) { Write-Host "" ; Write-Host "[STEP] $msg" -ForegroundColor Cyan }
function Write-OK([string]$msg)   { Write-Host "  [OK] $msg" -ForegroundColor Green }
function Write-Fail([string]$msg) { Write-Host "[FAIL] $msg" -ForegroundColor Red ; exit 1 }

Write-Host ""
Write-Host "=== ART Pack Update Pipeline ===" -ForegroundColor Magenta
Write-Host "  Camelot : $CAMELOT_DIR"
Write-Host "  Morgana : $MORGANA_DIR"
Write-Host "  Atomics : $AtomicsDir"
if ($DryRun) { Write-Host "  Mode    : DRY RUN" -ForegroundColor Yellow }

# Step 1 - Clone o aggiorna atomic-red-team
Write-Step "Aggiorna atomic-red-team"
if (-not (Test-Path $AtomicsDir)) {
    Write-Host "  Repo non trovato. Clono in: $ATOMICS_REPO"
    if (-not (Test-Path (Split-Path $ATOMICS_REPO -Parent))) {
        New-Item -ItemType Directory -Path (Split-Path $ATOMICS_REPO -Parent) -Force | Out-Null
    }
    & git clone --depth=1 https://github.com/redcanaryco/atomic-red-team.git $ATOMICS_REPO
    if ($LASTEXITCODE -ne 0) { Write-Fail "git clone fallito (exit $LASTEXITCODE)" }
    Write-OK "Clone completato"
} else {
    Write-Host "  Repo trovato. git pull..."
    Push-Location $ATOMICS_REPO
    & git pull origin master
    $pullExit = $LASTEXITCODE
    Pop-Location
    if ($pullExit -ne 0) { Write-Host "  [WARN] git pull non completato - continuo con dati esistenti" -ForegroundColor Yellow }
    else { Write-OK "Repo aggiornato" }
}

# Step 2 - Verifica PyYAML
Write-Step "Verifica dipendenze Python"
$pyCheck = python -c "import yaml; print('ok')" 2>&1
if ("$pyCheck" -ne "ok") {
    Write-Host "  PyYAML non trovato. Installo..."
    pip install pyyaml --quiet
    if ($LASTEXITCODE -ne 0) { Write-Fail "pip install pyyaml fallito" }
}
Write-OK "PyYAML disponibile"

# Step 3 - Converter
Write-Step "Esegui convert_atomics.py"
Push-Location $TOOLS_DIR
if ($DryRun) {
    python convert_atomics.py --atomics-dir $AtomicsDir --dry-run
} else {
    python convert_atomics.py --atomics-dir $AtomicsDir
}
$converterExit = $LASTEXITCODE
Pop-Location
if ($converterExit -ne 0) { Write-Fail "Converter fallito (exit $converterExit)" }
Write-OK "Pack generati in: $ART_DIR"

if ($DryRun) {
    Write-Host ""
    Write-Host "[DRY RUN] Nessun commit eseguito." -ForegroundColor Yellow
    exit 0
}

# Step 4 - Commit e push Camelot
Write-Step "Commit e push Camelot"
Push-Location $CAMELOT_DIR

& git add "morgana/excalibur/art/" "morgana/excalibur/catalog.json" "morgana/excalibur/tools/convert_atomics.py" "morgana/excalibur/tools/test_art_import.py" "morgana/excalibur/tools/update-art-packs.ps1" "morgana/excalibur/art/README.md"

$camelotStatus = & git status --porcelain
if (-not $camelotStatus) {
    Write-Host "  Nessuna modifica da committare in Camelot." -ForegroundColor Yellow
} else {
    $artCount = (Get-ChildItem "$ART_DIR\art-*.json" -ErrorAction SilentlyContinue).Count
    $msg = "feat: Red Canary ART packs update - $artCount packs - $TODAY"
    & git commit -m $msg
    if ($LASTEXITCODE -ne 0) { Write-Fail "git commit Camelot fallito" }
    & git push
    if ($LASTEXITCODE -ne 0) { Write-Fail "git push Camelot fallito" }
    Write-OK "Camelot pushato - CDN live"
}
Pop-Location

# Step 5 - Commit e push Morgana
if (-not $SkipMorganaCommit) {
    Write-Step "Commit e push Morgana"
    if (-not (Test-Path $MORGANA_DIR)) {
        Write-Host "  [SKIP] Cartella Morgana non trovata: $MORGANA_DIR" -ForegroundColor Yellow
    } else {
        Push-Location $MORGANA_DIR
        $morganaStatus = & git status --porcelain "server/routers/scripts.py" "ui/app.js" "ui/modules/excalibur.js" "commit_history/"
        if (-not $morganaStatus) {
            Write-Host "  Nessuna modifica da committare in Morgana." -ForegroundColor Yellow
        } else {
            & git add "server/routers/scripts.py" "ui/app.js" "ui/modules/excalibur.js" "commit_history/20260811_art_integration.md"
            & git commit -m "feat: ART pack support - add ART prefix, catalog category"
            if ($LASTEXITCODE -ne 0) { Write-Fail "git commit Morgana fallito" }
            & git push
            if ($LASTEXITCODE -ne 0) { Write-Fail "git push Morgana fallito" }
            Write-OK "Morgana pushato"
        }
        Pop-Location
    }
} else {
    Write-Host "  [SKIP] Morgana commit saltato (-SkipMorganaCommit)" -ForegroundColor DarkGray
}

# Riepilogo
Write-Host ""
Write-Host "=== Pipeline completata ===" -ForegroundColor Magenta
$finalCount = (Get-ChildItem "$ART_DIR\art-*.json" -ErrorAction SilentlyContinue).Count
Write-Host "  Pack ART pubblicati : $finalCount"
Write-Host "  CDN base URL : https://raw.githubusercontent.com/x3m-ai/Camelot/main/morgana/excalibur/art/"
Write-Host ""
Write-Host "  Morgana UI -> Scripts -> Refresh catalog -> Atomic Red Team" -ForegroundColor Green
Write-Host ""