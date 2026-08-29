# ANSSI FuzzySully Post-Integration Refinement

**Date:** 2026-08-29
**Repository:** Camelot
**Commit:** See git log

## Purpose

Correct root-project license metadata (LGPL-2.1 → GPL-2.0), add a pinned runtime deployment artifact, and expand the FuzzySully corpus with 6 genuinely novel targeted OPC UA request-node profiles discovered via Fuzzowski graph analysis.

## Summary

| | Before | After |
|---|---|---|
| Scripts | 73 | 79 |
| Packages | 4 | 7 |
| Root license | LGPL-2.1 (wrong) | GPL-2.0 (correct) |
| Runtime lock | missing | `requirements-lock.txt` |
| Bundle build script | missing | `build-bundle.sh` |

---

## Refinement A — License correction

The upstream `ANSSI-FR/fuzzysully` repository contains `LICENCE.md` with "GNU GENERAL PUBLIC LICENSE Version 2". The previous milestone incorrectly recorded `LGPL-2.1`.

**Files updated:**
- `LICENSE-NOTICE.md` — corrected to GPL-2.0 with separate LGPL-2.1 attribution for opcua-asyncio
- `README.md` — license badge corrected
- `build-manifest.json` — `source_license: "GPL-2.0"`
- `conversion-report.json` — `source_license: "GPL-2.0"` + `license_corrected` note
- `convert_fuzzysully.py` — all generated package and asset JSON now emits `"GPL-2.0"`
- `fuzzysully_mapping_overrides.json` — license corrected
- All 7 package JSON files regenerated with correct license

---

## Refinement B — Runtime deployment

Added reproducible deployment artifacts so agents do not require manual `git clone` or ad-hoc `pip install`:

| File | Purpose |
|---|---|
| `requirements-lock.txt` | Exact pinned versions of all FuzzySully dependencies |
| `build-bundle.sh` | Linux build script — produces `fuzzysully-runtime-linux-amd64.tar.gz` self-contained venv |
| `build-manifest.json` | Added `requirements_lock_sha256`, `runtime_bundle_filename`, `runtime_self_contained`, `manual_fuzzysully_install_required` |

**Runtime installation path (until bundle is published):**
```bash
pip install -r requirements-lock.txt
pip install fuzzysully==0.1.1
# No git, gcc, apt, or WSL required
```

**`manual_fuzzysully_install_required = true`** documented clearly. Set to `false` after `build-bundle.sh` is run on Linux and the bundle is published to Camelot CDN.

---

## Refinement C — Targeted OPC UA request-node profiles

Performed Fuzzowski graph analysis: enumerated all `s_initialize()` request nodes (32 total) and identified which are **never** the fuzz target in any existing high-level function (always prerequisite/cleanup only).

**Genuinely novel targeted profiles (6 new scripts):**

| Script | Node | Mode/Policy | Why novel |
|---|---|---|---|
| `FUZZYSULLY TARGET - SERVER - CREATESESSION - NONE` | CreateSession | server/None | Always prerequisite, never targeted |
| `FUZZYSULLY TARGET - SERVER - ACTIVATESESSION - NONE` | ActivateSession | server/None | Always prerequisite, never targeted |
| `FUZZYSULLY TARGET - SERVER - CLOSESESSION - NONE` | CloseSession | server/None | Always cleanup, never targeted |
| `FUZZYSULLY TARGET - SERVER - CLOSESECURECHANNEL - NONE` | CloseSecureChannel | server/None | Always cleanup, never targeted |
| `FUZZYSULLY TARGET - SERVER - CLOSESECURECHANNELSIGN - BASIC256SHA256` | CloseSecureChannelSign | server/Basic256Sha256 | Signed variant; never targeted |
| `FUZZYSULLY TARGET - REVERSE - REVERSEHELLOERROR - NONE` | ReverseHelloError | reverse/None | Error response path; never targeted |

**Deduplication:** Nodes already covered by existing 73 (Browse, Read, OpenSecureChannel, etc.) were not duplicated. Target-node inventory written to `target-node-inventory` section of `fuzzysully_mapping_overrides.json`.

**Mechanism:** `goto_path("NodeName")` via Fuzzowski Session API — runner accepts `--goto-path` argument.

**New packages:**
- `fuzzysully-server-none-targeted-v1` (4 scripts)
- `fuzzysully-server-basic256sha256-targeted-v1` (1 script)
- `fuzzysully-reverse-targeted-v1` (1 script)

---

## Python version normalization

`requires_python = ">=3.10"` confirmed from `pyproject.toml` — consistent across all metadata.

---

## Files Modified

### Tooling
- `morgana/excalibur/tools/convert_fuzzysully.py` — targeted profile generation, GPL-2.0, `--goto-path` support, runtime bundle manifest fields
- `morgana/excalibur/tools/fuzzysully_mapping_overrides.json` — GPL-2.0, `targeted_nodes` definitions, runtime bundle metadata
- `morgana/excalibur/tools/test_convert_fuzzysully.py` — updated counts (79 scripts, 7 packages, 6 targeted)
- `morgana/excalibur/tools/validate_fuzzysully_packages.py` — 7 packages, GPL-2.0 check, `requirements_lock_sha256` check

### Content — existing packages (license corrected, regenerated)
- `morgana/excalibur/ot/fuzzing/fuzzysully/server-none/fuzzysully-server-none-v1.json`
- `morgana/excalibur/ot/fuzzing/fuzzysully/server-basic256sha256/fuzzysully-server-basic256sha256-v1.json`
- `morgana/excalibur/ot/fuzzing/fuzzysully/gds/fuzzysully-gds-v1.json`
- `morgana/excalibur/ot/fuzzing/fuzzysully/reverse/fuzzysully-reverse-v1.json`

### Content — new targeted packages
- `morgana/excalibur/ot/fuzzing/fuzzysully/server-none-targeted/fuzzysully-server-none-targeted-v1.json`
- `morgana/excalibur/ot/fuzzing/fuzzysully/server-basic256sha256-targeted/fuzzysully-server-basic256sha256-targeted-v1.json`
- `morgana/excalibur/ot/fuzzing/fuzzysully/reverse-targeted/fuzzysully-reverse-targeted-v1.json`

### Content — support files
- `morgana/excalibur/ot/fuzzing/fuzzysully/LICENSE-NOTICE.md`
- `morgana/excalibur/ot/fuzzing/fuzzysully/README.md`
- `morgana/excalibur/ot/fuzzing/fuzzysully/build-manifest.json`
- `morgana/excalibur/ot/fuzzing/fuzzysully/conversion-report.json`
- `morgana/excalibur/ot/fuzzing/fuzzysully/source-inventory.json`
- `morgana/excalibur/ot/fuzzing/fuzzysully/morgana_fuzzysully_runner.py`
- `morgana/excalibur/ot/fuzzing/fuzzysully/requirements-lock.txt` (NEW)
- `morgana/excalibur/ot/fuzzing/fuzzysully/build-bundle.sh` (NEW)

### Catalog
- `morgana/excalibur/catalog.json` — +3 targeted packages (224 total packs)

---

## Validation

| Check | Result |
|---|---|
| Unit tests | 12/12 PASS |
| Static validation | PASS — 79 scripts, 7 packages, catalog, runner hash |
| License field | GPL-2.0 confirmed in build-manifest, all package JSONs |
| requirements_lock_sha256 | `ca749a47...` verified |
| Existing 73 profiles | Preserved — IDs unchanged |
| Catalog | 7 FuzzySully entries confirmed |
