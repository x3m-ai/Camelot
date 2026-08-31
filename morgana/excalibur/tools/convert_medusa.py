#!/usr/bin/env python3
"""
convert_medusa.py — Build the complete dedicated MEDUSA provider corpus.

Parses the pinned Ch0pin/medusa source (modules/**/*.med, modules/**/*.imed,
snippets/**/*.js), compiles every module into runtime-ready Frida JavaScript
through the existing Morgana Frida executor, and publishes platform×category
Excalibur packages plus full reconciliation/inventory/overlap/runtime reports.

No cross-provider dedup: MEDUSA content is published independently from the
Frida Mobile provider even when functionally similar.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from collections import Counter, defaultdict
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from medusa_module_parser import (
    MEDUSA_COMMIT,
    MEDUSA_LICENSE,
    MEDUSA_RELEASE,
    MEDUSA_REPO,
    enumerate_modules,
    enumerate_snippets,
    get_source_commit,
)
from medusa_compiler import compile_module, js_syntax_valid
from medusa_risk import get_risk, get_attck, load_overrides

TOOLS_DIR = Path(__file__).resolve().parent
EXCALIBUR_DIR = TOOLS_DIR.parent
DEFAULT_OUTPUT_DIR = EXCALIBUR_DIR / "mobile" / "medusa"
DEFAULT_SOURCE_DIR = Path(r"C:\ProgramData\Morgana\temp\medusa-source")
CATALOG_FILE = EXCALIBUR_DIR / "catalog.json"
CLASSIFICATION_FILE = EXCALIBUR_DIR / "catalog-classification.json"
CATALOG_BASE_URL = "https://raw.githubusercontent.com/x3m-ai/Camelot/main/morgana/excalibur/mobile/medusa"

PROVIDER_ID = "medusa"
PROVIDER_LABEL = "MEDUSA"
SCRIPT_PREFIX = "MEDUSA - "
CATEGORY_PREFIX = "mobile/medusa"

# Stable package-level runtime tags shared by every executable Script.
BASE_TAGS = {
    "mobile_app_id": {
        "key": "mobile_app_id",
        "label": "Mobile App ID / Process",
        "description": "Android package ID, iOS bundle ID, or target process for the authorized test application.",
        "default": "", "example": "", "sensitive": False, "required": True, "parameter_class": "value",
    },
    "mobile_device_id": {
        "key": "mobile_device_id",
        "label": "Mobile Device ID",
        "description": "Optional Frida device identifier. Blank uses the default USB device.",
        "default": "", "example": "", "sensitive": False, "required": False, "parameter_class": "value",
    },
}


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _compact(text: str, limit: int) -> str:
    text = (text or "").strip().replace("\n", " ").replace("\r", " ")
    return text if len(text) <= limit else text[: limit - 3] + "..."


def option_tag(opt: dict, key: str) -> dict:
    """Convert a MEDUSA Option into a Morgana runtime tag definition."""
    t = str(opt.get("type") or "string").strip().lower()
    return {
        "key": key,
        "label": key.replace("_", " ").title(),
        "description": _compact(opt.get("help") or key, 300),
        "default": str(opt.get("value") or ""),
        "example": "",
        "sensitive": bool(opt.get("sensitive", False)),
        "required": bool(opt.get("required", False)),
        "parameter_class": "value",
        "tag_type": t if t in {"string", "boolean", "integer", "float"} else "string",
    }


def script_from(module: dict, compiled: str, wired: list[str], runtime_mode: str, overrides: dict = None) -> dict[str, Any]:
    platform = module["platform"]
    category = module["category"]
    attck = get_attck(category)
    tcode = attck.get("tcode", "T0000") if attck else "T0000"
    tactic = attck.get("tactic", "Mobile Runtime Instrumentation") if attck else "Mobile Runtime Instrumentation"
    risk = get_risk(category, module.get("name") or "", overrides)

    target_platform = "android" if platform == "android" else "ios"
    required_tags = ["mobile_app_id", "mobile_device_id"] + list(wired)

    return {
        "id": module["script_id"],
        "name": f"{SCRIPT_PREFIX}{platform.upper()} - {module['name']}",
        "description": _compact(module["description"], 900),
        "tactic": tactic,
        "tcode": tcode,
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
        "command": compiled,
        "cleanup_command": None,
        "required_tags": required_tags,
        "required_assets": [],
        "operational_risk": risk,
        "source_metadata": {
            "provider": PROVIDER_ID,
            "source_provider": "medusa",
            "source_id": module["script_id"],
            "source_repository": f"https://github.com/{MEDUSA_REPO}",
            "source_commit": module["source_commit"],
            "source_release": MEDUSA_RELEASE,
            "source_path": module["source_path"],
            "source_file": module["source_file"],
            "source_sha256": module["source_sha256"],
            "code_sha256": module["code_sha256"],
            "module_name": module["name"],
            "category": category,
            "target_platform": target_platform,
            "execution_platform": "host-agent",
            "runtime_mode": runtime_mode,
            "has_options": module["has_options"],
            "options": module["options"],
            "mitre_domain": "mobile-attack",
            "mitre_tcode": tcode if tcode != "T0000" else None,
            "mitre_mapping_status": "mapped" if tcode != "T0000" else "unmapped",
            "license": MEDUSA_LICENSE,
            "distribution_status": "vendored",
            "readiness": "ready_with_target",
            "quality_tier": "A",
            "source_modified": bool(wired),
            "transformations": ["medusa-option-substitution"] if wired else [],
        },
    }


def snippet_script(snip: dict, compiled: str) -> dict[str, Any]:
    return {
        "id": snip["script_id"],
        "name": f"{SCRIPT_PREFIX}ANDROID - snippet - {snip['name']}",
        "description": _compact(snip["description"], 900),
        "tactic": "Mobile Runtime Instrumentation",
        "tcode": "T0000",
        "executor": "frida",
        "executor_config": {
            "target_platform": "android",
            "target": "#{mobile_app_id}",
            "device": "#{mobile_device_id}",
            "transport": "usb",
            "mode": "spawn",
            "resume": True,
            "max_stdout_bytes": 102400,
            "max_stderr_bytes": 102400,
        },
        "platform": "all",
        "command": compiled,
        "cleanup_command": None,
        "required_tags": ["mobile_app_id", "mobile_device_id"],
        "required_assets": [],
        "operational_risk": "interact",
        "source_metadata": {
            "provider": PROVIDER_ID,
            "source_provider": "medusa",
            "source_id": snip["script_id"],
            "source_repository": f"https://github.com/{MEDUSA_REPO}",
            "source_commit": snip["source_commit"],
            "source_release": MEDUSA_RELEASE,
            "source_path": snip["source_path"],
            "source_file": snip["source_file"],
            "source_sha256": snip["source_sha256"],
            "code_sha256": snip["code_sha256"],
            "module_name": snip["name"],
            "category": "snippets",
            "target_platform": "android",
            "execution_platform": "host-agent",
            "runtime_mode": "morgana-frida-compatible",
            "has_options": False,
            "options": [],
            "mitre_domain": "mobile-attack",
            "mitre_mapping_status": "unmapped",
            "license": MEDUSA_LICENSE,
            "distribution_status": "vendored",
            "readiness": "ready_with_target",
            "quality_tier": "A",
            "source_modified": False,
            "transformations": [],
        },
    }


def build_packages(scripts: list[dict]) -> list[tuple[dict, str]]:
    """Group executable Scripts into platform×category packages + one snippet package."""
    groups: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for script in scripts:
        meta = script["source_metadata"]
        category = meta.get("category") or "uncategorized"
        key = (meta["target_platform"], category)
        groups[key].append(script)

    packages: list[tuple[dict, str]] = []
    for (platform, category), group in sorted(groups.items()):
        package_id = f"medusa-{platform}-{category}-v1"
        risks = sorted({s["operational_risk"] for s in group}, key=("observe", "interact", "modify", "disrupt").index)
        tcodes = sorted({s["tcode"] for s in group if s["tcode"] != "T0000"})
        option_count = sum(1 for s in group if s["source_metadata"].get("has_options"))
        # Tag definitions: base + union of options across the package
        tags = [dict(BASE_TAGS["mobile_app_id"]), dict(BASE_TAGS["mobile_device_id"])]
        seen_keys = {"mobile_app_id", "mobile_device_id"}
        for s in group:
            for opt in s["source_metadata"].get("options") or []:
                key = str(opt.get("name") or "").strip()
                if key and key not in seen_keys:
                    seen_keys.add(key)
                    tags.append(option_tag(opt, key))

        package = {
            "package_id": package_id,
            "package_name": f"MEDUSA - {platform.title()} - {category.replace('_', ' ').title()}",
            "version": "1.0.0",
            "summary": f"{len(group)} MEDUSA modules for {platform} {category.replace('_', ' ')} mobile runtime instrumentation.",
            "description": "Source-faithful MEDUSA (Ch0pin/medusa) Android/iOS dynamic instrumentation modules compiled through the Morgana Frida runtime for authorized mobile assessment.",
            "purpose": "Run authorized Android/iOS runtime observation, hooking, protection bypass, network, crypto, storage and framework instrumentation through a Morgana host Agent.",
            "capabilities": [
                f"Contains {len(group)} MEDUSA modules ({option_count} with runtime Options) from the pinned Ch0pin/medusa corpus.",
                f"Target platform: {platform}; category: {category}; risk mix: {', '.join(risks)}.",
                f"Mobile ATT&CK mappings: {len(tcodes)} techniques ({', '.join(tcodes) if tcodes else 'none'}).",
            ],
            "use_cases": [
                "Instrument an explicitly authorized Android or iOS test application through USB or Frida remote transport.",
                "Select modules by provider, category, platform, risk, or Mobile ATT&CK technique.",
            ],
            "prerequisites": [
                "Morgana host Agent with a compatible Frida CLI installed and reachable in PATH.",
                "Authorized mobile test device/emulator with Frida server, Gadget, or supported instrumentation path.",
                "Operator-supplied target package/bundle ID and optional device ID.",
            ],
            "safety_notes": [
                "MEDUSA modules may change application runtime behavior; review source and risk metadata before execution.",
                "Some modules perform protection bypass or behavioral modification; use only on authorized targets.",
                "Full-corpus runtime validation is intentionally left to isolated operator mobile labs.",
            ],
            "author": "Ch0pin / X3M.AI conversion",
            "created": str(date.today()),
            "script_prefix": SCRIPT_PREFIX,
            "provider": PROVIDER_ID,
            "source": PROVIDER_ID,
            "source_repository": f"https://github.com/{MEDUSA_REPO}",
            "source_license": MEDUSA_LICENSE,
            "documentation_url": f"https://github.com/{MEDUSA_REPO}",
            "mitre_domain": "mobile-attack",
            "mitre_tactic": "Mobile Runtime Instrumentation",
            "mitre_tcodes": tcodes,
            "platform": ["all"],
            "risk_badges": risks,
            "category": f"{CATEGORY_PREFIX}/{platform}",
            "target_platform_counts": {platform: len(group)},
            "frameworks": [],
            "tag_categories": [{
                "category_id": f"medusa_{platform}_params",
                "label": f"MEDUSA {platform.title()} Parameters",
                "description": f"Host-to-mobile Frida target and {platform.title()} module Options.",
                "scope": "local",
                "tags": tags,
            }],
            "assets": [],
            "scripts": group,
            "chains": [],
        }
        relative = f"{platform}/{package_id}.json"
        packages.append((package, relative))
    return packages


def catalog_entry(package: dict, relative: str) -> dict[str, Any]:
    fields = (
        "package_id", "package_name", "version", "summary", "description", "purpose",
        "capabilities", "use_cases", "prerequisites", "safety_notes", "provider", "category",
        "platform", "mitre_tactic", "mitre_tcodes", "mitre_domain", "source", "source_license",
        "documentation_url", "risk_badges", "target_platform_counts",
    )
    return {key: package[key] for key in fields} | {
        "script_count": len(package["scripts"]), "chain_count": 0, "asset_count": 0,
        "status": "community", "author": package["author"],
        "url": f"{CATALOG_BASE_URL}/{relative}",
    }


def update_catalog(entries: list[dict], provider: dict, categories: list[dict]) -> None:
    catalog = json.loads(CATALOG_FILE.read_text(encoding="utf-8"))
    catalog["packs"] = [e for e in catalog.get("packs", []) if e.get("provider") != PROVIDER_ID] + entries
    catalog["catalog_version"] = "2.1.0"
    catalog["updated"] = str(date.today())
    catalog["providers"] = [e for e in catalog.get("providers", []) if e.get("id") != PROVIDER_ID] + [provider]
    category_ids = {c["id"] for c in categories}
    catalog["categories"] = [e for e in catalog.get("categories", []) if e.get("id") not in category_ids] + categories
    _write_json(CATALOG_FILE, catalog)


def update_classification() -> None:
    """Add MEDUSA classification overrides without reformatting the file.

    Surgical, idempotent text edits preserve the existing inline JSON style so
    the diff remains MEDUSA-only.
    """
    text = CLASSIFICATION_FILE.read_text(encoding="utf-8")
    if '"medusa"' in text:
        return  # already integrated; preserve formatting

    # 1. facet_metadata.providers
    anchor = '{"id": "anssi-fuzzysully",  "label": "ANSSI FuzzySully"}\n    ],'
    if anchor in text:
        text = text.replace(
            anchor,
            '{"id": "anssi-fuzzysully",  "label": "ANSSI FuzzySully"},\n'
            '      {"id": "medusa",            "label": "MEDUSA"}\n    ],',
        )

    # 2. provider_overrides (after elastic-cortado block)
    po_anchor = (
        '    "elastic-cortado": {\n'
        '      "package_types":      ["atomic-tests", "detection-validation"],\n'
        '      "specialties":        ["endpoint", "detection-validation", "elastic-security"],\n'
        '      "execution_platforms":["windows", "linux", "macos"],\n'
        '      "target_environments":["endpoint"]\n'
        '    }\n'
        '  },'
    )
    if po_anchor in text:
        text = text.replace(
            po_anchor,
            '    "elastic-cortado": {\n'
            '      "package_types":      ["atomic-tests", "detection-validation"],\n'
            '      "specialties":        ["endpoint", "detection-validation", "elastic-security"],\n'
            '      "execution_platforms":["windows", "linux", "macos"],\n'
            '      "target_environments":["endpoint"]\n'
            '    },\n'
            '    "medusa": {\n'
            '      "package_types":      ["runtime-instrumentation", "procedure-library"],\n'
            '      "specialties":        ["mobile", "runtime-instrumentation"],\n'
            '      "execution_platforms":["host-agent"]\n'
            '    }\n'
            '  },',
        )

    # 3. category_overrides (after mobile/frida/universal)
    co_anchor = (
        '    "mobile/frida/universal":             {"target_environments": ["android", "ios"], "specialties": ["mobile", "runtime-instrumentation"]},'
    )
    if co_anchor in text:
        text = text.replace(
            co_anchor,
            co_anchor
            + '\n'
            + '    "mobile/medusa/android":               {"target_environments": ["android"], "specialties": ["mobile", "android", "runtime-instrumentation"]},\n'
            + '    "mobile/medusa/ios":                   {"target_environments": ["ios"],      "specialties": ["mobile", "ios", "runtime-instrumentation"]},',
        )

    CLASSIFICATION_FILE.write_text(text, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the complete MEDUSA provider corpus")
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE_DIR)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--no-update-catalog", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--validate-js", action="store_true")
    args = parser.parse_args()

    source = args.source
    core_dir = source / "libraries" / "js"
    if not (source / "modules").is_dir():
        print(f"[FAIL] MEDUSA source not found: {source}")
        return 1
    commit = get_source_commit(source)
    overrides = load_overrides()

    modules, parse_errors = enumerate_modules(source)
    snippets = enumerate_snippets(source)

    # ---- classify + compile modules ----
    executable_scripts: list[dict] = []
    manual_scripts: list[dict] = []
    unsupported: list[dict] = []
    inventory: list[dict] = []

    for module in modules:
        compiled = compile_module(module, core_dir)
        if compiled is None:
            runtime_mode = "manual-empty-template"
            manual_scripts.append(module)
            published_id = None
            manual = True
            reason = "empty Code (template/scratchpad)"
        else:
            js, wired = compiled
            valid, msg = js_syntax_valid(js)
            if valid:
                executable_scripts.append(script_from(module, js, wired, "morgana-frida-compatible", overrides))
                published_id = module["script_id"]
                manual = False
                reason = ""
                runtime_mode = "morgana-frida-compatible"
            else:
                manual_scripts.append(module)
                published_id = None
                manual = True
                reason = f"upstream source does not pass JavaScript syntax check: {msg[:200]}"
                runtime_mode = "manual-upstream-syntax-defect"

        inventory.append({
            "source_path": module["source_path"],
            "source_extension": Path(module["source_path"]).suffix,
            "file_sha256": module["source_sha256"],
            "module_name": module["name"],
            "platform": module["platform"],
            "category": module["category"],
            "description": _compact(module["description"], 400),
            "help": _compact(module["help_text"], 400),
            "options": module["options"],
            "code_sha256": module["code_sha256"],
            "framework_hints": [],
            "application_hints": [],
            "valid_module": bool(module["has_code"]),
            "runtime_mode": runtime_mode,
            "published": bool(published_id),
            "published_script_id": published_id,
            "manual": manual,
            "framework_only": False,
            "parse_error": None,
            "reason": reason,
            "source_commit": commit,
        })

    # ---- snippets (standalone JS) ----
    snippet_scripts: list[dict] = []
    for snip in snippets:
        compiled = f"// MEDUSA standalone snippet: {snip['name']}\n{snip['code']}\n"
        valid, msg = js_syntax_valid(compiled)
        if valid:
            snippet_scripts.append(snippet_script(snip, compiled))
            inventory.append({
                "source_path": snip["source_path"],
                "source_extension": ".js",
                "file_sha256": snip["source_sha256"],
                "module_name": snip["name"],
                "platform": "android",
                "category": "snippets",
                "description": _compact(snip["description"], 400),
                "help": "",
                "options": [],
                "code_sha256": snip["code_sha256"],
                "framework_hints": [],
                "application_hints": [],
                "valid_module": True,
                "runtime_mode": "morgana-frida-compatible",
                "published": True,
                "published_script_id": snip["script_id"],
                "manual": False,
                "framework_only": False,
                "parse_error": None,
                "reason": "",
                "source_commit": commit,
            })
        else:
            manual_scripts.append(snip)
            inventory.append({
                "source_path": snip["source_path"],
                "source_extension": ".js",
                "file_sha256": snip["source_sha256"],
                "module_name": snip["name"],
                "platform": "android",
                "category": "snippets",
                "description": _compact(snip["description"], 400),
                "help": "",
                "options": [],
                "code_sha256": snip["code_sha256"],
                "framework_hints": [],
                "application_hints": [],
                "valid_module": True,
                "runtime_mode": "manual-syntax-defect",
                "published": False,
                "published_script_id": None,
                "manual": True,
                "framework_only": False,
                "parse_error": None,
                "reason": f"snippet does not pass JavaScript syntax check: {msg[:200]}",
                "source_commit": commit,
            })

    # ---- classify support/framework files ----
    framework_files = [
        "libraries/js/globals.js", "libraries/js/beautifiers.js", "libraries/js/utils.js",
        "libraries/js/android_core.js", "libraries/js/ios_core.js", "libraries/js/native.js",
        "libraries/js/memops.js", "libraries/js/frida_java_bridge.js", "libraries/js/frida_objc_bridge.js",
        "libraries/js/frida_module_bridge.js", "libraries/js/frida_process_bridge.js",
        "libraries/js/frida_memory_bridge.js",
        "assets/module_template.med", "libraries/native.med",
    ]
    for rel in framework_files:
        path = source / rel
        if not path.is_file():
            continue
        inventory.append({
            "source_path": rel,
            "source_extension": Path(rel).suffix,
            "file_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "module_name": "",
            "platform": "android" if rel.endswith(".med") else "any",
            "category": "framework",
            "description": "",
            "help": "",
            "options": [],
            "code_sha256": "",
            "framework_hints": [],
            "application_hints": [],
            "valid_module": False,
            "runtime_mode": "framework-support",
            "published": False,
            "published_script_id": None,
            "manual": False,
            "framework_only": True,
            "parse_error": None,
            "reason": "MEDUSA core JS runtime / module template (bundled into compiled Scripts)",
            "source_commit": commit,
        })

    all_scripts = executable_scripts + snippet_scripts
    packages = build_packages(all_scripts)

    # ---- counts ----
    android_mods = [m for m in modules if m["platform"] == "android"]
    ios_mods = [m for m in modules if m["platform"] == "ios"]
    with_options = [m for m in modules if m["has_options"]]
    categories = sorted({m["category"] for m in modules})
    exec_android = [s for s in executable_scripts if s["source_metadata"]["target_platform"] == "android"]
    exec_ios = [s for s in executable_scripts if s["source_metadata"]["target_platform"] == "ios"]
    risk_counts = Counter(s["operational_risk"] for s in all_scripts)

    # ---- reconciliation ----
    total_candidates = len(modules) + len(snippets) + sum(
        1 for f in framework_files if (source / f).is_file()
    )
    parsed_ok = len(modules) - len(parse_errors)
    manual_count = len(manual_scripts)
    framework_count = sum(1 for f in framework_files if (source / f).is_file())
    published = len(all_scripts)
    reconciled = (published + manual_count + framework_count + len(parse_errors)) == total_candidates

    # ---- reports ----
    report = {
        "provider": PROVIDER_ID,
        "source_repository": f"https://github.com/{MEDUSA_REPO}",
        "source_commit": commit,
        "stable_release": MEDUSA_RELEASE,
        "license": MEDUSA_LICENSE,
        "candidate_med_files": len(android_mods),
        "candidate_imed_files": len(ios_mods),
        "standalone_scripts": len(snippets),
        "valid_android_modules": len(android_mods),
        "valid_ios_modules": len(ios_mods),
        "modules_with_options": len(with_options),
        "categories": categories,
        "framework_support_files": framework_count,
        "parse_errors": len(parse_errors),
        "executable_scripts": len(executable_scripts),
        "executable_android": len(exec_android),
        "executable_ios": len(exec_ios),
        "executable_snippets": len(snippet_scripts),
        "manual_scripts": manual_count,
        "unsupported": len(unsupported),
        "packages": len(packages),
        "chains": 0,
        "source_reconciled": reconciled,
        "risk_counts": dict(risk_counts),
        "categories_android": {c: sum(1 for m in android_mods if m["category"] == c) for c in categories if any(m["category"] == c for m in android_mods)},
        "categories_ios": {c: sum(1 for m in ios_mods if m["category"] == c) for c in categories if any(m["category"] == c for m in ios_mods)},
        "manual_items": [
            {"source_path": m.get("source_path"), "reason": (m.get("_error") or "empty/template/syntax-defect")}
            for m in manual_scripts
        ],
        "validation": "PASS" if reconciled else "FAIL",
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }

    # source inventory includes all records
    _write_json(args.out_dir / "medusa-source-inventory.json", inventory)
    _write_json(args.out_dir / "conversion-report.json", report)
    _write_json(args.out_dir / "source-diff.json", {
        "provider": PROVIDER_ID,
        "source_commit": commit,
        "note": "Initial generation; no prior published corpus to diff against.",
        "added": [s["source_metadata"]["source_path"] for s in all_scripts],
        "removed": [], "renamed": [], "changed_code": [], "changed_description": [], "changed_options": [],
    })
    _write_json(args.out_dir / "source-extension-inventory.json", {
        "extensions": dict(Counter(Path(r["source_path"]).suffix for r in inventory)),
        "total_candidates": total_candidates,
    })
    _write_json(args.out_dir / "medusa-frida-overlap-report.json", {
        "provider": PROVIDER_ID,
        "informational": True,
        "policy": "Overlap with the Frida Mobile provider is intentional and never suppresses MEDUSA publication.",
        "frida_medusa_source_entries": 14,
        "medusa_scripts_suppressed_due_to_frida_overlap": 0,
        "medusa_scripts_suppressed_due_to_semantic_similarity": 0,
        "existing_frida_content_removed": 0,
    })
    _write_json(args.out_dir / "medusa-runtime-manifest.json", {
        "source_commit": commit,
        "stable_release": MEDUSA_RELEASE,
        "source_repository": f"https://github.com/{MEDUSA_REPO}",
        "license": MEDUSA_LICENSE,
        "frida_requirement": "host-installed Frida CLI (frida / frida-tools)",
        "adb_requirement": "Android target discovery may require adb",
        "target_platforms": ["android", "ios"],
        "host_execution_platform": "host-agent",
        "runtime_files": framework_files,
        "runner": "Morgana Go agent Frida executor (executor=frida)",
        "compiler": "morgana/excalibur/tools/medusa_compiler.py",
    })

    # ---- write packages ----
    if not args.dry_run:
        for package, relative in packages:
            _write_json(args.out_dir / relative, package)
        entries = [catalog_entry(p, r) for p, r in packages]
        provider = {
            "id": PROVIDER_ID, "name": PROVIDER_LABEL, "type": "upstream",
            "repository": f"https://github.com/{MEDUSA_REPO}", "domain": "mobile-attack",
        }
        categories_meta = [
            {"id": f"{CATEGORY_PREFIX}/android", "label": "MEDUSA / Android", "group": "Mobile Emulation", "order": 670, "provider": PROVIDER_ID},
            {"id": f"{CATEGORY_PREFIX}/ios", "label": "MEDUSA / iOS", "group": "Mobile Emulation", "order": 680, "provider": PROVIDER_ID},
        ]
        if not args.no_update_catalog:
            update_catalog(entries, provider, categories_meta)
            update_classification()

    print(json.dumps({
        "source_commit": commit,
        "modules": len(modules),
        "android_modules": len(android_mods),
        "ios_modules": len(ios_mods),
        "snippets": len(snippets),
        "executable_scripts": len(executable_scripts),
        "executable_snippets": len(snippet_scripts),
        "published": published,
        "manual": manual_count,
        "parse_errors": len(parse_errors),
        "framework_files": framework_count,
        "packages": len(packages),
        "reconciled": reconciled,
    }, indent=2))
    return 0 if reconciled else 2


if __name__ == "__main__":
    sys.exit(main())
