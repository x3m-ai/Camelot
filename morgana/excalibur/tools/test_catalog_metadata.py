#!/usr/bin/env python3
"""Validate decision metadata for every package in the Excalibur catalog."""

from __future__ import annotations

import json
from pathlib import Path


CATALOG = Path(__file__).resolve().parent.parent / "catalog.json"
REQUIRED_LISTS = ("capabilities", "use_cases", "prerequisites", "safety_notes")


def validate_catalog(catalog: dict) -> list[str]:
    errors: list[str] = []
    packs = catalog.get("packs")
    if not isinstance(packs, list) or not packs:
        return ["catalog packs must be a non-empty array"]

    package_ids: set[str] = set()
    urls: set[str] = set()
    known_providers = {
        item.get("id") for item in catalog.get("providers", []) if isinstance(item, dict)
    }
    for index, pack in enumerate(packs):
        label = str(pack.get("package_id") or f"pack[{index}]")
        package_id = str(pack.get("package_id") or "").strip()
        if not package_id:
            errors.append(f"{label}: missing package_id")
        elif package_id in package_ids:
            errors.append(f"{label}: duplicate package_id")
        package_ids.add(package_id)

        for field in ("package_name", "description"):
            value = str(pack.get(field) or "").strip()
            if len(value) < 4:
                errors.append(f"{label}: {field} is missing or too short")
        if not str(pack.get("mitre_tactic") or "").strip():
            errors.append(f"{label}: missing mitre_tactic")
        if len(str(pack.get("description") or "").strip()) < 80:
            errors.append(f"{label}: description must provide a meaningful summary")

        for field in REQUIRED_LISTS:
            values = pack.get(field)
            if not isinstance(values, list) or not values:
                errors.append(f"{label}: {field} must be a non-empty array")
            elif any(not isinstance(item, str) or len(item.strip()) < 12 for item in values):
                errors.append(f"{label}: {field} contains blank or placeholder guidance")

        provider = str(pack.get("provider") or "").strip()
        if not provider:
            errors.append(f"{label}: missing provider")
        elif known_providers and provider not in known_providers:
            errors.append(f"{label}: unknown provider {provider}")
        if not isinstance(pack.get("platform"), list) or not pack.get("platform"):
            errors.append(f"{label}: platform must be a non-empty array")
        for field in ("script_count", "chain_count"):
            if not isinstance(pack.get(field), int) or pack[field] < 0:
                errors.append(f"{label}: invalid {field}")
        url = str(pack.get("url") or "").strip()
        if not url.startswith("https://"):
            errors.append(f"{label}: package URL must use HTTPS")
        elif url in urls:
            errors.append(f"{label}: duplicate package URL")
        urls.add(url)
    return errors


def main() -> int:
    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    errors = validate_catalog(catalog)
    if errors:
        print(f"[FAIL] Catalog metadata: {len(errors)} errors")
        for error in errors:
            print(f"  - {error}")
        return 1
    print(f"[OK] Catalog metadata complete for {len(catalog['packs'])} packages")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())