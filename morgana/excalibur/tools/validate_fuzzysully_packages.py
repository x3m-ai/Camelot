#!/usr/bin/env python3
"""Static validator for ANSSI FuzzySully Excalibur packages."""
from __future__ import annotations

import json
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent / "ot" / "fuzzing" / "fuzzysully"
PACKAGE_DIRS = ["server-none", "server-basic256sha256", "gds", "reverse"]
EXPECTED_COUNTS = {
    "server-none": 20,
    "server-basic256sha256": 34,
    "gds": 18,
    "reverse": 1,
}
REQUIRED_SCRIPT_FIELDS = ["id", "name", "command", "executor_config", "required_assets",
                           "required_tags", "source_metadata", "operational_risk"]
REQUIRED_META_FIELDS = ["provider", "mode", "function", "security_policy", "generator_type",
                        "protocol", "mitre_domain", "source_modified"]
VALID_RISKS = {"observe", "interact", "modify", "disrupt"}

errors: list[str] = []
total_scripts = 0
total_packages = 0

for pkg_dir_name in PACKAGE_DIRS:
    pkg_dir = BASE / pkg_dir_name
    pkg_files = list(pkg_dir.glob("*.json"))
    if not pkg_files:
        errors.append(f"MISSING package file in {pkg_dir_name}/")
        continue
    pkg = json.loads(pkg_files[0].read_text(encoding="utf-8"))
    scripts = pkg.get("scripts", [])
    total_scripts += len(scripts)
    total_packages += 1
    expected = EXPECTED_COUNTS[pkg_dir_name]
    if len(scripts) != expected:
        errors.append(f"{pkg_dir_name}: expected {expected} scripts, got {len(scripts)}")

    if pkg.get("mitre_domain") != "ics-attack":
        errors.append(f"{pkg_dir_name}: package mitre_domain missing or wrong ({pkg.get('mitre_domain')!r})")

    seen_ids: set[str] = set()
    for s in scripts:
        sid = s.get("id", "?")
        if sid in seen_ids:
            errors.append(f"{pkg_dir_name}: duplicate id {sid}")
        seen_ids.add(sid)

        for field in REQUIRED_SCRIPT_FIELDS:
            if field not in s:
                errors.append(f"{pkg_dir_name}:{sid} missing field {field}")

        meta = s.get("source_metadata", {})
        for mf in REQUIRED_META_FIELDS:
            if mf not in meta:
                errors.append(f"{pkg_dir_name}:{sid} source_metadata missing {mf}")

        if meta.get("mitre_domain") != "ics-attack":
            errors.append(f"{pkg_dir_name}:{sid} source_metadata mitre_domain wrong")

        if meta.get("source_modified") is not False:
            errors.append(f"{pkg_dir_name}:{sid} source_metadata source_modified is not false")

        nm = s.get("name", "")
        if not nm.startswith("FUZZYSULLY"):
            errors.append(f"{pkg_dir_name}:{sid} bad name prefix: {nm!r}")

        platform = s.get("platform") or pkg.get("platform", [])
        if isinstance(platform, list):
            if platform != ["linux"]:
                errors.append(f"{pkg_dir_name}:{sid} bad platform: {platform}")
        elif platform != "linux":
            errors.append(f"{pkg_dir_name}:{sid} bad platform: {platform}")

        cmd = s.get("command", "")
        # MORGANA_RESULT_METADATA= is emitted by morgana_fuzzysully_runner.py to stdout;
        # the bash command invokes the runner which handles result emission.
        if "python3" not in cmd and "morgana_fuzzysully_runner" not in cmd and 'runner' not in cmd:
            errors.append(f"{pkg_dir_name}:{sid} missing runner invocation in command")
        if "opcua_target_host" not in cmd:
            errors.append(f"{pkg_dir_name}:{sid} missing opcua_target_host in command")
        if "python3" not in cmd:
            errors.append(f"{pkg_dir_name}:{sid} missing python3 runner invocation in command")

        risk = s.get("operational_risk", "")
        if risk not in VALID_RISKS:
            errors.append(f"{pkg_dir_name}:{sid} invalid operational_risk: {risk!r}")

        ec = s.get("executor_config", {})
        if "fuzz_max_duration" not in str(ec.get("timeout_seconds", "")):
            errors.append(f"{pkg_dir_name}:{sid} executor_config.timeout_seconds not a tag ref")

        req_tags = s.get("required_tags", [])
        tag_keys = {t.get("key", t) if isinstance(t, dict) else t for t in req_tags}
        if "opcua_target_host" not in tag_keys:
            errors.append(f"{pkg_dir_name}:{sid} required_tags missing opcua_target_host")

        # Basic256Sha256 scripts must require cert
        if meta.get("security_policy") == "Basic256Sha256":
            if "opcua_client_cert_path" not in tag_keys:
                errors.append(f"{pkg_dir_name}:{sid} Basic256Sha256 script missing cert required_tag")
        # No PEM content in script
        if "BEGIN PRIVATE KEY" in cmd or "BEGIN CERTIFICATE" in cmd:
            errors.append(f"{pkg_dir_name}:{sid} PEM content found in command (credential leak)")

# Validate catalog
catalog_path = BASE.parent.parent.parent / "catalog.json"
if catalog_path.exists():
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    packs = catalog.get("packs", [])
    fs_entries = [e for e in packs if "fuzzysully" in e.get("package_id", "")]
    print(f"catalog_fuzzysully_entries={len(fs_entries)}")
    if len(fs_entries) != 4:
        errors.append(f"catalog: expected 4 FuzzySully entries, got {len(fs_entries)}")
else:
    errors.append("catalog.json not found")

# Validate build-manifest
bm_path = BASE / "build-manifest.json"
if bm_path.exists():
    bm = json.loads(bm_path.read_text(encoding="utf-8"))
    if not bm.get("runner_sha256"):
        errors.append("build-manifest: missing runner_sha256")
    if bm.get("source_modified") is not False:
        errors.append("build-manifest: source_modified is not false")
    if not bm.get("source_commit"):
        errors.append("build-manifest: missing source_commit")
    print(f"build_manifest_commit={bm.get('source_commit')}")
    print(f"build_manifest_runner_sha256={bm.get('runner_sha256')}")
else:
    errors.append("build-manifest.json not found")

# Validate runner exists
runner_path = BASE / "morgana_fuzzysully_runner.py"
if not runner_path.exists():
    errors.append("morgana_fuzzysully_runner.py not found")
else:
    import hashlib
    runner_sha = hashlib.sha256(runner_path.read_bytes()).hexdigest()
    print(f"runner_sha256_verified={runner_sha}")

# Validate source-inventory
inv_path = BASE / "source-inventory.json"
if inv_path.exists():
    inv = json.loads(inv_path.read_text(encoding="utf-8"))
    print(f"source_inventory_entries={len(inv)}")
    if len(inv) != total_scripts:
        errors.append(f"source-inventory count {len(inv)} != total_scripts {total_scripts}")
else:
    errors.append("source-inventory.json not found")

# Validate function-inventory
fi_path = BASE / "function-inventory.json"
if not fi_path.exists():
    errors.append("function-inventory.json not found")

# Validate conversion-report
rpt_path = BASE / "conversion-report.json"
if rpt_path.exists():
    rpt = json.loads(rpt_path.read_text(encoding="utf-8"))
    if not rpt.get("source_reconciled"):
        errors.append("conversion-report: source_reconciled is not true")
    if rpt.get("total_scripts", 0) != total_scripts:
        errors.append(f"conversion-report total_scripts={rpt.get('total_scripts')} != {total_scripts}")
    print(f"conversion_report_total_scripts={rpt.get('total_scripts')}")
    print(f"conversion_report_skipped={rpt.get('skipped_profiles')}")
else:
    errors.append("conversion-report.json not found")

print(f"\ntotal_scripts={total_scripts}")
print(f"total_packages={total_packages}")

if errors:
    print(f"\nFAILED with {len(errors)} error(s):")
    for e in errors:
        print(f"  ERROR: {e}")
    sys.exit(1)
else:
    print(f"\nSTATIC VALIDATION: PASS — {total_scripts} scripts, {total_packages} packages, catalog verified, runner verified")
