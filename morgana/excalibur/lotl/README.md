# Morgana Living-Off-The-Land Packs

Source-derived LOLBAS and GTFOBins procedures for authorized detection validation and Purple Team exercises. Conversion and import are static operations: no generated command is executed by the build pipeline.

## Corpus

| Provider | Source objects | Raw variants | Published Scripts | Duplicates | Packs |
|---|---:|---:|---:|---:|---:|
| LOLBAS | 245 | 484 | 475 | 9 | 15 |
| GTFOBins | 478 | 3585 | 3582 | 3 | 34 |
| **Combined** | **723** | **4069** | **4057** | **12** | **49** |

LOLBAS packs contain Windows procedures grouped by the current upstream behavioral category. GTFOBins packs contain Linux/Unix procedures grouped by function and explicit execution context. Packs are deterministically chunked at a maximum of 400 Scripts and intentionally contain no mass-generated one-step Chains.

## Execution Readiness

- `ready`: self-contained source command.
- `ready_with_parameters`: requires operator-supplied Morgana Tags.
- `environment_prerequisite`: requires a preconfigured sudo, SUID, or capability context.
- `interactive`: retains source interactive behavior and requires an appropriate session.
- `manual_counterpart_required`: requires separately controlled listener, connector, sender, or receiver infrastructure.

Morgana does not grant privileges, modify sudoers, configure SUID/capabilities, or start attacker-side infrastructure. Remote targets and paths are blank operator-supplied Tags.

## Updating

Run `morgana/excalibur/tools/update-lotl-packs.ps1`. It updates both source repositories, records SHAs, runs compact fixture tests, converts the complete corpus, reconciles all variants, validates every generated Script/package/catalog entry, and stops. Use `-SmokeImport` only to import one representative package per provider without execution. Publication requires explicit `-Publish` approval.

## Provenance

- LOLBAS: `67781fd49a5c8605bba0171dc3d3feec148b432e` / GPL-3.0
- GTFOBins: `acd524623f9c406acedd2754ebd9c2431f3675ad` / GPL-3.0
- Unique ATT&CK techniques: 66
- Conversion validation: PASS

See `conversion-report.json` for provider/category/context/TCode/readiness counts and `source-inventory.json` for source-level coverage accounting.
