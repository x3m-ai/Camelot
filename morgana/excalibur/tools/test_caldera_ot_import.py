#!/usr/bin/env python3
"""Statically validate and optionally import generated CALDERA OT packs."""

from __future__ import annotations

import argparse
import hashlib
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

OT_DIR = Path(__file__).resolve().parent.parent / "ot"
DEFAULT_URL = "https://localhost:8888/api/v2/scripts/import-package"
DEFAULT_KEY_FILE = Path(r"C:\ProgramData\Morgana\data\master.key")
VALID_EXECUTORS = {"powershell", "cmd", "bash", "python"}
VALID_PLATFORMS = {"windows", "linux", "macos"}
VALID_RISKS = {"observe", "interact", "modify", "disrupt"}
FACT_PLACEHOLDER = re.compile(r"#\{([^{}]+)\}")
ASSET_PLACEHOLDER = re.compile(r"\{\{asset:([a-z0-9_]+)\}\}")
SAFE_FILENAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
TRUSTED_ASSET_PREFIX = "https://raw.githubusercontent.com/x3m-ai/Camelot/"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_pack(path: Path) -> dict[str, Any]:
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"{path}: invalid JSON: {exc}") from exc
    if not isinstance(loaded, dict):
        raise ValueError(f"{path}: pack root must be an object")
    return loaded


def validate_pack(pack: dict[str, Any], path: Path | None = None) -> list[str]:
    errors: list[str] = []
    prefix = str(pack.get("script_prefix") or "")
    if not prefix:
        errors.append("missing package script_prefix")
    if pack.get("mitre_domain") != "ics-attack":
        errors.append("mitre_domain must be ics-attack")
    assets = {
        asset.get("id"): asset for asset in pack.get("assets", [])
        if isinstance(asset, dict) and asset.get("id")
    }
    for identifier, asset in assets.items():
        filename = str(asset.get("filename") or "")
        if not SAFE_FILENAME.fullmatch(filename):
            errors.append(f"asset {identifier}: unsafe filename")
        if not str(asset.get("url") or "").startswith(TRUSTED_ASSET_PREFIX):
            errors.append(f"asset {identifier}: URL is not controlled Camelot HTTPS")
        if not re.fullmatch(r"[0-9a-f]{64}", str(asset.get("sha256") or "")):
            errors.append(f"asset {identifier}: invalid SHA256")
        for field_name in ("platform", "architecture", "source_repository", "source_commit", "license"):
            if not asset.get(field_name):
                errors.append(f"asset {identifier}: missing {field_name}")
        if asset.get("executable") is not True:
            errors.append(f"asset {identifier}: executable must be true")
        if asset.get("review_status") != "reviewed-local-pinned":
            errors.append(f"asset {identifier}: invalid review status")
        if path:
            local = path.parent / "assets" / filename
            if not local.is_file():
                errors.append(f"asset {identifier}: local published file is missing")
            else:
                if local.stat().st_size != asset.get("size"):
                    errors.append(f"asset {identifier}: local size does not match metadata")
                if sha256_file(local) != asset.get("sha256"):
                    errors.append(f"asset {identifier}: local SHA256 does not match metadata")

    tags = {
        tag.get("key"): tag
        for category in pack.get("tag_categories", [])
        if isinstance(category, dict)
        for tag in category.get("tags", [])
        if isinstance(tag, dict) and tag.get("key")
    }
    names: set[str] = set()
    for index, script in enumerate(pack.get("scripts", [])):
        if not isinstance(script, dict):
            errors.append(f"script {index}: not an object")
            continue
        name = str(script.get("name") or "")
        if not name.startswith(prefix):
            errors.append(f"script {index}: does not match declared prefix")
        if name in names:
            errors.append(f"script {index}: duplicate name")
        names.add(name)
        if script.get("mitre_domain") != "ics-attack":
            errors.append(f"script {index}: invalid domain")
        if script.get("executor") not in VALID_EXECUTORS:
            errors.append(f"script {index}: invalid executor")
        if script.get("platform") not in VALID_PLATFORMS:
            errors.append(f"script {index}: invalid platform")
        if script.get("operational_risk") not in VALID_RISKS:
            errors.append(f"script {index}: invalid risk")
        if not script.get("source_metadata"):
            errors.append(f"script {index}: missing source metadata")
        required_tags = set(script.get("required_tags", []))
        placeholders = set(
            FACT_PLACEHOLDER.findall(
                f"{script.get('command') or ''}\n{script.get('cleanup_command') or ''}"
            )
        )
        if required_tags != placeholders or required_tags - set(tags):
            errors.append(f"script {index}: tag references are inconsistent")
        required_assets = set(script.get("required_assets", []))
        asset_placeholders = set(ASSET_PLACEHOLDER.findall(str(script.get("command") or "")))
        if required_assets != asset_placeholders or required_assets - set(assets):
            errors.append(f"script {index}: asset references are inconsistent")
    for key, tag in tags.items():
        if tag.get("default") or tag.get("example"):
            errors.append(f"tag {key}: public OT defaults are forbidden")
        if tag.get("parameter_class") not in {"connection", "read", "process_write", "control"}:
            errors.append(f"tag {key}: invalid parameter_class")
    for index, chain in enumerate(pack.get("chains", [])):
        refs = chain.get("script_refs", []) if isinstance(chain, dict) else []
        if len(refs) != 1:
            errors.append(f"chain {index}: OT chains must be one-step")
        if any(ref not in names for ref in refs):
            errors.append(f"chain {index}: unresolved script reference")
    return errors


def available_packs() -> list[Path]:
    return sorted(OT_DIR.glob("*/ot-*-v1.json"))


def select_packs(arguments: argparse.Namespace) -> list[Path]:
    available = available_packs()
    if not available:
        raise ValueError(f"no OT packs found under {OT_DIR}")
    if arguments.pack:
        requested = arguments.pack if arguments.pack.endswith(".json") else f"{arguments.pack}.json"
        matches = [path for path in available if path.name == requested]
        if not matches:
            raise ValueError(f"pack not found: {arguments.pack}")
        return matches
    if arguments.protocol:
        matches = [path for path in available if path.parent.name == arguments.protocol]
        if not matches:
            raise ValueError(f"no packs found for protocol: {arguments.protocol}")
        return matches
    if arguments.all or arguments.list:
        return available
    observe = [
        path for path in available
        if all(script.get("operational_risk") == "observe" for script in read_pack(path).get("scripts", []))
    ]
    candidates = observe or available
    return [min(candidates, key=lambda path: (len(read_pack(path).get("scripts", [])), path.name))]


def get_api_key(url: str) -> str:
    configured = os.environ.get("MORGANA_API_KEY", "").strip()
    if configured:
        return configured
    host = (urllib.parse.urlparse(url).hostname or "").lower()
    if host not in {"localhost", "127.0.0.1", "::1"}:
        raise ValueError("refusing to send the local Morgana master key to a non-loopback URL")
    try:
        return DEFAULT_KEY_FILE.read_text(encoding="utf-8").strip()
    except OSError as exc:
        raise ValueError("Morgana API key unavailable; set MORGANA_API_KEY or use loopback") from exc


def ssl_context(url: str) -> ssl.SSLContext:
    context = ssl.create_default_context()
    if (urllib.parse.urlparse(url).hostname or "").lower() in {"localhost", "127.0.0.1", "::1"}:
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
    return context


def import_pack(path: Path, url: str, api_key: str) -> bool:
    pack = read_pack(path)
    errors = validate_pack(pack, path)
    if errors:
        print(f"[FAIL] {path.name}: {len(errors)} validation errors")
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
    except (urllib.error.URLError, json.JSONDecodeError) as exc:
        print(f"[FAIL] {path.name}: {exc}")
        return False
    print(f"[OK] {path.name}: imported={result.get('imported', 0)} chains={result.get('chains_imported', 0)}")
    return bool(result.get("success"))


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate or import MITRE CALDERA OT packs")
    parser.add_argument("--list", action="store_true", help="List and validate all matching packs")
    parser.add_argument("--pack", help="Pack ID or filename")
    parser.add_argument("--protocol", choices=["bacnet", "dnp3", "modbus", "profinet", "iec61850", "gems"])
    parser.add_argument("--all", action="store_true", help="Select all OT packs")
    parser.add_argument("--url", default=DEFAULT_URL, help="Morgana import-package endpoint")
    parser.add_argument("--validate-only", action="store_true", help="Do not import selected packs")
    arguments = parser.parse_args()
    try:
        packs = select_packs(arguments)
        if arguments.list or arguments.validate_only:
            invalid = 0
            for path in packs:
                pack = read_pack(path)
                errors = validate_pack(pack, path)
                status = "OK" if not errors else f"FAIL ({len(errors)})"
                print(f"[{status}] {path.parent.name}/{path.name} scripts={len(pack.get('scripts', []))} assets={len(pack.get('assets', []))}")
                for error in errors[:20]:
                    print(f"  - {error}")
                invalid += bool(errors)
            return 1 if invalid else 0
        api_key = get_api_key(arguments.url)
        failed = sum(not import_pack(path, arguments.url, api_key) for path in packs)
        return 1 if failed else 0
    except ValueError as exc:
        print(f"[ERROR] {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())