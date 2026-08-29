#!/usr/bin/env python3
"""Validate all generated Frida mobile packs and optionally smoke-import one."""

from __future__ import annotations

import argparse
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

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "mobile" / "frida"
CATALOG_FILE = Path(__file__).resolve().parent.parent / "catalog.json"
DEFAULT_URL = "https://localhost:8888/api/v2/scripts/import-package"
DEFAULT_KEY_FILE = Path(r"C:\ProgramData\Morgana\data\master.key")
PACKAGE_DIRS = ("android", "ios", "flutter", "react-native", "xamarin", "unity-il2cpp", "universal")
VALID_PLATFORMS = {"android", "ios", "universal-native", "linux-native", "other"}
VALID_SCOPES = {"generic", "library-specific", "framework-specific", "app-specific", "version-specific", "research-snippet"}
VALID_READINESS = {"ready", "ready_with_target", "environment_prerequisite", "framework_prerequisite", "app_specific", "legacy", "manual_review"}
PLACEHOLDER = re.compile(r"#\{([^{}]+)\}")


def paths() -> list[Path]:
    return sorted(path for directory in PACKAGE_DIRS for path in (OUTPUT_DIR / directory).glob("*.json"))


def read(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict): raise ValueError(f"{path}: root must be object")
    return value


def validate(package: dict[str, Any], path: Path, validate_js: bool = False) -> list[str]:
    errors: list[str] = []
    if package.get("provider") != "frida-mobile": errors.append("invalid provider")
    if not str(package.get("category") or "").startswith("mobile/frida/"): errors.append("invalid category")
    scripts = package.get("scripts")
    if not isinstance(scripts, list) or not scripts: return errors + ["scripts must be non-empty"]
    if len(scripts) > 350: errors.append("pack exceeds 350 scripts")
    if path.stat().st_size > 10_000_000: errors.append("pack exceeds 10 MB hard limit")
    if package.get("assets") != [] or package.get("chains") != []: errors.append("bulk Frida package must not contain assets/chains")
    if path.name != f"{package.get('package_id')}.json": errors.append("filename/package mismatch")
    tag_keys = {tag.get("key") for group in package.get("tag_categories") or [] for tag in group.get("tags") or []}
    names: set[str] = set(); ids: set[str] = set()
    with tempfile.TemporaryDirectory(prefix="frida-pack-check-") as temporary:
        for index, script in enumerate(scripts):
            name = str(script.get("name") or ""); source_id = str(script.get("id") or ""); metadata = script.get("source_metadata") or {}; config = script.get("executor_config") or {}
            if not name.startswith("FRIDA - "): errors.append(f"script {index}: invalid prefix")
            if name in names or source_id in ids: errors.append(f"script {index}: duplicate identity")
            names.add(name); ids.add(source_id)
            if script.get("executor") != "frida" or script.get("platform") != "all": errors.append(f"script {index}: invalid executor/host platform")
            if config.get("target") != "#{mobile_app_id}" or config.get("transport") not in {"usb", "remote"} or config.get("mode") not in {"spawn", "attach"}: errors.append(f"script {index}: invalid Frida config")
            code = str(script.get("command") or "")
            if not code.strip(): errors.append(f"script {index}: blank source")
            if re.search(r"```|<!DOCTYPE|<html\b", code, re.I): errors.append(f"script {index}: mixed markup")
            required = set(script.get("required_tags") or []); placeholders = set(PLACEHOLDER.findall(json.dumps(config) + "\n" + code))
            if required != placeholders: errors.append(f"script {index}: placeholder mismatch")
            if not required.issubset(tag_keys): errors.append(f"script {index}: undefined tags")
            if metadata.get("provider") != "frida-mobile" or metadata.get("target_platform") not in VALID_PLATFORMS: errors.append(f"script {index}: incomplete platform provenance")
            if metadata.get("scope") not in VALID_SCOPES or not metadata.get("behaviors") or not metadata.get("frida_apis"): errors.append(f"script {index}: incomplete classification")
            if metadata.get("readiness") not in VALID_READINESS or not metadata.get("source_hash") or not metadata.get("normalized_hash"): errors.append(f"script {index}: incomplete readiness/fingerprint")
            if not metadata.get("license") or not metadata.get("distribution_status"): errors.append(f"script {index}: license metadata missing")
            if validate_js:
                script_path = Path(temporary) / f"{index:04d}.js"; script_path.write_text(code, encoding="utf-8")
                result = subprocess.run(["node", "--check", str(script_path)], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=20)
                if result.returncode: errors.append(f"script {index}: JavaScript syntax invalid")
    return errors


def get_key(url: str) -> str:
    configured = os.environ.get("MORGANA_API_KEY", "").strip()
    if configured: return configured
    if (urllib.parse.urlparse(url).hostname or "").lower() not in {"localhost", "127.0.0.1", "::1"}: raise ValueError("refusing local key for non-loopback URL")
    return DEFAULT_KEY_FILE.read_text(encoding="utf-8").strip()


def import_pack(path: Path, url: str, key: str) -> bool:
    request = urllib.request.Request(url, data=json.dumps(read(path)).encode(), method="POST", headers={"KEY": key, "Content-Type": "application/json"})
    context = ssl.create_default_context(); context.check_hostname = False; context.verify_mode = ssl.CERT_NONE
    try:
        with urllib.request.urlopen(request, context=context, timeout=180) as response: result = json.loads(response.read().decode())
    except urllib.error.HTTPError as exc:
        print(f"[FAIL] {path.name}: HTTP {exc.code} {exc.read().decode(errors='replace')[:500]}"); return False
    print(f"[OK] {path.name}: imported={result.get('imported', 0)} errors={len(result.get('errors', []))}")
    return bool(result.get("success"))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--validate-only", action="store_true")
    parser.add_argument("--validate-js", action="store_true")
    parser.add_argument("--pack")
    parser.add_argument("--url", default=DEFAULT_URL)
    args = parser.parse_args(); selected = paths()
    if args.pack: selected = [path for path in selected if path.stem == args.pack or path.name == args.pack]
    elif not args.all: selected = [min(selected, key=lambda path: len(read(path)["scripts"]))] if selected else []
    if not selected: print("[ERROR] No Frida packages selected"); return 1
    catalog = read(CATALOG_FILE); entries = {entry.get("package_id"): entry for entry in catalog.get("packs", [])}; failures = 0
    for path in selected:
        package = read(path); errors = validate(package, path, args.validate_js); entry = entries.get(package.get("package_id"))
        if not entry: errors.append("catalog entry missing")
        elif entry.get("script_count") != len(package["scripts"]): errors.append("catalog count mismatch")
        if errors:
            failures += 1; print(f"[FAIL] {path.name}: {len(errors)} errors")
            for error in errors[:20]: print(f"  - {error}")
        else: print(f"[OK] {path.name}: scripts={len(package['scripts'])}")
    if failures or args.validate_only: return 1 if failures else 0
    key = get_key(args.url)
    return 1 if any(not import_pack(path, args.url, key) for path in selected) else 0


if __name__ == "__main__": raise SystemExit(main())