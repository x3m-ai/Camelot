# MITRE CALDERA Stockpile Packs for Morgana

MITRE CALDERA Stockpile abilities converted into Morgana-native Excalibur Pack JSON.

- **Upstream:** [MITRE Stockpile](https://github.com/mitre/stockpile)
- **License:** Apache License 2.0
- **Original authors:** MITRE and Stockpile contributors
- **Conversion:** X3M.AI for Morgana
- **Runtime dependency:** None. CALDERA and Stockpile are not installed or required by Morgana.

## Current Conversion Snapshot

The current generated set uses Stockpile commit `996ec41cd1c5d1c7cc09e620fc55dabe5aefd9cc` dated 2026-04-30.

| Measure | Count |
|---|---:|
| YAML files scanned | 209 |
| Abilities parsed | 190 |
| Platform/executor variants | 314 |
| Morgana Scripts generated | 221 |
| Variants skipped | 93 |
| Packs generated | 11 |
| CALDERA facts converted | 125 |
| Payload references excluded | 49 |
| Unsafe runtime-dependent variants excluded | 33 |

See `conversion-report.json` for the complete machine-readable diagnostics.

## Architecture

```text
MITRE Stockpile data/abilities/**/*.yml
                  |
                  v
          convert_stockpile.py
                  |
                  v
       Morgana Excalibur Pack JSON
                  |
                  v
          Camelot public catalog
                  |
                  v
  Morgana /api/v2/scripts/import-package
                  |
                  v
       Native Morgana Scripts and Chains
```

The converter is an offline content adapter. It reads, parses, normalizes, validates, and writes JSON. It never executes an ability command, cleanup command, payload, parser, requirement, or build block.

## Package Naming

One package is generated per supported MITRE ATT&CK tactic:

```text
stockpile-discovery-v1
stockpile-exec-v1
stockpile-persist-v1
stockpile-privesc-v1
stockpile-evasion-v1
stockpile-credaccess-v1
stockpile-lateral-v1
stockpile-collection-v1
stockpile-exfil-v1
stockpile-c2-v1
stockpile-impact-v1
```

Generated scripts use deterministic names:

```text
STOCKPILE - <TCODE> - <Ability Name> [<Platform>/<Executor>]
```

Every generated script retains its Stockpile ability UUID, source path, source platform, and source executor in package metadata. These fields support a future adversary-profile conversion phase without changing the Morgana database schema.

## Supported Variants

| Stockpile | Morgana |
|---|---|
| `windows` | `windows` |
| `linux` | `linux` |
| `darwin`, `macos` | `macos` |
| `psh`, `pwsh`, `powershell` | `powershell` |
| `cmd` | `cmd` |
| `sh`, `bash` | `bash` |
| `python`, `python3` | `python` |

Comma-separated Stockpile compatibility keys such as `psh,pwsh` are expanded and deduplicated by normalized platform/executor identity.

Only direct command variants are emitted in Phase 1.

## CALDERA Facts and Morgana Tags

CALDERA facts in commands and cleanup blocks are converted to scoped Morgana tags.

```text
#{remote.host.ip}
```

becomes a key similar to:

```text
#{stockpile_lateral_1021_002_remote_host_ip}
```

The generated tag appears in the pack-level `tag_categories` and the script's `required_tags`. Values are supplied through Morgana's existing tag assignment and substitution workflow. Morgana does not implement a CALDERA fact engine.

Credential-like fact names are marked sensitive. Defaults and example credentials are never invented.

## Unsupported and Diagnostic-Only Features

Phase 1 intentionally does not recreate the CALDERA runtime.

| Feature | Phase 1 behavior |
|---|---|
| Parser metadata | Command may be imported; parser is recorded but ignored during execution |
| CALDERA requirements | Preserved in diagnostics; orchestration relationships are not enforced |
| Payload-dependent variants | Detected and skipped; arbitrary payloads are not copied into Camelot |
| Source/build variants | Detected and skipped; Morgana does not compile Stockpile source code |
| Sandcat/CALDERA runtime dependencies | Detected and skipped |
| Unverified remote downloads | Detected and skipped when no package integrity metadata is available |
| Unknown executors/platforms | Logged and skipped without aborting the conversion |
| Stockpile adversaries | Not imported in Phase 1 |

A skipped variant is preferable to publishing content that appears ready but cannot execute correctly.

## Conversion Report

`conversion-report.json` records:

- exact upstream commit SHA and commit date;
- YAML files and abilities scanned;
- variants generated and skipped;
- executor and platform counts;
- converted facts and cleanup blocks;
- parser and requirement metadata;
- payload references;
- unsupported build variants;
- malformed/invalid source entries;
- package counts.

The report is diagnostic metadata and is not an installable catalog entry.

## Update Procedure

Dry run without writing packs or catalog entries:

```powershell
.\morgana\excalibur\tools\update-stockpile-packs.ps1 -DryRun
```

Generate and validate all packs:

```powershell
.\morgana\excalibur\tools\update-stockpile-packs.ps1
```

Generate, validate, and smoke-import Discovery into a local Morgana server:

```powershell
.\morgana\excalibur\tools\update-stockpile-packs.ps1 -SmokeImport
```

Publish only after review and explicit approval:

```powershell
.\morgana\excalibur\tools\update-stockpile-packs.ps1 -SmokeImport -Publish
```

If a reviewed upstream change intentionally removes more than 25% of the currently published Scripts, add `-AllowLargeReduction`. Without that explicit switch, the pipeline stops before replacing files.

The updater clones or updates Stockpile under `C:\ProgramData\Morgana\temp\stockpile`; the upstream repository is never stored in Camelot.

After Morgana's initial `STOCKPILE -` prefix and catalog category support is deployed, future scripts and packs require only a Camelot catalog publication. Morgana fetches the current catalog dynamically when the user selects **Scripts > Excalibur Packs > Refresh catalog**.

## Direct Converter Commands

All tactics:

```powershell
python .\morgana\excalibur\tools\convert_stockpile.py `
  --stockpile-dir C:\ProgramData\Morgana\temp\stockpile
```

Discovery dry run:

```powershell
python .\morgana\excalibur\tools\convert_stockpile.py `
  --stockpile-dir C:\ProgramData\Morgana\temp\stockpile `
  --tactic discovery `
  --dry-run `
  --no-update-catalog
```

Filter by platform:

```powershell
python .\morgana\excalibur\tools\convert_stockpile.py `
  --stockpile-dir C:\ProgramData\Morgana\temp\stockpile `
  --platform windows
```

## Validation and Import Tests

Run converter fixture tests without executing any ability:

```powershell
python -m unittest morgana.excalibur.tools.test_convert_stockpile -v
```

List and statically validate every generated pack:

```powershell
python .\morgana\excalibur\tools\test_stockpile_import.py --all --validate-only
```

Smoke-import Discovery:

```powershell
python .\morgana\excalibur\tools\test_stockpile_import.py --pack stockpile-discovery-v1
```

Use a different Morgana endpoint:

```powershell
$env:MORGANA_API_KEY = '<MORGANA_API_KEY>'
python .\morgana\excalibur\tools\test_stockpile_import.py `
  --pack stockpile-discovery-v1 `
  --url https://<SERVER_HOST>:8888/api/v2/scripts/import-package
```

The test tool disables TLS certificate verification only for localhost development URLs, matching the existing local smoke-test convention.

## Attribution and License

Stockpile is a MITRE CALDERA plugin distributed under the Apache License 2.0. X3M.AI did not author the original abilities. Generated packs retain the upstream repository, commit SHA, ability UUID, and source path.

Review the [upstream license](https://github.com/mitre/stockpile/blob/master/LICENSE) before redistribution or modification.

## Phase 2

A future phase may convert Stockpile adversary definitions into ordered Morgana Chains by resolving preserved ability UUIDs to converted variants. Phase 1 does not claim that the generated full-tactic convenience chains represent authentic CALDERA adversaries or threat-actor operation sequences.
