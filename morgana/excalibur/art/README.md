# ART Packs — Red Canary Atomic Red Team Integration

> **Source:** [redcanaryco/atomic-red-team](https://github.com/redcanaryco/atomic-red-team)  
> **Generated:** 2026-08-11 | **Scripts:** 1603 | **Chains:** 1616 | **Tactics:** 13

---

## Cos'è questo

Questa cartella contiene 13 Excalibur Pack JSON convertiti automaticamente dagli script YAML di Red Canary Atomic Red Team. Ogni pack corrisponde a un MITRE ATT&CK tactic e può essere installato in Morgana via **Scripts → Refresh catalog → Install** esattamente come un pack Excalibur normale.

**Nessuna modifica al server Morgana è richiesta.** Il converter produce JSON compatibile con il meccanismo `import-package` già esistente.

---

## Struttura della cartella

```
art/
  README.md                         questo file
  art-initial_access-v1.json        TA0001  26 scripts
  art-exec-v1.json                  TA0002  139 scripts
  art-persist-v1.json               TA0003  197 scripts
  art-privesc-v1.json               TA0004  91 scripts
  art-evasion-v1.json               TA0005  400 scripts
  art-credaccess-v1.json            TA0006  206 scripts
  art-discovery-v1.json             TA0007  286 scripts
  art-lateral-v1.json               TA0008  19 scripts
  art-collection-v1.json            TA0009  54 scripts
  art-exfil-v1.json                 TA0010  27 scripts
  art-c2-v1.json                    TA0011  90 scripts
  art-impact-v1.json                TA0040  66 scripts
  art-recon-v1.json                 TA0043  2 scripts
```

**Naming convention pack:** `art-{tactic_slug}-v1.json`  
**Naming convention script:** `ART - {TCode} - {TestName}`  
**Naming convention tag key:** `art_{tactic_slug}_{tcode_digits}_{arg_name}` (es. `art_exec_1059_001_input_file`)

---

## Come funziona il converter

**File:** `../tools/convert_atomics.py`

Il converter legge i file `T*.yaml` dalla cartella `atomics/` di Red Canary e produce pack JSON Excalibur validi.

### Mapping dei campi

| Campo Red Canary YAML | Campo Excalibur Pack |
|---|---|
| `attack_technique` | `tcode` |
| `atomic_tests[].name` | `name` (prefissato `ART - {TCode} - `) |
| `atomic_tests[].executor.name` | `executor` (vedi tabella sotto) |
| `atomic_tests[].executor.command` | `command` |
| `atomic_tests[].executor.cleanup_command` | `cleanup_command` |
| `atomic_tests[].input_arguments` | `tag_categories[].tags[]` + `required_tags[]` |
| `atomic_tests[].supported_platforms` | `platform` |
| `atomic_tests[].auto_generated_guid` | `atomic_guid` (nel campo `script`) |

### Mapping executor

| Red Canary | Morgana |
|---|---|
| `powershell` | `powershell` |
| `command_prompt` | `cmd` |
| `sh` | `bash` |
| `bash` | `bash` |
| `python` | `python` |
| `manual` | `manual` (skippato di default) |

### Tag key naming

Red Canary usa `input_arguments` con chiavi piatte (`input_file`, `output_path`). Morgana richiede chiavi univoche in tutto il DB perché `apply_tag_substitution()` risolve per chiave.

Formula: `art_{tactic_slug}_{tcode_digits}_{arg_name}`

```
T1059.001  arg: script_path
→ art_exec_1059_001_script_path

T1003.001  arg: output_file  
→ art_credaccess_1003_001_output_file
```

I placeholder nel comando vengono rinominati di conseguenza:
```
#{script_path}  →  #{art_exec_1059_001_script_path}
```

### Chains generate

Per ogni script viene generata automaticamente una chain a 1 step con lo stesso nome. Alla fine di ogni pack viene aggiunta una "Full Tactic Chain" che esegue tutti gli script del tactic in sequenza.

---

## Pipeline di aggiornamento automatico

**File:** `../tools/update-art-packs.ps1`

Script PowerShell che esegue l'intera pipeline in un comando solo:
aggiorna Red Canary → rigenera i pack → commit + push Camelot → commit + push Morgana.

### Prima esecuzione (setup completo)

```powershell
cd Camelot\morgana\excalibur\tools
.\update-art-packs.ps1
```

Esegue in sequenza:
1. Clona `atomic-red-team` in `C:\ProgramData\Morgana\temp\` (percorso escluso da Defender)
2. Verifica PyYAML, lo installa se mancante
3. Esegue `convert_atomics.py` → rigenera tutti i pack JSON in `art/`
4. Commit + push Camelot → CDN live immediatamente
5. Commit + push Morgana → server e UI aggiornati

### Aggiornamenti periodici (Morgana già pushato)

```powershell
.\update-art-packs.ps1 -SkipMorganaCommit
```

Solo Camelot viene toccato. Usare ogni volta che Red Canary rilascia nuovi atomic tests.

### Dry run (solo preview)

```powershell
.\update-art-packs.ps1 -DryRun
```

Mostra cosa verrebbe generato senza scrivere file né eseguire commit.

### Parametri

| Parametro | Default | Descrizione |
|---|---|---|
| `-AtomicsDir` | `C:\ProgramData\Morgana\temp\atomic-red-team\atomics` | Path alla cartella atomics/ di Red Canary |
| `-SkipMorganaCommit` | false | Skippa commit+push su Morgana |
| `-DryRun` | false | Nessun file scritto, nessun commit |

---

## Come rigenerare i pack manualmente

### Prerequisiti

```powershell
pip install pyyaml

# Clone del repo Red Canary nel percorso Defender-excluded
git clone --depth=1 https://github.com/redcanaryco/atomic-red-team.git C:\ProgramData\Morgana\temp\atomic-red-team
```

> **IMPORTANTE:** Usare `C:\ProgramData\Morgana\temp\` — Windows Defender blocca i file di attacco in `C:\Windows\Temp\` e altri percorsi standard.

### Comandi converter

```powershell
cd Camelot\morgana\excalibur\tools

# Rigenerazione completa (tutti i 13 tactics)
python convert_atomics.py --atomics-dir C:\ProgramData\Morgana\temp\atomic-red-team\atomics

# Solo un tactic
python convert_atomics.py --atomics-dir ... --tactic TA0002

# Solo Windows
python convert_atomics.py --atomics-dir ... --platform windows

# Dry run (nessun file scritto)
python convert_atomics.py --atomics-dir ... --dry-run

# Senza aggiornare catalog.json
python convert_atomics.py --atomics-dir ... --no-update-catalog
```

### Aggiornamento dopo nuovo release Red Canary

```powershell
git -C C:\ProgramData\Morgana\temp\atomic-red-team pull
python convert_atomics.py --atomics-dir C:\ProgramData\Morgana\temp\atomic-red-team\atomics
```

---

## Come testare l'import in Morgana

**File:** `../tools/test_art_import.py`

```powershell
cd Camelot\morgana\excalibur\tools

# Smoke test (pack più piccoli, ≤30 script)
python test_art_import.py

# Un pack specifico
python test_art_import.py --pack art-lateral-v1

# Tutti i 13 pack
python test_art_import.py --all

# Solo lista senza importare
python test_art_import.py --list
```

Il test legge il master.key da `C:\ProgramData\Morgana\data\master.key`. Morgana deve essere avviato prima di eseguirlo.

### Verifica manuale dopo import

1. Aprire Morgana UI → **Scripts**
2. Filtrare per nome `ART -` — devono comparire gli script importati
3. Aprire uno script → sezione **Tags** → verificare che i `required_tags` siano presenti
4. Creare le tag mancanti con **+ Create missing tags automatically**
5. Assegnare un valore → **Execute** → verificare che `#{art_...}` sia sostituito nel log

---

## Catalog.json

I 13 pack ART sono registrati in `catalog.json` con:
- `"category": "art"`
- `"source": "atomic-red-team"`  
- `"status": "community"`
- URL puntato a `https://raw.githubusercontent.com/x3m-ai/Camelot/main/morgana/excalibur/art/{package_id}.json`

Il campo `status: "community"` li distingue visivamente dai pack Excalibur certificati (`status: "stable"`).

---

## Decisioni architetturali

| Decisione | Scelta | Motivazione |
|---|---|---|
| Formato output | Excalibur Pack JSON | Riusa tutta la pipeline `import-package` senza modifiche al server |
| Granularità | Un pack per MITRE tactic | Specchia la struttura Excalibur; 13 pack gestibili nel catalogo |
| Tag key naming | `art_{tactic}_{tcode}_{arg}` | Evita collisioni con tag Excalibur e tra atomics diversi (stessa chiave piatta) |
| Submodule | No — clone manuale in `C:\ProgramData\Morgana\temp\` | Il repo ART (~500MB) non va in Camelot; il percorso è escluso da Defender |
| Script `manual` | Skippati | Nessun comando da eseguire; non utili in un contesto di automazione |
