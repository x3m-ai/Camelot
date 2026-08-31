# MEDUSA — Complete Mobile Instrumentation Provider

**Date:** 2026-08-31
**Repository:** Camelot
**Commit:** See git log

## Purpose

Recover and complete the interrupted MEDUSA provider: import the complete
pinned Ch0pin/medusa module corpus as a first-class Morgana mobile runtime
instrumentation provider, independent from Frida Mobile.

---

## Summary

| | |
|---|---|
| Source repository | `Ch0pin/medusa` |
| Pinned commit | `8c62447d082f8612aeb9e07f8d8c20d8fa5f1fbb` |
| Stable release | v3.9.6 |
| License | GPL-3.0 |
| Android modules (.med) | 125 |
| iOS modules (.imed) | 12 |
| Standalone snippets | 14 |
| Published Scripts | 147 (133 modules + 14 snippets) |
| Manual Scripts | 4 |
| Packages | 38 (33 Android + 5 iOS) |
| Catalog total (after) | 313 |

---

## Architecture

- **MEDUSA source module → compiler (core JS + module Code) → existing Morgana Frida executor**
- **Precompiled at build time** — core runtime inlined, Options placeholders substituted at execution time via Morgana tag substitution
- **Android** wraps in `Java.perform` + `setTimeout(displayAppInfo,500)` + JNIEnv prolog for JNICalls
- **iOS** wraps in `try{}` ObjC block
- **Options** `__name__ = value` → `#{name}` runtime tags (string quoted, boolean/number unquoted)
- **No cross-provider dedup** — MEDUSA published independently of Frida Mobile

---

## Files Created

### Tooling
- `morgana/excalibur/tools/medusa_compiler.py` — source-faithful module compiler + JS syntax validation
- `morgana/excalibur/tools/convert_medusa.py` — converter: parse → compile → package → catalog
- `morgana/excalibur/tools/medusa_risk_overrides.json` — per-module risk overrides (empty baseline)
- `morgana/excalibur/tools/test_medusa_runtime.py` — 6 compiler/runtime unit tests
- `morgana/excalibur/tools/test_medusa_import.py` — 38-package static validation
- `morgana/excalibur/tools/test_medusa_module_parser.py` — parser tests (corrected to real counts)
- `morgana/excalibur/tools/update-medusa-packs.ps1` — full build/validate/publish pipeline

### Packages (38 JSON) + reports
```
morgana/excalibur/mobile/medusa/
  android/  (33 packages)
  ios/      (5 packages)
  medusa-source-inventory.json
  conversion-report.json
  source-diff.json
  source-extension-inventory.json
  medusa-frida-overlap-report.json
  medusa-runtime-manifest.json
  README.md
  LICENSE-NOTICE.md
```

### Updated
- `morgana/excalibur/catalog.json` — +38 MEDUSA packages (total 313), provider + 2 categories + facets
- `morgana/excalibur/catalog-classification.json` — MEDUSA provider override + 2 category overrides + facet entry
- `morgana/excalibur/tools/medusa_module_parser.py` — pre-existing path/category/options fixes preserved
- `morgana/excalibur/PACKAGES.md`, `README.md`, `CHANGELOG.md`

---

## Validation

| Check | Result |
|---|---|
| Source reconciliation | PASS (151 = 147 published + 4 manual) |
| Parse errors | 0 |
| Compiler/runtime unit tests | 6/6 PASS |
| Package static validation | 38/38 PASS |
| JS syntax (node --check) | PASS (133/133 modules) |
| Catalog MEDUSA metadata | 0 errors |
| Overlap suppression | 0 (Frida / semantic) |

## Runtime smoke tests

**NOT RUN** — no authorized mobile lab / Morgana server available in this environment.
Static validation, unit tests, and package validation serve as primary quality gates.

## Known limitations

- 1 upstream iOS module (`dump_ios_url_scheme.imed`) has a genuine brace defect → published as manual.
- Pre-existing catalog metadata errors for 5 older providers are unrelated to MEDUSA.
