#!/usr/bin/env python3
"""
enrich_catalog.py — Enrich catalog.json with normalized facet metadata.

Reads catalog.json + catalog-classification.json, applies classification
overrides to each pack (non-destructively), aggregates top-level `facets`,
and writes the enriched catalog back.

Usage:
    python enrich_catalog.py [--catalog PATH] [--classification PATH] [--report]
"""
from __future__ import annotations

import argparse
import json
import sys
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent
CAMELOT_ROOT = TOOLS_DIR.parent.parent.parent
DEFAULT_CATALOG = CAMELOT_ROOT / "morgana/excalibur/catalog.json"
DEFAULT_CLASSIF = CAMELOT_ROOT / "morgana/excalibur/catalog-classification.json"


# ── CTID plan_type → package_type inference ──────────────────────────────────
_PLAN_TYPE_MAP = {
    "full-emulation":  "full-emulation",
    "micro-emulation": "micro-emulation",
}

# ── legacy platform normalization ─────────────────────────────────────────────
_LEGACY_PLATFORM_EXEC_MAP = {
    "windows": "windows",
    "linux":   "linux",
    "macos":   "macos",
    "all":     "cross-platform",
}
_LEGACY_PLATFORM_SKIP = {"azure"}  # azure goes to target_environments, not exec

_LEGACY_PLATFORM_TARGET_MAP = {
    "azure":   ["azure", "entra-id"],
}


def _uniq(lst: list) -> list:
    seen = set()
    out = []
    for x in lst:
        if x and x not in seen:
            seen.add(x)
            out.append(x)
    return out


def _resolve_field(pack: dict, classif: dict, field: str) -> list:
    """
    Resolution order for array fields (specialties, package_types, etc.):
    1. Explicit pack metadata (new fields)
    2. Provider override from classification
    3. Category override from classification
    4. Legacy inference
    Returns deduplicated list.
    """
    # 1. Explicit new field
    if pack.get(field):
        explicit = pack[field]
        if isinstance(explicit, list) and explicit:
            return _uniq(explicit)

    result: list[str] = []

    # 2. Provider override
    provider = pack.get("provider") or pack.get("source") or ""
    po = classif.get("provider_overrides", {}).get(provider, {})
    result.extend(po.get(field, []))

    # 3. Category override
    category = pack.get("category", "")
    co = classif.get("category_overrides", {}).get(category, {})
    result.extend(co.get(field, []))

    # 4. Legacy inference for specific fields
    if field == "package_types" and not result:
        pt = pack.get("plan_type", "")
        if pt in _PLAN_TYPE_MAP:
            result.append(_PLAN_TYPE_MAP[pt])
        elif not pt:
            result.append("tactic-pack")  # sensible default for non-emulation packs

    if field == "execution_platforms" and not result:
        for plat in (pack.get("platform") or []):
            p = str(plat).lower().strip()
            if p in _LEGACY_PLATFORM_SKIP:
                continue
            mapped = _LEGACY_PLATFORM_EXEC_MAP.get(p)
            if mapped:
                result.append(mapped)

    if field == "target_environments" and not result:
        for plat in (pack.get("platform") or []):
            p = str(plat).lower().strip()
            extras = _LEGACY_PLATFORM_TARGET_MAP.get(p)
            if extras:
                result.extend(extras)
            elif p not in _LEGACY_PLATFORM_EXEC_MAP and p not in ("all",):
                result.append(p)  # e.g. azure passthrough

    if field == "specialties" and not result:
        cat = pack.get("category", "")
        if cat.startswith("art"):
            result = ["endpoint", "adversary-emulation"]
        elif cat.startswith("ctid"):
            result = ["adversary-emulation", "detection-validation"]
        elif cat.startswith("stockpile"):
            result = ["adversary-emulation"]
        elif cat.startswith("lotl"):
            result = ["living-off-the-land", "endpoint"]
        elif cat.startswith("drivers"):
            result = ["driver-security", "endpoint"]
        elif cat.startswith("mobile"):
            result = ["mobile", "runtime-instrumentation"]
        elif cat.startswith("ot"):
            result = ["ot-ics"]
        elif cat == "technology":
            result = []
        elif cat == "general":
            result = []

    return _uniq(result)


def _get_attack_domain(pack: dict) -> str:
    return pack.get("mitre_domain", "")


def _get_tactics(pack: dict) -> list[str]:
    explicit = pack.get("mitre_tactics", [])
    if explicit and isinstance(explicit, list):
        return [t for t in explicit if t]
    single = pack.get("mitre_tactic", "")
    return [single] if single else []


def enrich_pack(pack: dict, classif: dict) -> dict:
    """Add normalized facet fields to a pack dict (non-destructive, additive)."""
    p = deepcopy(pack)
    p["specialties"]          = _resolve_field(pack, classif, "specialties")
    p["package_types"]         = _resolve_field(pack, classif, "package_types")
    p["execution_platforms"]   = _resolve_field(pack, classif, "execution_platforms")
    p["target_environments"]   = _resolve_field(pack, classif, "target_environments")
    p["mitre_tactics_resolved"] = _get_tactics(pack)
    if not p.get("mitre_domain"):
        p.pop("mitre_domain", None)
    return p


def build_facets(packs: list[dict], classif: dict) -> dict:
    """Build top-level facets from enriched packs + facet_metadata from classif."""
    meta = classif.get("facet_metadata", {})

    def _known_ids(name):
        return {e["id"] for e in meta.get(name, [])}

    def _label(name, id_):
        for e in meta.get(name, []):
            if e.get("id") == id_:
                return e
        return {"id": id_, "label": id_.replace("-", " ").title()}

    # Collect actually-used values from enriched packs
    used: dict[str, set[str]] = {
        "providers": set(),
        "specialties": set(),
        "attack_domains": set(),
        "attack_tactics": set(),
        "package_types": set(),
        "execution_platforms": set(),
        "target_environments": set(),
        "operational_risks": set(),
    }
    for pack in packs:
        pid = pack.get("provider") or pack.get("source") or ""
        if pid: used["providers"].add(pid)
        for x in pack.get("specialties", []):          used["specialties"].add(x)
        dom = pack.get("mitre_domain", "")
        if dom: used["attack_domains"].add(dom)
        for t in pack.get("mitre_tactics_resolved", []): used["attack_tactics"].add(t)
        for x in pack.get("package_types", []):         used["package_types"].add(x)
        for x in pack.get("execution_platforms", []):   used["execution_platforms"].add(x)
        for x in pack.get("target_environments", []):   used["target_environments"].add(x)
        for x in pack.get("risk_badges", []):            used["operational_risks"].add(x)

    def _build_list(name, used_ids, id_key="id"):
        defined = meta.get(name, [])
        defined_ids = {e.get("id") for e in defined}
        result = [deepcopy(e) for e in defined if e.get("id") in used_ids]
        # Add unknown values not in metadata
        for uid in sorted(used_ids - defined_ids):
            result.append({"id": uid, "label": uid.replace("-", " ").title()})
        # Sort by label (defined entries may have order)
        return sorted(result, key=lambda e: (e.get("order", 99), e.get("label", "")))

    return {
        "providers":           _build_list("providers", used["providers"]),
        "specialties":         _build_list("specialties", used["specialties"]),
        "attack_domains":      _build_list("attack_domains", used["attack_domains"]),
        "attack_tactics":      sorted(list({"id": t, "label": t} for t in used["attack_tactics"]), key=lambda e: e["label"]),
        "package_types":       _build_list("package_types", used["package_types"]),
        "execution_platforms": _build_list("execution_platforms", used["execution_platforms"]),
        "target_environments": _build_list("target_environments", used["target_environments"]),
        "operational_risks":   _build_list("operational_risks", used["operational_risks"]),
    }


def generate_report(packs: list[dict]) -> dict:
    n = len(packs)
    has_pkg_type       = sum(1 for p in packs if p.get("package_types"))
    has_exec_plat      = sum(1 for p in packs if p.get("execution_platforms"))
    has_target_env     = sum(1 for p in packs if p.get("target_environments"))
    has_specialties    = sum(1 for p in packs if p.get("specialties"))
    has_domain         = sum(1 for p in packs if p.get("mitre_domain"))
    legacy_all         = [p["package_id"] for p in packs if "all" in [str(x).lower() for x in (p.get("platform") or [])]]
    azure_legacy       = [p["package_id"] for p in packs if "azure" in [str(x).lower() for x in (p.get("platform") or [])] and not p.get("target_environments")]
    no_pkg_type        = [p["package_id"] for p in packs if not p.get("package_types")]
    mobile_with_target = sum(1 for p in packs if any(e in ["android", "ios"] for e in (p.get("target_environments") or [])))
    ot_with_target     = sum(1 for p in packs if any(e in ["ot-ics", "opc-ua", "modbus", "dnp3", "s7comm", "iec-104"] for e in (p.get("target_environments") or [])))

    return {
        "total_packages": n,
        "packages_with_package_types":      has_pkg_type,
        "packages_with_execution_platforms": has_exec_plat,
        "packages_with_target_environments": has_target_env,
        "packages_with_specialties":         has_specialties,
        "packages_with_attack_domain":        has_domain,
        "legacy_all_platform_count":          len(legacy_all),
        "azure_in_legacy_platform_count":     len(azure_legacy),
        "packages_without_package_type":      len(no_pkg_type),
        "mobile_packages_with_target_env":    mobile_with_target,
        "ot_packages_with_target_env":        ot_with_target,
        "providers": sorted({p.get("provider","") for p in packs if p.get("provider")}),
        "domains":   sorted({p.get("mitre_domain","") for p in packs if p.get("mitre_domain")}),
        "package_types_used": sorted({t for p in packs for t in (p.get("package_types") or [])}),
        "execution_platforms_used": sorted({e for p in packs for e in (p.get("execution_platforms") or [])}),
        "target_environments_used": sorted({e for p in packs for e in (p.get("target_environments") or [])}),
    }


def main() -> int:
    p = argparse.ArgumentParser(description="Enrich Excalibur catalog with normalized facets")
    p.add_argument("--catalog",        default=str(DEFAULT_CATALOG))
    p.add_argument("--classification", default=str(DEFAULT_CLASSIF))
    p.add_argument("--report",         action="store_true", help="Print classification report")
    p.add_argument("--dry-run",        action="store_true", help="Do not write output")
    args = p.parse_args()

    catalog_path = Path(args.catalog)
    classif_path = Path(args.classification)

    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    classif = json.loads(classif_path.read_text(encoding="utf-8"))

    packs = catalog.get("packs", [])
    print(f"[INFO] Enriching {len(packs)} packs...")

    enriched_packs = [enrich_pack(pack, classif) for pack in packs]
    facets = build_facets(enriched_packs, classif)

    if args.report:
        report = generate_report(enriched_packs)
        report_path = catalog_path.parent / "catalog-classification-report.json"
        if not args.dry_run:
            report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
            print(f"[OK] Report written: {report_path}")
        else:
            print(json.dumps(report, indent=2))

    if args.dry_run:
        print(f"[DRY RUN] Facets that would be generated:")
        for k, v in facets.items():
            print(f"  {k}: {len(v)} values")
        return 0

    catalog["packs"] = enriched_packs
    catalog["facets"] = facets
    catalog["updated"] = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    catalog_path.write_text(json.dumps(catalog, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print(f"[SUCCESS] Catalog enriched:")
    for k, v in facets.items():
        print(f"  {k}: {len(v)} distinct values")
    return 0


if __name__ == "__main__":
    sys.exit(main())
