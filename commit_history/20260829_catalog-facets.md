# Excalibur Catalog Facets and Dynamic Classification

**Date:** 2026-08-29
**Repository:** Camelot
**Commit:** See git log

## Purpose

Add normalized facet metadata to catalog.json so Morgana's dynamic filter
system can drive all dropdowns from catalog data without hardcoded option lists.
Also adds classification overrides for all existing providers.

## Summary

### New files

| File | Purpose |
|---|---|
| `morgana/excalibur/catalog-classification.json` | Central classification override file: provider/category overrides, facet_metadata (labels, groups, ordering) for all 8 facet dimensions |
| `morgana/excalibur/tools/enrich_catalog.py` | Enrichment script: reads catalog + classification, adds normalized fields to each pack, builds top-level `facets`, writes back |
| `morgana/excalibur/catalog-classification-report.json` | Classification coverage report: counts for each facet dimension, unclassified packages, legacy field stats |

### catalog.json changes

- Added top-level `facets` object with 8 arrays: `providers`, `specialties`, `attack_domains`, `attack_tactics`, `package_types`, `execution_platforms`, `target_environments`, `operational_risks`.
- Each array entry has at minimum `{id, label}`; specialties and target_environments also have `group` for optgroup rendering.
- All 224 packs enriched with: `specialties`, `package_types`, `execution_platforms`, `target_environments`, `mitre_tactics_resolved`.
- Legacy fields (`platform`, `category`, `plan_type`, `mitre_tactic`) preserved for backward compatibility.

### Facet coverage

| Facet | Distinct values |
|---|---|
| providers | 11 |
| specialties | 12 |
| attack_domains | 3 |
| attack_tactics | 48 |
| package_types | 10 |
| execution_platforms | 4 |
| target_environments | 13 |
| operational_risks | 4 |

### Classification applied

| Provider | package_types | specialties | exec_platforms | target_envs |
|---|---|---|---|---|
| atomic-red-team | atomic-tests | endpoint, adversary-emulation | from platform[] | from platform[] |
| mitre-ctid | full/micro-emulation | adversary-emulation, detection-validation | from platform[] | from platform[] |
| mitre-stockpile | procedure-library | adversary-emulation | from platform[] | from platform[] |
| lolbas | procedure-library | living-off-the-land | windows | windows |
| gtfobins | procedure-library | living-off-the-land | linux, macos | linux, macos |
| loldrivers | procedure-library, detection-validation | driver-security | windows | windows |
| frida-mobile | runtime-instrumentation | mobile, runtime-instrumentation | host-agent | android/ios per category |
| ics-scada-fuzzer | fuzzing-generator | ot-ics, fuzzing | linux | ot-ics |
| anssi-fuzzysully | fuzzing-generator | ot-ics, opc-ua, fuzzing | linux | ot-ics, opc-ua |
| x3m-ai | technology-pack | technology | from platform[] | from platform[] |

### Legacy platform normalization

- `"all"` → `execution_platforms: ["cross-platform"]` (no longer appears as filter option `ALL`)
- `"azure"` in platform[] → `target_environments: ["azure","entra-id"]` (not in exec platforms)
- Frida `"all"` platform → `execution_platforms: ["host-agent"]`

## Files Modified

| File | Change |
|---|---|
| `morgana/excalibur/catalog.json` | Added `facets`, enriched all 224 packs |
| `morgana/excalibur/catalog-classification.json` | NEW |
| `morgana/excalibur/tools/enrich_catalog.py` | NEW |
| `morgana/excalibur/catalog-classification-report.json` | NEW |
| `commit_history/20260829_catalog-facets.md` | This record |
