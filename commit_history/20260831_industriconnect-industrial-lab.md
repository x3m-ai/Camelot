# IndustriConnect Provider + Industrial Lab Catalog

**Date:** 2026-08-31
**Repository:** Camelot
**Commit:** See git log

## Purpose

Publish the IndustriConnect Excalibur provider (130 MCP tools → 130 Scripts,
10 protocol packages) and the provider-agnostic Industrial Lab catalog
(10 mock service manifests + 4 Lab templates) to the Camelot CDN.

---

## Summary

| | |
|---|---|
| Upstream | `IndustriAgents/IndustriConnect` |
| Pinned commit | `aa634a12ece8186b3e6c775cea1917ea89418f5e` |
| New catalog packs | 10 (`industriconnect-{protocol}-v1`) |
| MCP tools imported | 130 (1 prompt excluded) |
| Industrial Lab services | 10 + 4 templates |

---

## Files Added / Modified

### Added — Excalibur provider
- `morgana/excalibur/ot/industriconnect/` — 10 pack JSONs, source inventory,
  conversion report, validation report, README.
- `morgana/excalibur/ot/industriconnect/runtime/morgana_mcp_stdio_runner.py`
  — generic MCP stdio runner package asset (byte-identical with Morgana server copy).

### Added — Industrial Lab catalog
- `morgana/industrial-lab/` — `catalog.json`, `full-catalog.json`,
  `industriconnect-lab-service-inventory.json`, README,
  `providers/industriconnect/{provider.json,services/*.json,templates/*.json}`.

### Added — Tooling
- `morgana/excalibur/tools/convert_industriconnect.py` — MCP tool discovery + pack generation.
- `morgana/excalibur/tools/generate_industrial_lab.py` — lab catalog generation.
- `morgana/excalibur/tools/validate_industriconnect_packs.py` — static validation.
- `morgana/excalibur/tools/update-industriconnect.ps1` — pinned-source update pipeline.

### Modified
- `morgana/excalibur/catalog.json` — 10 new IndustriConnect pack entries (additive-only, +724 lines).
- `CHANGELOG.md` — IndustriConnect + Industrial Lab release notes.

---

## Validation

- 130/130 Scripts pass static validation (schema, asset refs, tag declarations, Python compiles after substitution).
- Pack asset SHA256 verified against the shipped runner (`4281af32…`).
- Catalog valid JSON; 323 total packs, 10 IndustriConnect.

## Known Limitations

- Upstream Modbus mock device requires an older `pymodbus` (incompatible with 3.15).
- EtherCAT/PROFINET mocks are JSON-over-TCP bridges, not raw-frame emulators.
