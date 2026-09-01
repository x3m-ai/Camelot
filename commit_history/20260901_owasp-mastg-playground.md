# OWASP MASTG + Hacking Playground

**Date:** 2026-09-01
**Repository:** Camelot
**Commit:** See git log

## Purpose

Publish the complete OWASP MASTG test library, executable OWASP demos, and the
OWASP MASTG Hacking Playground app/backend assets to the Camelot CDN for Morgana
Mobile Lab consumption.

## Summary

| | |
|---|---|
| Upstream | `OWASP/mastg` @ `ef19f2b1` (CC BY-SA 4.0) |
| Playground | `OWASP/MASTG-Hacking-Playground` @ `db219a10` (GPL-3.0) |
| MASTG tests published | 292 (163 Android / 129 iOS) manual procedure cards |
| MASTG demos published | 157 (23 executable Frida, 134 manual reference) |
| Knowledge/techniques/tools/apps/best-practices | 550 reference records |
| Hacking Playground | 3 App Assets + 1 Rails backend Supporting Service |
| Mobile Lab templates | 2 (android-mastg-playground-lab, ios-mastg-playground-lab) |
| Validation | PASS (100% reconciliation) |

## Files Added / Modified

### Added — MASTG content
- `morgana/excalibur/mobile/mastg/` — 4 packs, 6 inventory/report JSONs, coverage, apps index, README.
- `morgana/mobile-lab/mastg-coverage.json` — MASTG tests + demos + MASVS rollup (CDN).
- `morgana/mobile-lab/owasp-playground-apps.json` — Hacking Playground app/service index.
- `morgana/mobile-lab/templates/android-mastg-playground-lab.json`, `ios-mastg-playground-lab.json`.

### Added — Tooling
- `morgana/excalibur/tools/mastg_parser.py`, `convert_mastg.py`,
  `test_mastg_parser.py`, `test_mastg_import.py`, `update-mastg.ps1`.

### Modified
- `morgana/excalibur/catalog.json` — +4 `owasp-mastg` packs (facets enriched).
- `morgana/excalibur/catalog-classification.json` — `owasp-mastg` provider,
  `test-methodology` package type, per-category overrides.
- `morgana/mobile-lab/catalog.json` — +3 apps, +1 service, +2 templates.
- `morgana/mobile-lab/README.md`, `morgana/README.md`, `docs/morgana/getting-started.md`.

## Notes
- MASTG Tests are manual procedure cards; only real Frida demos are executable.
- Hacking Playground binaries are not re-distributed (GPL-3.0, source-pinned).
- The Playground does not provide complete MASTG coverage; Morgana does not claim it does.
