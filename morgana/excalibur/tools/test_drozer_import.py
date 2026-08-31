#!/usr/bin/env python3
"""Validate all generated Drozer packages against the Excalibur schema."""

from __future__ import annotations

import json
import re
import sys
import tempfile
from pathlib import Path
from typing import Any

TOOLS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS_DIR))
OUTPUT_DIR = TOOLS_DIR.parent / "mobile" / "drozer"
CATALOG_FILE = TOOLS_DIR.parent / "catalog.json"
PLACEHOLDER = re.compile(r"#\{([^{}]+)\}")
ASSET = re.compile(r"\{\{asset:([a-zA-Z0-9_.-]+)\}\}")

EXPECTED_PACKAGES = 8
EXPECTED_SCRIPTS = 79
VALID_RISK = {"observe", "interact", "modify", "disrupt"}


def read(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: root must be object")
    return value


def paths() -> list[Path]:
    namespaces = ["app", "auxiliary", "exploit", "information", "post", "scanner", "shell", "tools"]
    return sorted(
        path for ns in namespaces for path in (OUTPUT_DIR / ns).glob("*.json")
    )


def validate(package: dict[str, Any], path: Path) -> list[str]:
    errors: list[str] = []
    if package.get("provider") != "drozer":
        errors.append("invalid provider")
    if not str(package.get("category") or "").startswith("mobile/drozer/"):
        errors.append("invalid category")
    scripts = package.get("scripts")
    if not isinstance(scripts, list) or not scripts:
        return errors + ["scripts must be non-empty"]
    if path.name != f"{package.get('package_id')}.json":
        errors.append("filename/package mismatch")
    assets = package.get("assets") or []
    if len(assets) != 1 or assets[0].get("id") != "drozer_runner":
        errors.append("package must declare exactly the drozer_runner asset")
    if package.get("chains") != []:
        errors.append("Drozer package must not contain chains")

    tag_keys = {
        tag.get("key")
        for group in package.get("tag_categories") or []
        for tag in group.get("tags") or []
    }
    names: set[str] = set()
    with tempfile.TemporaryDirectory(prefix="drozer-pack-check-") as temporary:
        for index, script in enumerate(scripts):
            metadata = script.get("source_metadata") or {}
            code = script.get("command") or ""
            config = script.get("executor_config") or {}
            if script.get("executor") != "python":
                errors.append(f"script {index}: executor must be python")
            if not code.strip():
                errors.append(f"script {index}: blank command")
            required = set(script.get("required_tags") or [])
            placeholders = set(PLACEHOLDER.findall(code))
            if required != placeholders:
                errors.append(
                    f"script {index}: placeholder mismatch required={sorted(required)} placeholders={sorted(placeholders)}"
                )
            if not required.issubset(tag_keys):
                errors.append(f"script {index}: undefined tags {sorted(required - tag_keys)}")
            asset_refs = set(ASSET.findall(code))
            if asset_refs != {"drozer_runner"}:
                errors.append(f"script {index}: asset refs {sorted(asset_refs)}")
            if set(script.get("required_assets") or []) != {"drozer_runner"}:
                errors.append(f"script {index}: required_assets must be ['drozer_runner']")
            # command must compile as Python
            try:
                compile(code, f"<drozer-{index}>", "exec")
            except SyntaxError as exc:
                errors.append(f"script {index}: python syntax invalid: {exc}")
            if metadata.get("provider") != "drozer":
                errors.append(f"script {index}: incomplete provider provenance")
            if metadata.get("target_platform") != "android":
                errors.append(f"script {index}: invalid target_platform")
            if metadata.get("requires_drozer") is not True:
                errors.append(f"script {index}: missing requires_drozer")
            if metadata.get("mobile_lab_compatible") is not True:
                errors.append(f"script {index}: missing mobile_lab_compatible")
            if not metadata.get("source_commit") or not metadata.get("source_sha256"):
                errors.append(f"script {index}: incomplete source provenance")
            if not metadata.get("license"):
                errors.append(f"script {index}: missing license")
            if script.get("operational_risk") not in VALID_RISK:
                errors.append(f"script {index}: invalid operational risk")
            name = script.get("name") or ""
            if not name.startswith("DROZER - "):
                errors.append(f"script {index}: name must start with 'DROZER - '")
            if name in names:
                errors.append(f"script {index}: duplicate name {name}")
            names.add(name)
    return errors


def main() -> int:
    selected = paths()
    catalog = read(CATALOG_FILE)
    entries = {entry.get("package_id"): entry for entry in catalog.get("packs", [])}
    failures = 0
    total_scripts = 0
    for path in selected:
        package = read(path)
        total_scripts += len(package.get("scripts") or [])
        errors = validate(package, path)
        entry = entries.get(package.get("package_id"))
        if not entry:
            errors.append("catalog entry missing")
        elif entry.get("script_count") != len(package.get("scripts") or []):
            errors.append("catalog count mismatch")
        if errors:
            failures += 1
            print(f"[FAIL] {path.name}: {len(errors)} errors")
            for error in errors[:20]:
                print(f"  - {error}")
        else:
            print(f"[OK] {path.name}: scripts={len(package.get('scripts'))}")

    report = read(OUTPUT_DIR / "drozer-conversion-report.json")
    assert len(selected) == EXPECTED_PACKAGES, f"expected {EXPECTED_PACKAGES} packages, got {len(selected)}"
    assert total_scripts == EXPECTED_SCRIPTS, f"expected {EXPECTED_SCRIPTS} scripts, got {total_scripts}"
    assert report.get("reconciliation", {}).get("silent_loss") == 0
    assert report.get("reconciliation", {}).get("core_reconciled") is True
    assert report.get("reconciliation", {}).get("external_reconciled") is True
    assert report.get("reconciliation", {}).get("suppressed_medusa") == 0
    assert report.get("reconciliation", {}).get("suppressed_frida_mobile") == 0

    if failures:
        print(f"[FAIL] Drozer package validation: {failures} packages failed")
        return 1
    print(f"[OK] Drozer packages valid: {len(selected)} packages, {total_scripts} scripts")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
