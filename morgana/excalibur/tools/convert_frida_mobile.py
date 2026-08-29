#!/usr/bin/env python3
"""Build the complete Frida CodeShare and curated mobile Script corpus."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import tempfile
from collections import Counter, defaultdict
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from frida_classifier import classify
from frida_dedup import deduplicate
from frida_github import discover_repository
from frida_sources import FridaSource, compact, load_registry, sha256, write_json

TOOLS_DIR = Path(__file__).resolve().parent
EXCALIBUR_DIR = TOOLS_DIR.parent
DEFAULT_OUTPUT_DIR = EXCALIBUR_DIR / "mobile" / "frida"
DEFAULT_REGISTRY = DEFAULT_OUTPUT_DIR / "source-registry.json"
DEFAULT_CACHE_ROOT = Path(r"C:\ProgramData\Morgana\temp\frida-mobile")
CATALOG_FILE = EXCALIBUR_DIR / "catalog.json"
MAPPING_OVERRIDES_FILE = TOOLS_DIR / "frida_mobile_mapping_overrides.json"
CATALOG_BASE_URL = "https://raw.githubusercontent.com/x3m-ai/Camelot/main/morgana/excalibur/mobile/frida"
VALID_READINESS = {"ready", "ready_with_target", "environment_prerequisite", "framework_prerequisite", "app_specific", "legacy", "manual_review"}
VALID_PLATFORMS = {"android", "ios", "universal-native", "linux-native", "other"}
PLATFORM_DIR = {
    "android": "android", "ios": "ios", "universal-native": "universal",
    "linux-native": "universal", "other": "universal",
}
BEHAVIOR_GROUP = {
    "tls-pinning-testing": "network", "network-observation": "network",
    "enumeration": "enumeration", "runtime-tracing": "runtime",
    "method-hooking": "runtime", "native-hooking": "native",
    "crypto-observation": "crypto", "keystore-keychain": "storage",
    "filesystem": "storage", "database": "storage", "clipboard": "storage",
    "webview": "webview", "biometrics": "biometrics",
    "root-state-testing": "security-controls", "jailbreak-state-testing": "security-controls",
    "debugger-detection-testing": "security-controls", "instrumentation-detection-testing": "security-controls",
    "emulator-detection-testing": "security-controls", "integrity-control-testing": "security-controls",
    "screenshot": "sensors", "location": "sensors", "ipc": "ipc", "other": "other",
}
TAG_DEFINITIONS = {
    "mobile_app_id": {"key": "mobile_app_id", "label": "Mobile App ID / Process", "description": "Android package ID, iOS bundle ID, or target process for the authorized test application.", "default": "", "example": "", "sensitive": False, "required": True, "parameter_class": "value"},
    "mobile_device_id": {"key": "mobile_device_id", "label": "Mobile Device ID", "description": "Optional Frida device identifier. Blank uses the default USB device.", "default": "", "example": "", "sensitive": False, "required": False, "parameter_class": "value"},
}


def codeshare_sources(codeshare_cache: Path) -> tuple[list[FridaSource], dict[str, Any]]:
    inventory_path = codeshare_cache / "codeshare-inventory.json"
    if not inventory_path.is_file():
        raise ValueError(f"CodeShare inventory not found: {inventory_path}; run frida_codeshare.py first")
    inventory = json.loads(inventory_path.read_text(encoding="utf-8"))
    records: list[FridaSource] = []
    for item in inventory.get("projects", []):
        records.append(FridaSource(
            source_provider="frida-codeshare",
            source_id=item["source_id"], title=item["title"],
            description=item.get("description") or "Frida CodeShare project",
            source_code=item["source_code"], source_url=item["project_url"],
            source_hash=item["source_hash"], license=item.get("license", "unknown"),
            license_source=item.get("license_source", "CodeShare"),
            distribution_status=item.get("distribution_status", "unknown-license"),
            quality_tier="B" if int(item.get("popularity", {}).get("likes") or 0) >= 5 else "C",
            source_metadata={
                "codeshare_author": item.get("author"), "codeshare_slug": item.get("slug"),
                "codeshare_fingerprint": item.get("codeshare_fingerprint"),
                "project_uuid": item.get("project_uuid"), "popularity": item.get("popularity", {}),
                "discovery_page": item.get("discovery_page"),
            },
        ))
    report = {
        "source_id": "frida-codeshare", "source_type": "codeshare",
        "pages_attempted": inventory.get("pages_attempted", 0),
        "pages_scanned": inventory.get("pages_scanned", 0),
        "projects_discovered": inventory.get("projects_discovered", 0),
        "projects_fetched": inventory.get("projects_fetched", 0),
        "errors": inventory.get("errors", []),
        "license": "unknown", "distribution_status": "unknown-license",
    }
    return records, report


def node_validate(sources: list[FridaSource]) -> tuple[list[FridaSource], list[dict[str, str]]]:
    valid: list[FridaSource] = []
    malformed: list[dict[str, str]] = []
    with tempfile.TemporaryDirectory(prefix="frida-js-validate-") as temporary:
        directory = Path(temporary)
        for index, source in enumerate(sources):
            if not source.source_code.strip():
                source.status = "excluded"
                malformed.append({"source_id": source.source_id, "reason": "empty source"})
                continue
            if source.source_metadata.get("source_extension") == ".ts":
                source.status = "unsupported"
                malformed.append({"source_id": source.source_id, "reason": "TypeScript source requires a pinned build toolchain"})
                continue
            if re.search(r"```(?:javascript|js|typescript|ts)?", source.source_code, re.I):
                source.status = "malformed"
                malformed.append({"source_id": source.source_id, "reason": "markdown fence remains in source"})
                continue
            if re.search(r"<!DOCTYPE|<html\b|<body\b", source.source_code, re.I):
                source.status = "malformed"
                malformed.append({"source_id": source.source_id, "reason": "HTML mixed into source"})
                continue
            script_path = directory / f"{index:05d}.js"
            script_path.write_text(source.source_code, encoding="utf-8")
            result = subprocess.run(
                ["node", "--check", str(script_path)], capture_output=True,
                text=True, encoding="utf-8", errors="replace", timeout=20,
            )
            if result.returncode:
                source.status = "malformed"
                reason = result.stderr.replace(str(script_path), "<source>.js")
                malformed.append({"source_id": source.source_id, "reason": compact(reason, 1000)})
            else:
                valid.append(source)
    return valid, malformed


def neutralize_comment_tag_collisions(sources: list[FridaSource]) -> None:
    for source in sources:
        lines = source.source_code.splitlines(keepends=True)
        changed = False
        for index, line in enumerate(lines):
            comment_index = line.find("//")
            if comment_index < 0 or "#{" not in line[comment_index:]:
                continue
            lines[index] = line[:comment_index] + line[comment_index:].replace("#{", "# {")
            changed = True
        if changed:
            source.source_code = "".join(lines)
            source.transformations.append("neutralized-morgana-tag-syntax-in-comment")


def script_name(source: FridaSource) -> str:
    platform = "ANDROID" if source.target_platform == "android" else "IOS" if source.target_platform == "ios" else "UNIVERSAL"
    app = " APP" if source.scope in {"app-specific", "version-specific"} else ""
    title = compact(source.title, 110)
    suffix = source.source_hash[:8]
    return f"FRIDA - {platform}{app} - {source.primary_behavior.replace('-', ' ').title()} - {title} [{suffix}]"


def script_from(source: FridaSource) -> dict[str, Any]:
    target_platform = "android" if source.target_platform == "android" else "ios" if source.target_platform == "ios" else "universal-native"
    return {
        "id": source.source_id,
        "name": script_name(source),
        "description": compact(source.description, 900),
        "tactic": "Mobile Runtime Instrumentation",
        "tcode": source.primary_tcode,
        "executor": "frida",
        "executor_config": {
            "target_platform": target_platform,
            "target": "#{mobile_app_id}",
            "device": "#{mobile_device_id}",
            "transport": "usb",
            "mode": "spawn",
            "resume": True,
            "max_stdout_bytes": 102400,
            "max_stderr_bytes": 102400,
        },
        "platform": "all",
        "command": source.source_code,
        "cleanup_command": None,
        "required_tags": ["mobile_app_id", "mobile_device_id"],
        "required_assets": [],
        "operational_risk": source.risk,
        "source_metadata": {
            **source.source_metadata,
            "provider": "frida-mobile", "source_provider": source.source_provider,
            "source_id": source.source_id, "source_url": source.source_url,
            "source_hash": source.source_hash, "normalized_hash": source.normalized_hash,
            "target_platform": source.target_platform, "execution_platform": "host-agent",
            "frameworks": source.frameworks, "scope": source.scope,
            "behaviors": source.behaviors, "primary_behavior": source.primary_behavior,
            "frida_apis": source.frida_apis, "compatibility_status": source.compatibility_status,
            "mitre_domain": "mobile-attack", "source_tcodes": source.source_tcodes,
            "mitre_mapping_status": "mapped" if source.source_tcodes else "unmapped",
            "quality_tier": source.quality_tier, "license": source.license,
            "license_source": source.license_source, "distribution_status": source.distribution_status,
            "readiness": source.readiness, "duplicate_of": source.duplicate_of,
            "derived_from": source.derived_from, "source_modified": bool(source.transformations),
            "transformations": source.transformations,
        },
    }


def pack_group(source: FridaSource) -> tuple[str, str]:
    for framework in ("flutter", "react-native", "xamarin", "unity-il2cpp"):
        if framework in source.frameworks:
            return framework, framework
    platform = PLATFORM_DIR[source.target_platform]
    behavior = "app-specific" if source.scope in {"app-specific", "version-specific"} else BEHAVIOR_GROUP.get(source.primary_behavior, "other")
    return platform, behavior


def chunk_sources(sources: list[FridaSource], max_count: int, max_bytes: int) -> list[list[FridaSource]]:
    chunks: list[list[FridaSource]] = []
    current: list[FridaSource] = []
    current_bytes = 0
    for source in sorted(sources, key=lambda item: item.source_id.lower()):
        estimated = len(source.source_code.encode("utf-8")) + 5000
        if current and (len(current) >= max_count or current_bytes + estimated > max_bytes):
            chunks.append(current); current = []; current_bytes = 0
        current.append(source); current_bytes += estimated
    if current: chunks.append(current)
    return chunks


def build_packs(sources: list[FridaSource], max_count: int, max_bytes: int) -> list[tuple[dict[str, Any], str]]:
    groups: dict[tuple[str, str], list[FridaSource]] = defaultdict(list)
    for source in sources: groups[pack_group(source)].append(source)
    packages: list[tuple[dict[str, Any], str]] = []
    for (directory, behavior), group in sorted(groups.items()):
        chunks = chunk_sources(group, max_count, max_bytes)
        for index, chunk in enumerate(chunks, start=1):
            suffix = f"-{index:02d}" if len(chunks) > 1 else ""
            package_id = f"frida-{directory}-{behavior}{suffix}-v1"
            scripts = [script_from(source) for source in chunk]
            platform_counts = Counter(source.target_platform for source in chunk)
            scope_counts = Counter(source.scope for source in chunk)
            frameworks = sorted({framework for source in chunk for framework in source.frameworks})
            behaviors = sorted({behavior_name for source in chunk for behavior_name in source.behaviors})
            source_providers = sorted({source.source_provider for source in chunk})
            quality_counts = Counter(source.quality_tier for source in chunk)
            license_counts = Counter(source.license for source in chunk)
            compatibility_counts = Counter(source.compatibility_status for source in chunk)
            tcodes = sorted({tcode for source in chunk for tcode in source.source_tcodes})
            risk_badges = sorted({source.risk for source in chunk}, key=("observe", "interact", "modify", "disrupt").index)
            package = {
                "package_id": package_id,
                "package_name": f"Frida - {directory.replace('-', ' ').title()} - {behavior.replace('-', ' ').title()}{' Part ' + str(index) if len(chunks) > 1 else ''}",
                "version": "1.0.0",
                "summary": f"{len(chunk)} Frida instrumentation procedures for {directory.replace('-', ' ')} {behavior.replace('-', ' ')} mobile testing.",
                "description": "Source-faithful public Frida JavaScript from CodeShare and curated repositories, statically validated and classified for authorized mobile dynamic analysis.",
                "purpose": "Run authorized Android/iOS runtime observation, hooking, framework, network, crypto, storage, and security-control validation through a Morgana host Agent.",
                "capabilities": [
                    f"Contains {len(chunk)} standalone Frida procedures from {len(source_providers)} source families.",
                    f"Target platforms: {', '.join(platform_counts)}; frameworks: {', '.join(frameworks)}.",
                    f"Scope mix: {dict(scope_counts)}; compatibility: {dict(compatibility_counts)}.",
                ],
                "use_cases": [
                    "Instrument an explicitly authorized Android or iOS test application through USB or Frida remote transport.",
                    "Select procedures by platform, framework, behavior, source, app scope, ATT&CK Mobile mapping, or quality tier.",
                ],
                "prerequisites": [
                    "Morgana host Agent with a compatible Frida CLI installed and reachable in PATH.",
                    "Authorized mobile test device/emulator with Frida server, Gadget, or supported instrumentation path.",
                    "Operator-supplied target package, bundle ID, or process and optional device ID.",
                ],
                "safety_notes": [
                    "Third-party scripts may change application runtime behavior; review source and risk metadata before execution.",
                    "Unknown-license content is clearly labeled in per-Script metadata and the license inventory.",
                    "Full-corpus runtime validation is intentionally left for isolated operator mobile labs.",
                ],
                "author": "Frida ecosystem / X3M.AI conversion",
                "created": str(date.today()), "script_prefix": "FRIDA - ",
                "provider": "frida-mobile", "source": "frida-mobile",
                "source_repository": "https://codeshare.frida.re/",
                "source_license": "mixed", "documentation_url": "https://frida.re/docs/",
                "mitre_domain": "mobile-attack", "mitre_tactic": "Mobile Runtime Instrumentation",
                "mitre_tcodes": tcodes, "platform": ["all"], "risk_badges": risk_badges,
                "category": f"mobile/frida/{directory}", "target_platform_counts": dict(platform_counts),
                "frameworks": frameworks, "behavior_categories": behaviors,
                "source_providers": source_providers, "scope_counts": dict(scope_counts),
                "quality_distribution": dict(quality_counts), "license_distribution": dict(license_counts),
                "compatibility_distribution": dict(compatibility_counts),
                "tag_categories": [{"category_id": "frida_mobile_target", "label": "Frida Mobile Target", "description": "Host-to-mobile Frida target parameters.", "scope": "local", "tags": list(TAG_DEFINITIONS.values())}],
                "assets": [], "scripts": scripts, "chains": [],
            }
            relative = f"{directory}/{package_id}.json"
            packages.append((package, relative))
    return packages


def catalog_entry(package: dict[str, Any], relative: str) -> dict[str, Any]:
    fields = (
        "package_id", "package_name", "version", "summary", "description", "purpose",
        "capabilities", "use_cases", "prerequisites", "safety_notes", "provider", "category",
        "platform", "mitre_tactic", "mitre_tcodes", "mitre_domain", "source", "source_license",
        "documentation_url", "risk_badges", "target_platform_counts", "frameworks",
        "behavior_categories", "source_providers", "scope_counts", "quality_distribution",
        "license_distribution", "compatibility_distribution",
    )
    return {key: package[key] for key in fields} | {
        "script_count": len(package["scripts"]), "chain_count": 0, "asset_count": 0,
        "status": "community", "author": package["author"],
        "url": f"{CATALOG_BASE_URL}/{relative}",
    }


def update_catalog(entries: list[dict[str, Any]]) -> None:
    catalog = json.loads(CATALOG_FILE.read_text(encoding="utf-8"))
    catalog["packs"] = [entry for entry in catalog.get("packs", []) if entry.get("provider") != "frida-mobile"] + entries
    catalog["catalog_version"] = "1.9.0"; catalog["updated"] = str(date.today())
    catalog["providers"] = [entry for entry in catalog.get("providers", []) if entry.get("id") != "frida-mobile"] + [{"id": "frida-mobile", "name": "Frida Mobile Ecosystem", "type": "multi-source", "repository": "https://codeshare.frida.re/", "domain": "mobile-attack"}]
    category_ids = {f"mobile/frida/{value}" for value in ("android", "ios", "flutter", "react-native", "xamarin", "unity-il2cpp", "universal")}
    catalog["categories"] = [entry for entry in catalog.get("categories", []) if entry.get("id") not in category_ids] + [
        {"id": "mobile/frida/android", "label": "Frida / Android", "group": "Mobile Emulation", "order": 600, "provider": "frida-mobile"},
        {"id": "mobile/frida/ios", "label": "Frida / iOS", "group": "Mobile Emulation", "order": 610, "provider": "frida-mobile"},
        {"id": "mobile/frida/flutter", "label": "Frida / Flutter", "group": "Mobile Emulation", "order": 620, "provider": "frida-mobile"},
        {"id": "mobile/frida/react-native", "label": "Frida / React Native", "group": "Mobile Emulation", "order": 630, "provider": "frida-mobile"},
        {"id": "mobile/frida/xamarin", "label": "Frida / Xamarin", "group": "Mobile Emulation", "order": 640, "provider": "frida-mobile"},
        {"id": "mobile/frida/unity-il2cpp", "label": "Frida / Unity IL2CPP", "group": "Mobile Emulation", "order": 650, "provider": "frida-mobile"},
        {"id": "mobile/frida/universal", "label": "Frida / Universal Native", "group": "Mobile Emulation", "order": 660, "provider": "frida-mobile"},
    ]
    write_json(CATALOG_FILE, catalog)


def load_codeshare_cache(cache_root: Path) -> list[dict[str, Any]]:
    inventory = json.loads((cache_root / "codeshare" / "codeshare-inventory.json").read_text(encoding="utf-8"))
    return inventory.get("projects", [])


def readme(report: dict[str, Any]) -> str:
    return f"""# Frida Mobile Emulation Packs

Source-faithful Frida JavaScript from CodeShare and curated public repositories for authorized Android/iOS dynamic analysis through a Morgana host Agent.

- Source units discovered: {report['source_units_discovered']}
- Published Scripts: {report['published']}
- Exact duplicates: {report['exact_duplicates']}
- Normalized duplicates: {report['normalized_duplicates']}
- Meaningful derivatives retained: {report['meaningful_derivatives_retained']}
- Packages: {report['packages']}
- Validation: {report['validation']}

Every Script requires an operator-selected target app/process. Runtime validation of the complete third-party corpus is intentionally left to isolated mobile test environments.
"""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--codeshare-cache", type=Path, default=DEFAULT_CACHE_ROOT / "codeshare")
    parser.add_argument("--source-registry", type=Path, default=DEFAULT_REGISTRY)
    parser.add_argument("--cache-root", type=Path, default=DEFAULT_CACHE_ROOT)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--source")
    parser.add_argument("--platform", choices=sorted(VALID_PLATFORMS))
    parser.add_argument("--framework")
    parser.add_argument("--scope")
    parser.add_argument("--behavior")
    parser.add_argument("--quality")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--report-only", action="store_true")
    parser.add_argument("--no-update-catalog", action="store_true")
    parser.add_argument("--max-per-pack", type=int, default=350)
    parser.add_argument("--max-pack-bytes", type=int, default=5_000_000)
    parser.add_argument("--refresh-github", action="store_true")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()
    registry = load_registry(args.source_registry)
    overrides = json.loads(MAPPING_OVERRIDES_FILE.read_text(encoding="utf-8")) if MAPPING_OVERRIDES_FILE.is_file() else {}
    records, codeshare_report = codeshare_sources(args.codeshare_cache)
    source_reports: dict[str, Any] = {}
    registry_sources = [source for source in registry["sources"] if source.get("enabled") and source.get("type") == "github"]
    for source in registry_sources:
        if args.source and args.source != source["id"]:
            continue
        discovered, report = discover_repository(source, args.cache_root, args.refresh_github)
        records.extend(discovered); source_reports[source["id"]] = report
        if args.verbose: print(f"[GITHUB] {source['id']}: {len(discovered)} candidates")
    discovered_count = len(records)
    neutralize_comment_tag_collisions(records)
    valid, malformed = node_validate(records)
    for source in valid:
        classify(source, overrides)
    api_valid: list[FridaSource] = []
    unsupported_items: list[dict[str, str]] = []
    for source in valid:
        if source.frida_apis:
            api_valid.append(source)
            continue
        source.status = "unsupported"
        unsupported_items.append({
            "source_id": source.source_id,
            "reason": "No supported Frida JavaScript API primitive detected",
        })
    canonical, dedup_report = deduplicate(api_valid)
    filters = {
        "source_provider": args.source, "target_platform": args.platform,
        "scope": args.scope, "primary_behavior": args.behavior, "quality_tier": args.quality,
    }
    filtered = [source for source in canonical if all(not expected or getattr(source, field) == expected for field, expected in filters.items())]
    if args.framework: filtered = [source for source in filtered if args.framework in source.frameworks]
    filter_excluded = len(canonical) - len(filtered)
    canonical = filtered
    status_counts = Counter(source.status for source in records)
    exact_duplicates = dedup_report["exact_duplicates"]
    normalized_duplicates = dedup_report["normalized_duplicates"]
    unsupported_count = sum(source.status == "unsupported" for source in records)
    malformed_count = sum(source.status == "malformed" for source in records)
    excluded_count = filter_excluded + sum(source.status == "excluded" for source in records)
    reconciled = discovered_count == len(canonical) + exact_duplicates + normalized_duplicates + malformed_count + unsupported_count + excluded_count
    if not reconciled:
        raise ValueError(f"source reconciliation failed: discovered={discovered_count} published={len(canonical)} exact={exact_duplicates} normalized={normalized_duplicates} malformed={malformed_count} unsupported={unsupported_count} excluded={excluded_count}")
    for source in canonical:
        if source.target_platform not in VALID_PLATFORMS or source.readiness not in VALID_READINESS or not source.behaviors or not source.scope:
            raise ValueError(f"classification incomplete: {source.source_id}")
    packages = build_packs(canonical, args.max_per_pack, args.max_pack_bytes)
    source_inventory = [source.inventory() for source in sorted(records, key=lambda item: item.source_id.lower())]
    license_counts = Counter(source.license for source in records)
    distribution_counts = Counter(source.distribution_status for source in records)
    report = {
        "codeshare": codeshare_report,
        "sources_discovered": 1 + len(registry_sources),
        "curated_repositories_scanned": len(registry_sources),
        "source_reports": source_reports,
        "source_units_discovered": discovered_count,
        "raw_scripts": discovered_count,
        "exact_duplicates": exact_duplicates,
        "normalized_duplicates": normalized_duplicates,
        "meaningful_derivatives_retained": dedup_report["meaningful_derivatives_retained"],
        "published": len(canonical), "malformed": malformed_count,
        "unsupported": unsupported_count, "excluded": excluded_count,
        "unknown_license": distribution_counts["unknown-license"], "packages": len(packages),
        "platform_counts": dict(Counter(source.target_platform for source in canonical)),
        "framework_counts": dict(Counter(framework for source in canonical for framework in source.frameworks)),
        "scope_counts": dict(Counter(source.scope for source in canonical)),
        "behavior_counts": dict(Counter(behavior for source in canonical for behavior in source.behaviors)),
        "source_provider_counts": dict(Counter(source.source_provider for source in canonical)),
        "quality_counts": dict(Counter(source.quality_tier for source in canonical)),
        "compatibility_counts": dict(Counter(source.compatibility_status for source in canonical)),
        "license_counts": dict(license_counts), "distribution_counts": dict(distribution_counts),
        "source_reconciled": reconciled, "validation": "PASS",
        "malformed_items": malformed,
        "unsupported_items": unsupported_items,
    }
    if args.dry_run or args.report_only:
        print(json.dumps(report, indent=2)); return 0
    staging = Path(tempfile.mkdtemp(prefix="frida-mobile-output-", dir=str(args.out_dir.parent)))
    try:
        for package, relative in packages: write_json(staging / relative, package)
        write_json(staging / "source-registry.json", registry)
        write_json(staging / "source-inventory.json", source_inventory)
        codeshare_inventory = json.loads((args.codeshare_cache / "codeshare-inventory.json").read_text(encoding="utf-8"))
        for project in codeshare_inventory.get("projects", []): project.pop("source_code", None)
        write_json(staging / "codeshare-inventory.json", codeshare_inventory)
        write_json(staging / "conversion-report.json", report)
        write_json(staging / "license-inventory.json", {"license_counts": dict(license_counts), "distribution_counts": dict(distribution_counts), "sources": source_reports})
        write_json(staging / "dedup-report.json", dedup_report)
        write_json(staging / "compatibility-transformations.json", {"transformations": []})
        write_json(staging / "source-candidates.json", registry.get("source_candidates", []))
        write_json(staging / "mobile-attack-map.json", {"source": "ATT&CK Mobile", "mapping_policy": "curated deterministic behavior mappings", "techniques": sorted({source.primary_tcode for source in canonical if source.primary_tcode != "T0000"})})
        (staging / "README.md").write_text(readme(report), encoding="utf-8")
        if args.out_dir.exists(): shutil.rmtree(args.out_dir)
        staging.replace(args.out_dir)
    except Exception:
        shutil.rmtree(staging, ignore_errors=True); raise
    if not args.no_update_catalog: update_catalog([catalog_entry(package, relative) for package, relative in packages])
    print(f"[FRIDA] raw={discovered_count} published={len(canonical)} duplicates={exact_duplicates + normalized_duplicates} malformed={malformed_count} unsupported={unsupported_count} packs={len(packages)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())