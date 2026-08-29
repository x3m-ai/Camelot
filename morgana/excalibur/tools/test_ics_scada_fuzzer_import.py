#!/usr/bin/env python3
"""Validate and optionally import ICS-SCADA-Fuzzer packages without executing them."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import ssl
import subprocess
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent / "ot" / "fuzzing" / "ics-scada-fuzzer"
CATALOG_FILE = Path(__file__).resolve().parent.parent / "catalog.json"
DEFAULT_URL = "https://localhost:8888/api/v2/scripts/import-package"
DEFAULT_KEY_FILE = Path(r"C:\ProgramData\Morgana\data\master.key")
PROTOCOLS = {"modbus", "dnp3", "s7", "iec104", "opcua"}
STRATEGIES = {"random", "bitflip", "overflow", "dictionary", "format", "type", "time", "sequence"}
RISKS = {"interact", "modify", "disrupt"}
PLACEHOLDER = re.compile(r"#\{([^{}]+)\}")
ASSET = re.compile(r"\{\{asset:([a-z0-9_]+)\}\}")


def read(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict): raise ValueError(f"{path}: root must be object")
    return value


def paths() -> list[Path]:
    return sorted(path for protocol in PROTOCOLS for path in (ROOT / protocol).glob("*.json"))


def bash_syntax(command: str) -> str | None:
    candidates = [Path(r"C:\Program Files\Git\bin\bash.exe"), Path(r"C:\Program Files\Git\usr\bin\bash.exe")]
    bash = next((path for path in candidates if path.is_file()), None)
    if not bash: return None
    completed = subprocess.run([str(bash), "-n"], input=command, text=True, capture_output=True, check=False)
    return completed.stderr.strip() if completed.returncode else None


def validate(package: dict[str, Any], path: Path) -> list[str]:
    errors: list[str] = []
    if package.get("provider") != "ics-scada-fuzzer": errors.append("invalid provider")
    if package.get("category") != "ot/fuzzing/ics-scada-fuzzer": errors.append("invalid category")
    if package.get("platform") != ["linux"]: errors.append("invalid platform")
    if package.get("mitre_domain") != "ics-attack": errors.append("invalid ATT&CK domain")
    if package.get("source_attack_version") != "ICS v13": errors.append("invalid ATT&CK source version")
    if package.get("chains") != []: errors.append("fuzz packages must not generate one-step Chains")
    if len(package.get("scripts") or []) != 24: errors.append("protocol package must contain 24 profiles")
    protocol = package.get("protocol")
    if protocol not in PROTOCOLS: errors.append("invalid protocol")
    assets = {asset.get("id"): asset for asset in package.get("assets") or []}
    if len(assets) != 2: errors.append("package must contain binary and seed assets")
    for asset_id, asset in assets.items():
        if not str(asset.get("url") or "").startswith("https://"): errors.append(f"asset {asset_id}: non-HTTPS URL")
        if not re.fullmatch(r"[a-f0-9]{64}", str(asset.get("sha256") or "")): errors.append(f"asset {asset_id}: invalid SHA256")
        publication_name = str(asset.get("url") or "").rsplit("/", 1)[-1]
        local = ROOT / "assets" / publication_name
        if not local.is_file(): errors.append(f"asset {asset_id}: local publication missing")
        elif hashlib.sha256(local.read_bytes()).hexdigest() != asset.get("sha256"): errors.append(f"asset {asset_id}: local hash mismatch")
    tag_keys = {tag.get("key") for category in package.get("tag_categories") or [] for tag in category.get("tags") or []}
    names: set[str] = set(); identities: set[str] = set()
    mode_counts: dict[str, int] = {"generated": 0, "replay": 0}
    stateful_count = 0
    for index, script in enumerate(package.get("scripts") or []):
        metadata = script.get("source_metadata") or {}
        name = str(script.get("name") or ""); identity = str(script.get("id") or "")
        if not name.startswith("ICS FUZZ"): errors.append(f"script {index}: invalid prefix")
        if name in names or identity in identities: errors.append(f"script {index}: duplicate identity")
        names.add(name); identities.add(identity)
        if script.get("executor") != "bash" or script.get("platform") != "linux": errors.append(f"script {index}: invalid runtime")
        if metadata.get("protocol") != protocol: errors.append(f"script {index}: protocol mismatch")
        if metadata.get("strategy") not in STRATEGIES: errors.append(f"script {index}: invalid strategy")
        if metadata.get("mode") not in mode_counts: errors.append(f"script {index}: invalid mode")
        else: mode_counts[metadata["mode"]] += 1
        stateful_count += metadata.get("stateful") is True
        if metadata.get("generator_type") != "protocol-fuzzer" or metadata.get("source_modified") is not False: errors.append(f"script {index}: invalid provenance")
        if script.get("operational_risk") not in RISKS: errors.append(f"script {index}: invalid risk")
        command = str(script.get("command") or "")
        required = set(script.get("required_tags") or []); placeholders = set(PLACEHOLDER.findall(command + json.dumps(script.get("executor_config") or {})))
        if required != placeholders: errors.append(f"script {index}: Tag mismatch")
        if not required.issubset(tag_keys): errors.append(f"script {index}: undefined Tags")
        asset_refs = set(script.get("required_assets") or []); command_assets = set(ASSET.findall(command))
        if asset_refs != command_assets or not asset_refs.issubset(assets): errors.append(f"script {index}: asset mismatch")
        if "MORGANA_RESULT_METADATA=" not in command: errors.append(f"script {index}: structured result marker missing")
        syntax_error = bash_syntax(command)
        if syntax_error: errors.append(f"script {index}: Bash syntax: {syntax_error}")
    if mode_counts != {"generated": 16, "replay": 8}: errors.append(f"mode counts invalid: {mode_counts}")
    if stateful_count != 8: errors.append(f"stateful count invalid: {stateful_count}")
    if path.name != f"{package.get('package_id')}.json": errors.append("filename/package ID mismatch")
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
    parser.add_argument("--protocol", choices=sorted(PROTOCOLS))
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--validate-only", action="store_true")
    parser.add_argument("--url", default=DEFAULT_URL)
    args = parser.parse_args()
    selected = [path for path in paths() if not args.protocol or path.parent.name == args.protocol]
    if not args.all and not args.protocol: selected = selected[:1]
    catalog = read(CATALOG_FILE); catalog_entries = {item.get("package_id"): item for item in catalog.get("packs", [])}
    failures = 0
    for path in selected:
        package = read(path); errors = validate(package, path); entry = catalog_entries.get(package.get("package_id"))
        if not entry: errors.append("catalog entry missing")
        elif entry.get("script_count") != len(package["scripts"]): errors.append("catalog count mismatch")
        if errors:
            failures += 1; print(f"[FAIL] {path.name}: {len(errors)} errors")
            for error in errors[:20]: print(f"  - {error}")
        else: print(f"[OK] {path.name}: protocol={package['protocol']} scripts={len(package['scripts'])}")
    if failures or args.validate_only: return 1 if failures else 0
    key = get_key(args.url)
    return 1 if any(not import_pack(path, args.url, key) for path in selected) else 0


if __name__ == "__main__":
    raise SystemExit(main())