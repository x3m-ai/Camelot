"""Static validation for IndustriConnect generated packs.

Checks, for every pack JSON:
  - valid JSON and required top-level fields
  - unique script names
  - every required_asset references a declared asset
  - every tag in required_tags is declared in tag_categories
  - command compiles as Python after substituting asset placeholder and
    tag placeholders with their declared defaults
  - operational_risk is one of observe/interact/modify/disrupt
  - package/script prefix matches ALLOWED_PREFIXES convention (INDUSTRICONNECT)
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

EXCALIBUR = Path(__file__).resolve().parent.parent
PKG_DIR = EXCALIBUR / "ot" / "industriconnect"
RISKS = {"observe", "interact", "modify", "disrupt"}
ASSET_PLACEHOLDER = "{{asset:industriconnect_mcp_runner}}"
# Morgana replaces {{asset:id}} with a plain path (no quotes); tag values are
# inserted raw (no re-quoting). Simulate exactly that.
ASSET_STUB = "C:/ProgramData/Morgana/industriconnect/runner.py"


def tag_default(pkg: dict, key: str) -> str:
    for cat in pkg.get("tag_categories", []):
        for t in cat.get("tags", []):
            if t.get("key") == key:
                return t.get("default") or ""
    return ""


def validate_pkg(path: Path) -> list[str]:
    errors: list[str] = []
    pkg = json.loads(path.read_text(encoding="utf-8"))
    pkg_id = pkg.get("package_id", path.stem)

    if not pkg.get("package_id"):
        errors.append("missing package_id")
    if pkg.get("script_prefix") != "INDUSTRICONNECT - ":
        errors.append("script_prefix must be 'INDUSTRICONNECT - '")
    if not pkg.get("scripts"):
        errors.append("no scripts")

    declared_tags: set[str] = set()
    for cat in pkg.get("tag_categories", []):
        for t in cat.get("tags", []):
            declared_tags.add(t["key"])

    asset_ids = {a["id"] for a in pkg.get("assets", [])}
    names: set[str] = set()
    ids: set[str] = set()

    for s in pkg["scripts"]:
        name = s.get("name") or ""
        sid = s.get("id") or ""
        if name in names:
            errors.append(f"duplicate script name: {name}")
        names.add(name)
        if sid in ids:
            errors.append(f"duplicate script id: {sid}")
        ids.add(sid)

        if not name.startswith("INDUSTRICONNECT - "):
            errors.append(f"bad name prefix: {name}")
        if s.get("operational_risk") not in RISKS:
            errors.append(f"{name}: bad risk {s.get('operational_risk')!r}")
        for a in s.get("required_assets", []):
            if a not in asset_ids:
                errors.append(f"{name}: unknown asset {a}")
        for tag in s.get("required_tags", []):
            if tag not in declared_tags:
                errors.append(f"{name}: undeclared tag {tag}")

        cmd = s.get("command", "")
        if ASSET_PLACEHOLDER not in cmd:
            errors.append(f"{name}: missing runner asset placeholder")
        # substitute asset + tags (raw, matching Morgana apply_tag_substitution)
        resolved = cmd.replace(ASSET_PLACEHOLDER, ASSET_STUB)
        # Morgana tag substitution inserts raw values (no re-quoting); the
        # generator already wraps each placeholder in its own string literal.
        resolved = re.sub(
            r"#\{([^}]+)\}",
            lambda m: tag_default(pkg, m.group(1)),
            resolved,
        )
        try:
            compile(resolved, f"<{pkg_id}:{sid}>", "exec")
        except SyntaxError as exc:
            errors.append(f"{name}: command SyntaxError: {exc}")
        # unresolved placeholder check
        leftover = re.findall(r"#\{([^}]+)\}", resolved)
        if leftover:
            errors.append(f"{name}: unresolved placeholders {leftover}")

    return errors


def main() -> int:
    failed = False
    total_scripts = 0
    for path in sorted(PKG_DIR.glob("industriconnect-*.json")):
        # Skip report/artifact files that share the prefix.
        if path.name in {
            "industriconnect-validation-report.json",
            "industriconnect-lab-service-inventory.json",
            "industriconnect-conversion-report.json",
            "industriconnect-source-inventory.json",
        }:
            continue
        errs = validate_pkg(path)
        pkg = json.loads(path.read_text(encoding="utf-8"))
        total_scripts += len(pkg["scripts"])
        if errs:
            failed = True
            print(f"[FAIL] {path.name}: {len(errs)} errors")
            for e in errs[:10]:
                print(f"    - {e}")
        else:
            print(f"[OK] {path.name}: {len(pkg['scripts'])} scripts valid")
    print(f"\nTotal scripts validated: {total_scripts}")
    if failed:
        print("[FAIL] Validation FAILED")
        return 1
    print("[SUCCESS] All IndustriConnect packs pass static validation")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
