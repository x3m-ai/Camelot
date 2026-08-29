# Stratus Red Team — Cloud Adversary Emulation Packages

**Date:** 2026-08-29
**Repository:** Camelot
**Commit:** See git log

## Purpose

Integrate the complete Stratus Red Team technique registry as a first-class
Morgana cloud adversary-emulation provider. 93 techniques across 6 cloud
platforms, 30 packages, verified official Stratus v2.36.0 binaries.

---

## Summary

| | |
|---|---|
| Release | v2.36.0 |
| Source commit | `21c8fefa7cca862b38908090f85b403ed418400c` |
| License | Apache-2.0 |
| Techniques discovered | 93 |
| Scripts generated | 93 |
| Packages | 30 |
| Catalog total (after) | 254 |

---

## Techniques by platform

| Platform | Scripts |
|---|---|
| AWS | 44 |
| Azure | 15 |
| GCP | 19 |
| Entra ID | 7 |
| Kubernetes | 6 |
| Amazon EKS | 2 |

---

## Architecture

- **One Script per registered Stratus AttackTechnique** — no artificial inflation
- **MORGANA_TEST_ID = STRATUS_RED_TEAM_CORRELATION_ID** for Detection Fabric correlation
- **Separate detonate + cleanup lifecycle** — cleanup_command uses same correlation ID
- **Official Stratus binary** — downloaded at Agent runtime with SHA256 verification
- **No credentials embedded** — uses existing cloud auth (env vars, profile, ADC, kubeconfig)
- **Dynamic catalog facets** — cloud/aws/gcp/kubernetes/entra-id specialties and target_environments

---

## Files Created/Modified

### New tooling
- `morgana/excalibur/tools/stratus_source.py` — Go source technique enumerator (regex-based)
- `morgana/excalibur/tools/stratus_assets.py` — Official release asset + checksum definitions
- `morgana/excalibur/tools/stratus_risk_overrides.json` — Per-technique risk overrides
- `morgana/excalibur/tools/convert_stratus.py` — Main converter: enumerate → generate → publish
- `morgana/excalibur/tools/test_convert_stratus.py` — 10 unit tests (all passing)

### New packages (30 JSON files)
```
morgana/excalibur/cloud/stratus/
  aws/       (10 packages: credential-access, defense-evasion, discovery,
              execution, exfiltration, impact, initial-access,
              lateral-movement, persistence, privilege-escalation)
  azure/     (6 packages)
  gcp/       (7 packages)
  entra-id/  (1 package)
  k8s/       (3 packages)
  eks/       (2 packages)
  source-inventory.json
  conversion-report.json
  release-manifest.json
  README.md
  LICENSE-NOTICE.md
```

### Updated catalog
- `morgana/excalibur/catalog.json` — +30 Stratus packages (total: 254)
- `morgana/excalibur/catalog-classification.json` — Added cloud/aws/gcp/kubernetes/entra-id
  specialties and target_environments; added stratus-red-team provider override
- Catalog re-enriched: 12 providers, 15 specialties, 15 target environments, 57 tactics

### Updated documentation
- `morgana/excalibur/PACKAGES.md` — Added Section 11 (Stratus Red Team), updated totals
- `morgana/excalibur/README.md` — Updated provider table totals

---

## Unit tests

```
10/10 passed + 30 subtests passed
```

Tests cover: technique parsing, multi-tactic preservation, risk mapping,
platform metadata, stable IDs, no duplicate IDs, package structure,
correlation ID presence, source inventory, catalog validation.

---

## Validation

| Check | Result |
|---|---|
| Source reconciliation | PASS (93 techniques = 93 published) |
| Static script validation (all packages) | PASS |
| No credentials embedded | PASS |
| MORGANA_TEST_ID in all commands | PASS |
| Correlation ID in cleanup commands | PASS |
| STRATUS prefix in all script names | PASS |
| Catalog: 30 Stratus entries | CONFIRMED |
| Facets: cloud specialties/targets | CONFIRMED |

---

## Runtime smoke tests

**NOT RUN** — no authorized cloud sandbox available in this environment.
Static validation, unit tests, and import validation serve as primary quality gates.
Runtime detonation belongs to operator/lab validation using authorized sandbox accounts.
