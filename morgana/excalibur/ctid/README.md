# CTID Threat-Informed Emulation Packs

Morgana-native threat-informed packages derived from the MITRE Center for Threat-Informed Defense Adversary Emulation Library. The CTID library is the canonical intelligence and plan source; MITRE Emu is retained only as a conversion reference.

> Use this content only for explicitly authorized security validation, Purple Team exercises, research, and defensive testing.

## Initial Milestone

| Plan | Type | Scripts | Automated | Manual | Chains |
|---|---|---:|---:|---:|---:|
| APT29 | Full Emulation | 79 | 79 | 0 | 1 |
| Carbanak | Full Emulation | 24 | 24 | 0 | 1 |
| FIN6 | Full Emulation | 27 | 27 | 0 | 1 |
| FIN7 | Full Emulation | 10 | 10 | 0 | 1 |
| menuPass | Full Emulation | 15 | 15 | 0 | 1 |
| OilRig | Full Emulation | 44 | 44 | 0 | 1 |
| Sandworm Team (G0034) | Full Emulation | 40 | 40 | 0 | 1 |
| Turla - Carbon | Full Emulation | 45 | 45 | 0 | 1 |
| Turla - Snake | Full Emulation | 53 | 53 | 0 | 1 |
| Wizard Spider | Full Emulation | 38 | 38 | 0 | 4 |
| Blind Eagle | Full Emulation | 4 | 4 | 0 | 1 |
| OceanLotus | Full Emulation | 7 | 7 | 0 | 1 |
| Active Directory Enumeration | Micro Emulation | 1 | 1 | 0 | 1 |
| Remote Application Exploitation <!-- TOC ignore:true --> | Micro Emulation | 1 | 1 | 0 | 1 |
| Data Exfiltration | Micro Emulation | 1 | 1 | 0 | 1 |
| DLL Side-loading | Micro Emulation | 1 | 1 | 0 | 1 |
| File Access and File Modification | Micro Emulation | 1 | 1 | 0 | 1 |
| Clear Windows Event Logs | Micro Emulation | 1 | 1 | 0 | 1 |
| Named Pipes | Micro Emulation | 1 | 1 | 0 | 1 |
| Process Injection | Micro Emulation | 1 | 1 | 0 | 1 |
| Reflective Code Loading | Micro Emulation | 1 | 1 | 0 | 1 |
| User Execution | Micro Emulation | 1 | 1 | 0 | 1 |
| Web Shells | Micro Emulation | 1 | 1 | 0 | 1 |
| Windows Registry | Micro Emulation | 1 | 1 | 0 | 1 |

The full package preserves CTID procedure order in a modern Morgana `chains[].flow`. No conditional logic is invented: the initial canonical Chain is linear because the selected source plan does not provide a machine-evaluable branch criterion.

## Operational Procedures

Self-contained CTID commands are preserved as source-command Scripts. Procedures that depend on unavailable payloads, external C2 primitives, unsupported executors, or unresolved runtime facts become labeled Morgana-native simulations. Every Chain node is dispatchable; simulations create representative host or network telemetry in a confined workspace and include cleanup.

Micro plans use operational behavior simulations until a specific CTID release asset is reviewed and pinned with source version, license, platform, architecture, size, URL, and SHA256.

## Package Contents

- `full/`: named adversary full-emulation packages and canonical Attack Chains.
- `micro/`: focused compound-behavior packages.
- `plan-manifest.json`: normalized plan/scenario/step representation.
- `source-inventory.json`: per-procedure conversion status, requirements, payload references, and generated Script identity.
- `conversion-report.json`: source/reference commits, completeness metrics, Chain counts, and known limitations.

## Safety And Assets

The converter reads and normalizes source content but never executes procedures, payloads, build instructions, or external tools. No encrypted or malware-like payload is automatically decrypted, downloaded, mirrored, or approved. Reviewed future assets must use Morgana's existing HTTPS and SHA256-verified package asset model.

Credential, target host, server, domain, user, path, share, and URL defaults are blanked for runtime configuration. Operators must supply values for an explicitly authorized environment.

## Updating

Run `morgana/excalibur/tools/update-ctid-emu-packs.ps1`. The pipeline updates both source checkouts, records their SHAs, runs fixture tests, converts content, validates package flows and catalog metadata, and prints the conversion report. It never executes a Chain. Package import is opt-in with `-SmokeImport`; publication is opt-in with `-Publish`.

## Provenance

- CTID source: `https://github.com/center-for-threat-informed-defense/adversary_emulation_library`
- CTID commit: `4467a6eed6e67d25009704130e1d27d1a8007f57`
- MITRE Emu reference commit: `ef3bc4fa8fb605c774446ba7741365ba45d375a8`
- License: Apache-2.0

See the package `documentation_url` and per-procedure `cti_source` metadata for full source context.
