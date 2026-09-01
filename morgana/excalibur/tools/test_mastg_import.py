#!/usr/bin/env python3
"""Validate all generated OWASP MASTG packages, inventories, and coverage index."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

TOOLS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS_DIR))
OUTPUT_DIR = TOOLS_DIR.parent / "mobile" / "mastg"
CATALOG_FILE = TOOLS_DIR.parent / "catalog.json"
MOBILE_LAB_DIR = TOOLS_DIR.parent.parent / "mobile-lab"

EXPECTED_PACKAGES = 4
EXPECTED_TESTS = 292
EXPECTED_DEMOS = 157
VALID_RISK = {"observe", "interact", "modify", "disrupt"}
VALID_AUTOMATION = {"MANUAL", "SEMI_AUTOMATABLE", "AUTOMATABLE"}


def read(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: root must be object")
    return value


def pack_paths() -> list[Path]:
    return [
        OUTPUT_DIR / "tests" / "mastg-tests-android-v1.json",
        OUTPUT_DIR / "tests" / "mastg-tests-ios-v1.json",
        OUTPUT_DIR / "demos" / "mastg-demos-android-v1.json",
        OUTPUT_DIR / "demos" / "mastg-demos-ios-v1.json",
    ]


def validate_package(package: dict[str, Any], path: Path) -> list[str]:
    errors: list[str] = []
    if package.get("provider") != "owasp-mastg":
        errors.append("invalid provider")
    if not str(package.get("category") or "").startswith("mobile/mastg/"):
        errors.append("invalid category")
    scripts = package.get("scripts")
    if not isinstance(scripts, list) or not scripts:
        return errors + ["scripts must be non-empty"]
    if path.name != f"{package.get('package_id')}.json":
        errors.append("filename/package mismatch")
    if package.get("chains") != []:
        errors.append("MASTG packages must not contain chains")

    names: set[str] = set()
    for index, script in enumerate(scripts):
        metadata = script.get("source_metadata") or {}
        name = script.get("name") or ""
        executor = script.get("executor")
        if not name.startswith("MASTG - "):
            errors.append(f"script {index}: name must start with 'MASTG - '")
        if name in names:
            errors.append(f"script {index}: duplicate name {name}")
        names.add(name)
        if script.get("operational_risk") not in VALID_RISK:
            errors.append(f"script {index}: invalid operational risk")
        if metadata.get("provider") != "owasp-mastg":
            errors.append(f"script {index}: incomplete provider provenance")
        if not metadata.get("source_commit") or not metadata.get("source_sha256"):
            errors.append(f"script {index}: incomplete source provenance")
        if metadata.get("mobile_lab_compatible") is not True:
            errors.append(f"script {index}: missing mobile_lab_compatible")
        # content kind consistency
        kind = metadata.get("content_kind")
        if kind == "MASTG_TEST":
            if executor != "manual":
                errors.append(f"script {index}: MASTG_TEST must be manual executor, got {executor}")
            if metadata.get("canonical_test_id") is None:
                errors.append(f"script {index}: missing canonical_test_id")
            if metadata.get("automation_level") not in VALID_AUTOMATION:
                errors.append(f"script {index}: invalid automation_level")
        elif kind == "MASTG_DEMO":
            if metadata.get("canonical_demo_id") is None:
                errors.append(f"script {index}: missing canonical_demo_id")
            if metadata.get("demo_kind") == "FRIDA_EXEC":
                if executor != "frida":
                    errors.append(f"script {index}: FRIDA_EXEC demo must use frida executor, got {executor}")
                if not script.get("command", "").strip():
                    errors.append(f"script {index}: frida demo has blank command")
                if "mobile_app_id" not in (script.get("required_tags") or []):
                    errors.append(f"script {index}: frida demo missing mobile_app_id tag")
            else:
                if executor != "manual":
                    errors.append(f"script {index}: non-frida demo must be manual executor")
        else:
            errors.append(f"script {index}: unknown content_kind {kind}")
    return errors


def main() -> int:
    selected = pack_paths()
    catalog = read(CATALOG_FILE)
    entries = {e.get("package_id"): e for e in catalog.get("packs", [])}
    failures = 0
    total_tests = 0
    total_demos = 0
    for path in selected:
        package = read(path)
        for e in validate_package(package, path):
            print(f"[FAIL] {path.name}: {e}")
            failures += 1
        if path.parent.name == "tests":
            total_tests += len(package["scripts"])
        else:
            total_demos += len(package["scripts"])
        entry = entries.get(package["package_id"])
        if not entry:
            print(f"[FAIL] catalog missing entry for {package['package_id']}")
            failures += 1
        elif entry.get("script_count") != len(package["scripts"]):
            print(f"[FAIL] catalog script_count mismatch for {package['package_id']}")
            failures += 1

    if total_tests != EXPECTED_TESTS:
        print(f"[FAIL] expected {EXPECTED_TESTS} test scripts, got {total_tests}")
        failures += 1
    if total_demos != EXPECTED_DEMOS:
        print(f"[FAIL] expected {EXPECTED_DEMOS} demo scripts, got {total_demos}")
        failures += 1

    # coverage index integrity
    coverage = read(MOBILE_LAB_DIR / "mastg-coverage.json")
    counts = coverage.get("counts", {})
    if counts.get("tests") != EXPECTED_TESTS:
        print(f"[FAIL] coverage counts.tests != {EXPECTED_TESTS}")
        failures += 1
    if len(coverage.get("tests", [])) != EXPECTED_TESTS:
        print(f"[FAIL] coverage tests array length mismatch")
        failures += 1
    # every published test script must appear in coverage
    test_ids = {t.get("canonical_test_id") for t in coverage.get("tests", [])}
    for path in selected:
        if path.parent.name != "tests":
            continue
        package = read(path)
        for s in package["scripts"]:
            cid = s["source_metadata"].get("canonical_test_id")
            if cid not in test_ids:
                print(f"[FAIL] coverage missing test {cid}")
                failures += 1

    # reconciliation reports assert 100%
    validation = read(OUTPUT_DIR / "mastg-validation-report.json")
    if not validation.get("tests_reconciled_100"):
        print("[FAIL] tests reconciliation not 100%")
        failures += 1
    if not validation.get("demos_reconciled_100"):
        print("[FAIL] demos reconciliation not 100%")
        failures += 1

    # playground apps + services
    pg = read(MOBILE_LAB_DIR / "owasp-playground-apps.json")
    if len(pg.get("apps", [])) != 3:
        print(f"[FAIL] expected 3 playground apps, got {len(pg.get('apps', []))}")
        failures += 1
    if len(pg.get("backends", [])) != 1:
        print(f"[FAIL] expected 1 playground backend, got {len(pg.get('backends', []))}")
        failures += 1
    # license recorded
    for app in pg.get("apps", []):
        if app.get("license") != "GPL-3.0":
            print(f"[FAIL] playground app missing GPL-3.0 license: {app.get('name')}")
            failures += 1
        if app.get("source_commit") == "":
            print(f"[FAIL] playground app missing source commit: {app.get('name')}")
            failures += 1

    if failures:
        print(f"[FAIL] MASTG validation: {failures} error(s)")
        return 1
    print(f"[OK] MASTG validation passed: {total_tests} tests, {total_demos} demos, {len(selected)} packages")
    return 0


if __name__ == "__main__":
    sys.exit(main())
