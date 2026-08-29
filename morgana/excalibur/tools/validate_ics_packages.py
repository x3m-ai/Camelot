#!/usr/bin/env python3
"""Static validator for ICS-SCADA-Fuzzer Excalibur packages."""
from __future__ import annotations

import json
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent / "ot" / "fuzzing" / "ics-scada-fuzzer"
PROTOCOLS = ["modbus", "dnp3", "s7", "iec104", "opcua"]
REQUIRED_STRATEGIES = {"random", "bitflip", "overflow", "dictionary", "format", "type", "time", "sequence"}
REQUIRED_SCRIPT_FIELDS = ["id", "name", "command", "executor_config", "required_assets", "required_tags", "source_metadata", "operational_risk"]
REQUIRED_META_FIELDS = ["provider", "protocol", "strategy", "stateful", "mode", "generator_type", "source_modified"]

errors: list[str] = []
total_scripts = 0
strategy_counts: dict[str, int] = {}
mode_counts: dict[str, int] = {"generated": 0, "replay": 0}
stateful_counts: dict[str, int] = {"stateful": 0, "stateless": 0}

for proto in PROTOCOLS:
    pkg_dir = BASE / proto
    pkg_files = list(pkg_dir.glob("*.json"))
    if not pkg_files:
        errors.append(f"MISSING package dir/file for {proto}")
        continue
    pkg = json.loads(pkg_files[0].read_text(encoding="utf-8"))
    scripts = pkg.get("scripts", [])
    total_scripts += len(scripts)
    if len(scripts) != 24:
        errors.append(f"{proto}: expected 24 scripts, got {len(scripts)}")
    # package-level mitre_domain
    if pkg.get("mitre_domain") != "ics-attack":
        errors.append(f"{proto}: package missing mitre_domain=ics-attack (got {pkg.get('mitre_domain')!r})")
    seen_ids: set[str] = set()
    for s in scripts:
        sid = s.get("id", "?")
        if sid in seen_ids:
            errors.append(f"{proto}: duplicate id {sid}")
        seen_ids.add(sid)
        for field in REQUIRED_SCRIPT_FIELDS:
            if field not in s:
                errors.append(f"{proto}:{sid} missing field {field}")
        meta = s.get("source_metadata", {})
        for mf in REQUIRED_META_FIELDS:
            if mf not in meta:
                errors.append(f"{proto}:{sid} source_metadata missing {mf}")
        strategy = meta.get("strategy", "")
        strategy_counts[strategy] = strategy_counts.get(strategy, 0) + 1
        mode = meta.get("mode", "")
        if mode in mode_counts:
            mode_counts[mode] += 1
        else:
            errors.append(f"{proto}:{sid} unexpected mode {mode!r}")
        is_stateful = meta.get("stateful", None)
        if mode == "generated":
            if is_stateful is True:
                stateful_counts["stateful"] += 1
            elif is_stateful is False:
                stateful_counts["stateless"] += 1
        cmd = s.get("command", "")
        if "MORGANA_RESULT_METADATA=" not in cmd:
            errors.append(f"{proto}:{sid} missing MORGANA_RESULT_METADATA in command")
        if "ot_fuzz_target" not in cmd:
            errors.append(f"{proto}:{sid} missing ot_fuzz_target in command")
        nm = s.get("name", "")
        if not nm.startswith("ICS FUZZ"):
            errors.append(f"{proto}:{sid} bad name prefix: {nm!r}")
        platform = s.get("platform") or pkg.get("platform", [])
        if isinstance(platform, list):
            if platform != ["linux"]:
                errors.append(f"{proto}:{sid} bad platform: {platform}")
        elif platform != "linux":
            errors.append(f"{proto}:{sid} bad platform: {platform}")
        ec = s.get("executor_config", {})
        ts = str(ec.get("timeout_seconds", ""))
        if "#{ot_fuzz_timeout}" not in ts:
            errors.append(f"{proto}:{sid} executor_config.timeout_seconds not a tag ref: {ts!r}")
        # Check required_tags contains ot_fuzz_target
        req_tags = s.get("required_tags", [])
        tag_keys = {t.get("key", t) if isinstance(t, dict) else t for t in req_tags}
        if "ot_fuzz_target" not in tag_keys:
            errors.append(f"{proto}:{sid} required_tags missing ot_fuzz_target")
        # mitre_domain at the package level (already verified per-package below)

print(f"total_scripts={total_scripts}")
print(f"mode_counts={mode_counts}")
print(f"stateful_counts={stateful_counts}")
print(f"strategy_counts={strategy_counts}")
missing_strategies = REQUIRED_STRATEGIES - set(strategy_counts.keys())
if missing_strategies:
    errors.append(f"Missing strategies: {missing_strategies}")

# Validate catalog entry
catalog_path = BASE.parent.parent.parent / "catalog.json"
if catalog_path.exists():
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    ics_entries = [e for e in catalog.get("packs", []) if "ics-scada-fuzzer" in e.get("package_id", "")]
    print(f"catalog_ics_entries={len(ics_entries)}")
    if len(ics_entries) != 5:
        errors.append(f"catalog: expected 5 ICS entries, got {len(ics_entries)}")
else:
    errors.append("catalog.json not found")

# Validate source-inventory
inv_path = BASE / "source-inventory.json"
if inv_path.exists():
    inv = json.loads(inv_path.read_text(encoding="utf-8"))
    if isinstance(inv, list):
        inv_count = len(inv)
    else:
        inv_count = inv.get("total_scripts", 0)
    print(f"source_inventory_entries={inv_count}")
else:
    errors.append("source-inventory.json not found")

# Validate conversion-report
rpt_path = BASE / "conversion-report.json"
if rpt_path.exists():
    rpt = json.loads(rpt_path.read_text(encoding="utf-8"))
    # Check per-package mitre_domain
    if not rpt.get("source_reconciled"):
        errors.append("conversion-report: source_reconciled is not true")
    if rpt.get("total_scripts", 0) != 120:
        errors.append(f"conversion-report: total_scripts={rpt.get('total_scripts')}, expected 120")
    print(f"conversion_report_total_scripts={rpt.get('total_scripts')}")
else:
    errors.append("conversion-report.json not found")

# Validate build-manifest
bm_path = BASE / "build-manifest.json"
if bm_path.exists():
    bm = json.loads(bm_path.read_text(encoding="utf-8"))
    if not bm.get("binary_sha256"):
        errors.append("build-manifest: missing binary_sha256")
    if bm.get("source_modified") is not False:
        errors.append("build-manifest: source_modified is not false")
    print(f"build_manifest_sha256={bm.get('binary_sha256')}")
    print(f"build_manifest_source_commit={bm.get('source_commit')}")
else:
    errors.append("build-manifest.json not found")

# Verify binary exists
bin_path = BASE / "assets" / "ics-fuzzer-linux-amd64"
if bin_path.exists():
    import hashlib
    actual_sha = hashlib.sha256(bin_path.read_bytes()).hexdigest()
    bm_sha = bm.get("binary_sha256", "") if bm_path.exists() else ""
    if bm_sha and actual_sha != bm_sha:
        errors.append(f"binary SHA256 mismatch: manifest={bm_sha} actual={actual_sha}")
    else:
        print(f"binary_sha256_verified={actual_sha}")
else:
    errors.append("binary ics-fuzzer-linux-amd64 not found in assets/")

if errors:
    print(f"\nFAILED with {len(errors)} error(s):")
    for e in errors:
        print(f"  ERROR: {e}")
    sys.exit(1)
else:
    print(f"\nSTATIC VALIDATION: PASS - {total_scripts} scripts, 5 packages, catalog verified, binary hash verified")
