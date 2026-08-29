# ControlThings Suite — ICS/OT Protocol Assessment Provider

**Date:** 2026-08-29 | **Repository:** Camelot

| | |
|---|---|
| Components | ctmodbus, ctserial, ctspi, cti2c, ctvelocio |
| Scripts | 33 |
| Packages | 5 |
| Catalog total | 275 |
| Unit tests | 13/13 PASS |

## Components

| Repo | Role | License | Commit |
|---|---|---|---|
| ctmodbus | Executable Modbus tool | LGPL-3.0 | f8f91d9 |
| ctserial | Executable serial tool | LGPL-3.0 | 58abc18 |
| ctspi | Manual profile (Py2/hardware) | GPL-3.0 | fdd310b |
| cti2c | Manual profile (Py2/hardware) | GPL-3.0 | 9f0daa6 |
| ctvelocio | Manual profile (Py2/hardware) | GPL-3.0 | 190b51d |

## Files
- `tools/controlthings_sources.json` — multi-repo source manifest
- `tools/convert_controlthings.py` — converter
- `tools/test_convert_controlthings.py` — 13 tests
- `ot/controlthings/packages/` — 5 JSON packages
- `ot/controlthings/morgana_ctmodbus_runner.py` — non-interactive Modbus runner
- `ot/controlthings/morgana_ctserial_runner.py` — non-interactive serial runner
- `ot/controlthings/README.md`, `LICENSE-NOTICE.md`, `conversion-report.json`, `source-manifest.json`
- `catalog.json` — +5 packages (275 total)
- `PACKAGES.md` — Section 14 added
- `README.md` — provider table updated

## Smoke tests
NOT RUN — no authorized OT/ICS lab endpoint available. Static validation + 13 unit tests serve as quality gate.
