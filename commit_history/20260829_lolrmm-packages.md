# LOLRMM — Living Off the Land RMM Provider

**Date:** 2026-08-29  
**Repository:** Camelot  

| | |
|---|---|
| Source commit | `fa859607fb05af91878ac8d44a59655f44d286fe` |
| License | Apache-2.0 |
| Tools | 320 (291 probe + 29 manual) |
| Scripts | 320 |
| Packages | 3 |
| Catalog total | 270 |
| Unit tests | 9/9 PASS |

## Files
- `morgana/excalibur/tools/lolrmm_source.py` — YAML parser/normalizer
- `morgana/excalibur/tools/convert_lolrmm.py` — converter
- `morgana/excalibur/tools/test_convert_lolrmm.py` — 9 tests
- `morgana/excalibur/lotl/lolrmm/packages/` — 3 JSON packages (320 scripts)
- `morgana/excalibur/lotl/lolrmm/source-inventory.json` — 320 entries
- `morgana/excalibur/lotl/lolrmm/conversion-report.json`
- `morgana/excalibur/lotl/lolrmm/README.md`
- `morgana/excalibur/lotl/lolrmm/LICENSE-NOTICE.md`
- `morgana/excalibur/catalog.json` — +3 packages (270 total)
- `morgana/excalibur/PACKAGES.md` — Section 13
- `morgana/excalibur/README.md` — table updated

## Smoke tests
NOT RUN — no authorized endpoint lab. Static validation + unit tests serve as quality gate.
Runtime testing of RMM artifact probes requires authorized test endpoints with known tool installations.
Morgana did NOT install, download, or operate any LOLRMM-cataloged RMM product.
