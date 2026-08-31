#!/usr/bin/env python3
"""Validate all generated MEDUSA packages against the Excalibur schema."""

from __future__ import annotations

import json
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Any

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "mobile" / "medusa"
CATALOG_FILE = Path(__file__).resolve().parent.parent / "catalog.json"
PACKAGE_DIRS = ("android", "ios")
PLACEHOLDER = re.compile(r"#\{([^{}]+)\}")

EXPECTED_PACKAGES = 38
EXPECTED_SCRIPTS = 147
EXPECTED_MANUAL = 4


def read(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: root must be object")
    return value


def paths() -> list[Path]:
    return sorted(
        path
        for directory in PACKAGE_DIRS
        for path in (OUTPUT_DIR / directory).glob("*.json")
    )


def validate(package: dict[str, Any], path: Path, validate_js: bool = False) -> list[str]:
    errors: list[str] = []
    if package.get("provider") != "medusa":
        errors.append("invalid provider")
    if not str(package.get("category") or "").startswith("mobile/medusa/"):
        errors.append("invalid category")
    scripts = package.get("scripts")
    if not isinstance(scripts, list) or not scripts:
        return errors + ["scripts must be non-empty"]
    if path.name != f"{package.get('package_id')}.json":
        errors.append("filename/package mismatch")
    if package.get("assets") != [] or package.get("chains") != []:
        errors.append("bulk MEDUSA package must not contain assets/chains")

    tag_keys = {
        tag.get("key")
        for group in package.get("tag_categories") or []
        for tag in group.get("tags") or []
    }
    names: set[str] = set()
    ids: set[str] = set()
    with tempfile.TemporaryDirectory(prefix="medusa-pack-check-") as temporary:
        for index, script in enumerate(scripts):
            name = str(script.get("name") or "")
            source_id = str(script.get("id") or "")
            metadata = script.get("source_metadata") or {}
            config = script.get("executor_config") or {}
            if not name.startswith("MEDUSA - "):
                errors.append(f"script {index}: invalid prefix")
            if name in names or source_id in ids:
                errors.append(f"script {index}: duplicate identity")
            names.add(name)
            ids.add(source_id)
            if script.get("executor") != "frida" or script.get("platform") != "all":
                errors.append(f"script {index}: invalid executor/host platform")
            if (
                config.get("target") != "#{mobile_app_id}"
                or config.get("transport") not in {"usb", "remote"}
                or config.get("mode") not in {"spawn", "attach"}
            ):
                errors.append(f"script {index}: invalid Frida config")
            code = str(script.get("command") or "")
            if not code.strip():
                errors.append(f"script {index}: blank source")
            required = set(script.get("required_tags") or [])
            placeholders = set(PLACEHOLDER.findall(json.dumps(config) + "\n" + code))
            if required != placeholders:
                errors.append(
                    f"script {index}: placeholder mismatch required={sorted(required)} placeholders={sorted(placeholders)}"
                )
            if not required.issubset(tag_keys):
                errors.append(f"script {index}: undefined tags {sorted(required - tag_keys)}")
            if metadata.get("provider") != "medusa":
                errors.append(f"script {index}: incomplete provider provenance")
            if metadata.get("target_platform") not in {"android", "ios"}:
                errors.append(f"script {index}: invalid target_platform")
            if not metadata.get("source_commit") or not metadata.get("source_sha256"):
                errors.append(f"script {index}: incomplete source provenance")
            if metadata.get("license") != "GPL-3.0":
                errors.append(f"script {index}: missing GPL-3.0 license")
            if script.get("operational_risk") not in {"observe", "interact", "modify", "disrupt"}:
                errors.append(f"script {index}: invalid operational risk")
            if validate_js:
                script_path = Path(temporary) / f"{index:04d}.js"
                neutralized = re.sub(r"#\{[^{}]+\}", "0", code)
                script_path.write_text(neutralized, encoding="utf-8")
                result = subprocess.run(
                    ["node", "--check", str(script_path)],
                    capture_output=True, text=True, encoding="utf-8", errors="replace",
                    timeout=20,
                )
                if result.returncode:
                    errors.append(f"script {index}: JavaScript syntax invalid")
    return errors


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--validate-js", action="store_true")
    args = parser.parse_args()

    selected = paths()
    catalog = read(CATALOG_FILE)
    entries = {entry.get("package_id"): entry for entry in catalog.get("packs", [])}
    failures = 0
    total_scripts = 0
    for path in selected:
        package = read(path)
        total_scripts += len(package.get("scripts") or [])
        errors = validate(package, path, args.validate_js)
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

    report = read(OUTPUT_DIR / "conversion-report.json")
    assert len(selected) == EXPECTED_PACKAGES, f"expected {EXPECTED_PACKAGES} packages, got {len(selected)}"
    assert total_scripts == EXPECTED_SCRIPTS, f"expected {EXPECTED_SCRIPTS} scripts, got {total_scripts}"
    assert report.get("manual_scripts") == EXPECTED_MANUAL, report.get("manual_scripts")
    assert report.get("source_reconciled") is True

    if failures:
        print(f"[FAIL] MEDUSA package validation: {failures} packages failed")
        return 1
    print(f"[OK] MEDUSA packages valid: {len(selected)} packages, {total_scripts} scripts")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
