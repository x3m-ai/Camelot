#!/usr/bin/env python3
"""Statically validate all LOTL packs and optionally smoke-import representative packs."""

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

LOTL_DIR = Path(__file__).resolve().parent.parent / "lotl"
CATALOG_FILE = Path(__file__).resolve().parent.parent / "catalog.json"
DEFAULT_URL = "https://localhost:8888/api/v2/scripts/import-package"
DEFAULT_KEY_FILE = Path(r"C:\ProgramData\Morgana\data\master.key")
VALID_EXECUTORS = {"powershell", "cmd", "bash", "python"}
VALID_PLATFORMS = {"windows", "linux"}
VALID_RISKS = {"observe", "interact", "modify", "disrupt"}
VALID_READINESS = {"ready", "ready_with_parameters", "environment_prerequisite", "interactive", "manual_counterpart_required"}
PLACEHOLDER = re.compile(r"#\{([^{}]+)\}")
URL_HOST = re.compile(r"https?://(?P<host>(?!#\{)[a-z0-9.-]+)(?::\d+)?", re.I)
IPV4 = re.compile(r"(?<![\w.])(?:\d{1,3}\.){3}\d{1,3}(?![\w.])")


def package_paths(provider: str | None = None) -> list[Path]:
    roots = [LOTL_DIR / provider] if provider else [LOTL_DIR / "lolbas", LOTL_DIR / "gtfobins"]
    return sorted(path for root in roots for path in root.glob("*.json"))


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: root must be an object")
    return value


def validate_package(package: dict[str, Any], path: Path) -> list[str]:
    errors: list[str] = []
    provider = package.get("provider")
    prefix = "LOLBAS - " if provider == "lolbas" else "GTFOBINS - " if provider == "gtfobins" else ""
    if not prefix:
        errors.append("invalid provider")
    if package.get("category") != f"lotl/{provider}":
        errors.append("invalid category")
    scripts = package.get("scripts")
    if not isinstance(scripts, list) or not scripts:
        return errors + ["scripts must be non-empty"]
    if package.get("chains") != []:
        errors.append("bulk LOTL pack must not generate convenience Chains")
    if len(scripts) > 500:
        errors.append("pack exceeds 500 scripts")
    names: set[str] = set()
    ids: set[str] = set()
    tag_keys = {
        tag.get("key") for category in package.get("tag_categories") or []
        for tag in category.get("tags") or [] if isinstance(tag, dict)
    }
    for index, script in enumerate(scripts):
        name = str(script.get("name") or "")
        source_id = str(script.get("id") or "")
        metadata = script.get("source_metadata") or {}
        if not name.startswith(prefix): errors.append(f"script {index}: invalid prefix")
        if name in names: errors.append(f"script {index}: duplicate name")
        if source_id in ids: errors.append(f"script {index}: duplicate source identity")
        names.add(name); ids.add(source_id)
        if script.get("platform") not in VALID_PLATFORMS: errors.append(f"script {index}: invalid platform")
        if script.get("executor") not in VALID_EXECUTORS: errors.append(f"script {index}: invalid executor")
        if script.get("operational_risk") not in VALID_RISKS: errors.append(f"script {index}: invalid risk")
        if metadata.get("readiness") not in VALID_READINESS: errors.append(f"script {index}: invalid readiness")
        if metadata.get("provider") != provider or not metadata.get("source_file"): errors.append(f"script {index}: incomplete provenance")
        command = str(script.get("command") or "")
        if not command.strip(): errors.append(f"script {index}: blank command")
        external_hosts = [
            match.group("host") for match in URL_HOST.finditer(command)
            if match.group("host").lower() != "localhost"
            and not match.group("host").startswith("127.")
            and match.group("host") != "0.0.0.0"
        ]
        if external_hosts: errors.append(f"script {index}: literal external URL host: {external_hosts}")
        external_ips = [
            value for value in IPV4.findall(command)
            if not value.startswith("127.") and value != "0.0.0.0"
        ]
        if external_ips: errors.append(f"script {index}: literal non-loopback IP: {external_ips}")
        required = set(script.get("required_tags") or [])
        placeholders = set(PLACEHOLDER.findall(command + "\n" + str(script.get("cleanup_command") or "")))
        if required != placeholders: errors.append(f"script {index}: placeholder mismatch")
        if not required.issubset(tag_keys): errors.append(f"script {index}: undefined tags")
    if package.get("script_count") not in {None, len(scripts)}:
        errors.append("package script_count mismatch")
    expected_file = f"{package.get('package_id')}.json"
    if path.name != expected_file:
        errors.append("filename does not match package_id")
    return errors


def get_key(url: str) -> str:
    configured = os.environ.get("MORGANA_API_KEY", "").strip()
    if configured: return configured
    if (urllib.parse.urlparse(url).hostname or "").lower() not in {"localhost", "127.0.0.1", "::1"}:
        raise ValueError("refusing to send local key to non-loopback URL")
    return DEFAULT_KEY_FILE.read_text(encoding="utf-8").strip()


def import_package(path: Path, url: str, key: str) -> bool:
    package = read_json(path)
    request = urllib.request.Request(url, data=json.dumps(package).encode(), method="POST", headers={"KEY": key, "Content-Type": "application/json"})
    context = ssl.create_default_context(); context.check_hostname = False; context.verify_mode = ssl.CERT_NONE
    try:
        with urllib.request.urlopen(request, context=context, timeout=120) as response:
            result = json.loads(response.read().decode())
    except urllib.error.HTTPError as exc:
        print(f"[FAIL] {path.name}: HTTP {exc.code} {exc.read().decode(errors='replace')[:500]}")
        return False
    print(f"[OK] {path.name}: imported={result.get('imported', 0)} chains={result.get('chains_imported', 0)} errors={len(result.get('errors', []))}")
    return bool(result.get("success"))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--provider", choices=("lolbas", "gtfobins"))
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--validate-only", action="store_true")
    parser.add_argument("--pack")
    parser.add_argument("--url", default=DEFAULT_URL)
    args = parser.parse_args()
    paths = package_paths(args.provider)
    if args.pack:
        paths = [path for path in paths if path.stem == args.pack or path.name == args.pack]
    elif not args.all:
        paths = [min(paths, key=lambda path: len(read_json(path).get("scripts", [])))] if paths else []
    if not paths:
        print("[ERROR] No LOTL packages selected")
        return 1
    failures = 0
    catalog = read_json(CATALOG_FILE)
    catalog_entries = {entry.get("package_id"): entry for entry in catalog.get("packs", [])}
    for path in paths:
        package = read_json(path)
        errors = validate_package(package, path)
        entry = catalog_entries.get(package.get("package_id"))
        if not entry:
            errors.append("catalog entry missing")
        elif entry.get("script_count") != len(package["scripts"]):
            errors.append("catalog script_count mismatch")
        if errors:
            failures += 1
            print(f"[FAIL] {path.name}: {len(errors)} errors")
            for error in errors[:20]: print(f"  - {error}")
        else:
            print(f"[OK] {path.name}: scripts={len(package['scripts'])} provider={package['provider']}")
    if failures or args.validate_only:
        return 1 if failures else 0
    key = get_key(args.url)
    return 1 if any(not import_package(path, args.url, key) for path in paths) else 0


if __name__ == "__main__":
    raise SystemExit(main())