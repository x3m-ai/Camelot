# Elastic Cortado — Red Team Automations Provider

**Date:** 2026-08-29
**Repository:** Camelot
**Commit:** See git log

## Summary

| | |
|---|---|
| Release | dev-release-0.1.0+f1dd8bc1 |
| Source commit | `f1dd8bc1883a399c4990f2f4a63d7a3d26cdd89e` |
| License | Elastic License 2.0 |
| Total RTAs | 698 (618 CodeRTA + 80 HashRTA) |
| Scripts | 698 |
| Packages | 13 |
| Catalog total | 267 |
| Unit tests | 11/11 PASS |

## RTA Distribution

| Type | Count | Description |
|---|---|---|
| CodeRTA | 618 | Executable Python behaviors — run via official Cortado wheel |
| HashRTA | 80 | Sample-backed records — preserved as manual scripts |

## Packages

13 packages grouped by ATT&CK tactic + 1 sample-backed package.
Largest: Defense Evasion (210), Unmapped (124), Persistence (61), C2 (59), Execution (55).

## Architecture

- AST-based discovery (platform-safe, no cross-platform import issues)
- Official wheel `cortado-0.1.0+f1dd8bc1-py3-none-any.whl` (SHA256 verified)
- `morgana_cortado_runner.py` wraps CodeRTA execution with MORGANA_RESULT_METADATA output
- HashRTA preserved as manual scripts with sample_hash and Elastic rule metadata
- No Poetry, no manual pip install required on Agent
- Every script carries expected Elastic Endpoint + SIEM rule mappings

## Files Created

### Tooling
- `morgana/excalibur/tools/cortado_ast.py` — AST RTA enumerator
- `morgana/excalibur/tools/cortado_risk.py` — Risk + ATT&CK tactic mapping
- `morgana/excalibur/tools/cortado_risk_overrides.json` — Per-RTA risk overrides
- `morgana/excalibur/tools/convert_cortado.py` — Main converter
- `morgana/excalibur/tools/test_convert_cortado.py` — 11 unit tests

### Provider content
- `morgana/excalibur/detection/cortado/packages/` — 13 JSON packages
- `morgana/excalibur/detection/cortado/source-inventory.json` — 698 entries
- `morgana/excalibur/detection/cortado/build-manifest.json`
- `morgana/excalibur/detection/cortado/conversion-report.json`
- `morgana/excalibur/detection/cortado/morgana_cortado_runner.py`
- `morgana/excalibur/detection/cortado/README.md`
- `morgana/excalibur/detection/cortado/LICENSE-NOTICE.md`

### Updated
- `morgana/excalibur/catalog.json` — +13 packages (267 total)
- `morgana/excalibur/PACKAGES.md` — Section 12 added
- `morgana/excalibur/README.md` — Provider table updated
- `morgana/excalibur/catalog-classification.json` — elastic-cortado override added
