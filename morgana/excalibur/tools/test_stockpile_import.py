#!/usr/bin/env python3
"""Validate and optionally import MITRE Stockpile packs into Morgana."""

from __future__ import annotations

import argparse
import json
import os
import re
import ssl
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

STOCKPILE_DIR = Path(__file__).resolve().parent.parent / "stockpile"
DEFAULT_URL = "https://localhost:8888/api/v2/scripts/import-package"
DEFAULT_KEY_FILE = Path(r"C:\ProgramData\Morgana\data\master.key")
SCRIPT_PREFIX = "STOCKPILE - "
VALID_EXECUTORS = {"powershell", "cmd", "bash", "python"}
VALID_PLATFORMS = {"windows", "linux", "macos"}
PLACEHOLDER = re.compile(r"#\{([^{}]+)\}")
SENSITIVE_TERMS = (
    "password", "passwd", "token", "secret", "credential",
    "private_key", "apikey", "api_key", "access_key",
)


def get_api_key(url: str) -> str:
    configured = os.environ.get("MORGANA_API_KEY", "").strip()
    if configured:
        return configured
    parsed = urllib.parse.urlparse(url)
    if (parsed.hostname or "").lower() not in {"localhost", "127.0.0.1", "::1"}:
        print("[ERROR] Refusing to send the local Morgana master key to a non-local URL.")
        print("  Set MORGANA_API_KEY explicitly for an approved remote endpoint.")
        raise SystemExit(1)
    try:
        return DEFAULT_KEY_FILE.read_text(encoding="utf-8").strip()
    except OSError:
        print("[ERROR] Morgana API key unavailable. Set MORGANA_API_KEY or start Morgana locally.")
        raise SystemExit(1)


def validate_pack(pack: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for field_name in ("package_id", "package_name", "version", "scripts", "chains"):
        if not pack.get(field_name):
            errors.append(f"missing top-level field: {field_name}")

    scripts = pack.get("scripts") if isinstance(pack.get("scripts"), list) else []
    names: set[str] = set()
    tags = {
        tag.get("key"): tag
        for category in pack.get("tag_categories") or []
        if isinstance(category, dict)
        for tag in category.get("tags") or []
        if isinstance(tag, dict) and tag.get("key")
    }
    tag_keys = set(tags)
    for index, script in enumerate(scripts):
        if not isinstance(script, dict):
            errors.append(f"script {index}: entry is not an object")
            continue
        name = str(script.get("name") or "")
        if not name.startswith(SCRIPT_PREFIX):
            errors.append(f"script {index}: invalid prefix")
        if name in names:
            errors.append(f"script {index}: duplicate name: {name}")
        names.add(name)
        if not script.get("tcode"):
            errors.append(f"script {index}: missing tcode")
        if script.get("executor") not in VALID_EXECUTORS:
            errors.append(f"script {index}: unsupported executor: {script.get('executor')}")
        if script.get("platform") not in VALID_PLATFORMS:
            errors.append(f"script {index}: unsupported platform: {script.get('platform')}")
        if not str(script.get("command") or "").strip():
            errors.append(f"script {index}: empty command")
        command_text = f"{script.get('command') or ''}\n{script.get('cleanup_command') or ''}".lower()
        forbidden_runtime_markers = [
            marker
            for marker in ("s4ndc4t", "sandcat", "/file/download", "/file/upload")
            if marker in command_text
        ]
        if forbidden_runtime_markers:
            errors.append(
                f"script {index}: forbidden CALDERA runtime markers: {forbidden_runtime_markers}"
            )
        if "scriptleturl" in command_text and re.search(r"https?://", command_text):
            errors.append(f"script {index}: unverified remote ScriptletURL")
        for provenance in (
            "stockpile_id", "source_path", "source_executor", "source_platform"
        ):
            if not script.get(provenance):
                errors.append(f"script {index}: missing provenance field: {provenance}")
        if script.get("source") != "mitre-stockpile":
            errors.append(f"script {index}: invalid source")
        forbidden = {"payload", "payloads", "build_target", "code"}.intersection(script)
        if forbidden:
            errors.append(f"script {index}: forbidden packaged fields: {sorted(forbidden)}")
        required_tags = set(script.get("required_tags") or [])
        missing_tags = required_tags - tag_keys
        if missing_tags:
            errors.append(f"script {index}: undefined required tags: {sorted(missing_tags)}")
        placeholders = set(
            PLACEHOLDER.findall(
                f"{script.get('command') or ''}\n{script.get('cleanup_command') or ''}"
            )
        )
        if placeholders != required_tags:
            errors.append(
                f"script {index}: placeholders do not match required_tags: "
                f"{sorted(placeholders)} != {sorted(required_tags)}"
            )

    for key, tag in tags.items():
        sensitive_name = any(term in key.lower() for term in SENSITIVE_TERMS)
        if sensitive_name and not tag.get("sensitive"):
            errors.append(f"tag {key}: sensitive-looking key is not marked sensitive")
        if tag.get("sensitive") and (tag.get("default") or tag.get("example")):
            errors.append(f"tag {key}: sensitive tag must not contain default/example values")

    for index, chain in enumerate(pack.get("chains") or []):
        if not isinstance(chain, dict):
            errors.append(f"chain {index}: entry is not an object")
            continue
        refs = chain.get("script_refs") or []
        if not refs:
            errors.append(f"chain {index}: missing script_refs")
        if "Full Tactic" in str(chain.get("name") or ""):
            description = str(chain.get("description") or "").lower()
            if "not an authentic" not in description:
                errors.append(f"chain {index}: full-tactic chain lacks sequencing disclaimer")
        for ref in refs:
            if ref not in names:
                errors.append(f"chain {index}: unresolved script_ref: {ref}")
    return errors


def read_pack(path: Path) -> dict[str, Any]:
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"invalid JSON: {exc}") from exc
    if not isinstance(loaded, dict):
        raise ValueError("pack root must be an object")
    return loaded


def ssl_context(url: str) -> ssl.SSLContext:
    context = ssl.create_default_context()
    host = (urllib.parse.urlparse(url).hostname or "").lower()
    if host in {"localhost", "127.0.0.1", "::1"}:
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
    return context


def import_pack(path: Path, url: str, api_key: str) -> bool:
    pack = read_pack(path)
    validation_errors = validate_pack(pack)
    if validation_errors:
        print(f"[FAIL] {path.name}: {len(validation_errors)} static validation errors")
        for error in validation_errors[:10]:
            print(f"  - {error}")
        return False

    request = urllib.request.Request(
        url,
        data=json.dumps(pack).encode("utf-8"),
        method="POST",
        headers={"KEY": api_key, "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, context=ssl_context(url), timeout=120) as response:
            result = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:500]
        print(f"[FAIL] {path.name}: HTTP {exc.code}: {detail}")
        return False
    except Exception as exc:
        print(f"[FAIL] {path.name}: {exc}")
        return False

    print(
        f"[OK] {path.name}: imported={result.get('imported', 0)} "
        f"removed={result.get('removed', 0)} chains={result.get('chains_imported', 0)} "
        f"protected={result.get('skipped_user_modified', 0)} errors={len(result.get('errors', []))}"
    )
    return bool(result.get("success"))


def select_packs(arguments: argparse.Namespace) -> list[Path]:
    available = sorted(STOCKPILE_DIR.glob("stockpile-*-v1.json"))
    if not available:
        print(f"[ERROR] No Stockpile packs found in {STOCKPILE_DIR}")
        raise SystemExit(1)
    if arguments.pack:
        requested = arguments.pack if arguments.pack.endswith(".json") else f"{arguments.pack}.json"
        path = STOCKPILE_DIR / requested
        if not path.exists():
            print(f"[ERROR] Pack not found: {arguments.pack}")
            raise SystemExit(1)
        return [path]
    if arguments.all:
        return available
    small = [path for path in available if len(read_pack(path).get("scripts", [])) <= 150]
    return small[:1] or available[:1]


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate/import Morgana Stockpile packs")
    parser.add_argument("--pack", help="Pack ID or JSON filename")
    parser.add_argument("--all", action="store_true", help="Validate/import all Stockpile packs")
    parser.add_argument("--list", action="store_true", help="List packs and run static validation only")
    parser.add_argument("--validate-only", action="store_true", help="Validate selected packs without importing")
    parser.add_argument("--url", default=DEFAULT_URL, help="Morgana import-package endpoint")
    arguments = parser.parse_args()

    packs = select_packs(arguments)
    invalid = 0
    if arguments.list or arguments.validate_only:
        for path in packs:
            pack = read_pack(path)
            errors = validate_pack(pack)
            status = "OK" if not errors else f"FAIL ({len(errors)})"
            print(
                f"[{status}] {path.name:<38} scripts={len(pack.get('scripts', [])):>4} "
                f"chains={len(pack.get('chains', [])):>4}"
            )
            for error in errors[:10]:
                print(f"  - {error}")
            invalid += int(bool(errors))
        return 1 if invalid else 0

    api_key = get_api_key(arguments.url)
    succeeded = sum(import_pack(path, arguments.url, api_key) for path in packs)
    failed = len(packs) - succeeded
    print(f"[SUMMARY] {succeeded} imported, {failed} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
