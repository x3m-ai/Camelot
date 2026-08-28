#!/usr/bin/env python3
"""Validate every LOLDrivers pack and optionally smoke-import representative packs."""

from __future__ import annotations

import argparse
import json
import os
import re
import ssl
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "loldrivers"
CATALOG_FILE = Path(__file__).resolve().parent.parent / "catalog.json"
DEFAULT_URL = "https://localhost:8888/api/v2/scripts/import-package"
DEFAULT_KEY_FILE = Path(r"C:\ProgramData\Morgana\data\master.key")
VALID_FAMILIES = {
    "hash_presence", "filename_presence", "loaded_driver_inventory", "driver_service_inventory",
    "event_code_integrity", "event_sysmon_driver_load", "event_service_control_manager", "event_defender",
    "blocklist_validation", "cve_exposure", "signer_publisher_hunt", "source_command_simulation",
}
VALID_READINESS = {"ready", "ready_with_parameters", "environment_prerequisite", "benign_driver_required", "manual_validation"}
PLACEHOLDER = re.compile(r"#\{([^{}]+)\}")


def paths(category: str | None = None) -> list[Path]:
    roots = [OUTPUT_DIR / category] if category else [OUTPUT_DIR / "vulnerable", OUTPUT_DIR / "malicious", OUTPUT_DIR / "detection"]
    return sorted(path for root in roots for path in root.glob("*.json"))


def read(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict): raise ValueError(f"{path}: root must be object")
    return value


def validate(package: dict[str, Any], path: Path) -> list[str]:
    errors: list[str] = []
    if package.get("provider") != "loldrivers": errors.append("invalid provider")
    if package.get("category") not in {"drivers/vulnerable", "drivers/malicious", "drivers/hunting", "drivers/blocklist"}: errors.append("invalid category")
    scripts = package.get("scripts")
    if not isinstance(scripts, list) or not scripts: return errors + ["scripts must be non-empty"]
    if len(scripts) > 400: errors.append("pack exceeds 400 scripts")
    if package.get("assets") != []: errors.append("driver assets are forbidden")
    if package.get("chains") != []: errors.append("mass one-step Chains are forbidden")
    if path.name != f"{package.get('package_id')}.json": errors.append("filename/package_id mismatch")
    tag_keys = {tag.get("key") for group in package.get("tag_categories") or [] for tag in group.get("tags") or []}
    names: set[str] = set(); ids: set[str] = set()
    for index, script in enumerate(scripts):
        name = str(script.get("name") or ""); source_id = str(script.get("id") or ""); metadata = script.get("source_metadata") or {}
        if not name.startswith("LOLDRIVERS - "): errors.append(f"script {index}: invalid prefix")
        if name in names: errors.append(f"script {index}: duplicate name")
        if source_id in ids: errors.append(f"script {index}: duplicate id")
        names.add(name); ids.add(source_id)
        if script.get("platform") != "windows" or script.get("executor") != "powershell": errors.append(f"script {index}: invalid runtime")
        if not str(script.get("command") or "").strip(): errors.append(f"script {index}: blank command")
        if script.get("required_assets"): errors.append(f"script {index}: driver asset reference forbidden")
        if metadata.get("provider") != "loldrivers": errors.append(f"script {index}: provider metadata missing")
        if metadata.get("procedure_family") not in VALID_FAMILIES: errors.append(f"script {index}: invalid procedure family")
        if metadata.get("readiness") not in VALID_READINESS: errors.append(f"script {index}: invalid readiness")
        if "Metadata only" not in str(metadata.get("payload_policy")): errors.append(f"script {index}: payload policy missing")
        required = set(script.get("required_tags") or [])
        placeholders = set(PLACEHOLDER.findall(str(script.get("command") or "") + "\n" + str(script.get("cleanup_command") or "")))
        if required != placeholders: errors.append(f"script {index}: placeholder mismatch")
        if not required.issubset(tag_keys): errors.append(f"script {index}: undefined tag")
        command_lower = str(script.get("command") or "").lower()
        if re.search(r"invoke-webrequest|invoke-restmethod|start-bitstransfer|downloadstring|downloadfile|new-object\s+net\.webclient|\bcurl(?:\.exe)?\s|\bwget(?:\.exe)?\s", command_lower):
            errors.append(f"script {index}: network download primitive forbidden")
        if metadata.get("procedure_family") != "source_command_simulation" and re.search(r"\bsc(?:\.exe)?\s+(?:create|start)\b", command_lower): errors.append(f"script {index}: driver load operation outside benign simulation")
        if metadata.get("procedure_family") == "source_command_simulation":
            if "#{loldrivers_benign_driver_path}" not in command_lower or "get-authenticodesignature" not in command_lower:
                errors.append(f"script {index}: benign driver validation missing")
    return errors


def get_key(url: str) -> str:
    configured = os.environ.get("MORGANA_API_KEY", "").strip()
    if configured: return configured
    if (urllib.parse.urlparse(url).hostname or "").lower() not in {"localhost", "127.0.0.1", "::1"}:
        raise ValueError("refusing local key for non-loopback URL")
    return DEFAULT_KEY_FILE.read_text(encoding="utf-8").strip()


def import_pack(path: Path, url: str, key: str) -> bool:
    package = read(path)
    request = urllib.request.Request(url, data=json.dumps(package).encode(), method="POST", headers={"KEY": key, "Content-Type": "application/json"})
    context = ssl.create_default_context(); context.check_hostname = False; context.verify_mode = ssl.CERT_NONE
    try:
        with urllib.request.urlopen(request, context=context, timeout=180) as response: result = json.loads(response.read().decode())
    except urllib.error.HTTPError as exc:
        print(f"[FAIL] {path.name}: HTTP {exc.code} {exc.read().decode(errors='replace')[:500]}"); return False
    print(f"[OK] {path.name}: imported={result.get('imported', 0)} chains={result.get('chains_imported', 0)} errors={len(result.get('errors', []))}")
    return bool(result.get("success"))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--category", choices=("vulnerable", "malicious", "detection"))
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--validate-only", action="store_true")
    parser.add_argument("--pack")
    parser.add_argument("--url", default=DEFAULT_URL)
    args = parser.parse_args()
    selected = paths(args.category)
    if args.pack: selected = [path for path in selected if path.stem == args.pack or path.name == args.pack]
    elif not args.all: selected = [min(selected, key=lambda path: len(read(path).get("scripts", [])))] if selected else []
    if not selected: print("[ERROR] No packages selected"); return 1
    catalog = read(CATALOG_FILE); catalog_entries = {entry.get("package_id"): entry for entry in catalog.get("packs", [])}
    failures = 0
    for path in selected:
        package = read(path); errors = validate(package, path); entry = catalog_entries.get(package.get("package_id"))
        if not entry: errors.append("catalog entry missing")
        elif entry.get("script_count") != len(package["scripts"]): errors.append("catalog count mismatch")
        if errors:
            failures += 1; print(f"[FAIL] {path.name}: {len(errors)} errors")
            for error in errors[:20]: print(f"  - {error}")
        else: print(f"[OK] {path.name}: scripts={len(package['scripts'])} category={package['category']}")
    if failures or args.validate_only: return 1 if failures else 0
    key = get_key(args.url)
    return 1 if any(not import_pack(path, args.url, key) for path in selected) else 0


if __name__ == "__main__":
    raise SystemExit(main())