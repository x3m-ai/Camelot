#!/usr/bin/env python3
"""
convert_drozer.py — Build the complete Drozer provider corpus for Morgana.

Treats three separately pinned upstreams:
  - drozer            (core built-in modules)
  - drozer-agent      (Android app, BSD-3-Clause)
  - drozer-modules    (external community module tree)

Discovers every candidate module via AST, extracts argument schemas, maps risk
+ Mobile ATT&CK, generates one Script per real module, publishes namespaced
Excalibur packages, and emits complete source inventory / conversion report /
reconciliation. The runtime is a single generic runner asset that shells out
to the pinned isolated drozer runtime through the existing Morgana `python`
executor. No duplicate device manager; no fake parameter permutations.

Usage:
    python convert_drozer.py
        [--core-source C:\\ProgramData\\Morgana\\temp\\drozer-source]
        [--modules-source C:\\ProgramData\\Morgana\\temp\\drozer-modules-source]
        [--out-dir morgana/excalibur/mobile/drozer]
        [--no-update-catalog] [--dry-run]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path
from typing import Any

TOOLS_DIR = Path(__file__).resolve().parent
EXCALIBUR_DIR = TOOLS_DIR.parent
DEFAULT_OUTPUT_DIR = EXCALIBUR_DIR / "mobile" / "drozer"
DEFAULT_CORE_SOURCE = Path(r"C:\ProgramData\Morgana\temp\drozer-source")
DEFAULT_MODULES_SOURCE = Path(r"C:\ProgramData\Morgana\temp\drozer-modules-source")
CATALOG_FILE = EXCALIBUR_DIR / "catalog.json"
CLASSIFICATION_FILE = EXCALIBUR_DIR / "catalog-classification.json"
CATALOG_BASE_URL = "https://raw.githubusercontent.com/x3m-ai/Camelot/main/morgana/excalibur/mobile/drozer"
RUNNER_ASSET = DEFAULT_OUTPUT_DIR / "runtime" / "morgana_drozer_runner.py"

from drozer_module_parser import (  # noqa: E402
    DROZER_REPO, DROZER_COMMIT, DROZER_VERSION, DROZER_LICENSE,
    DROZER_AGENT_REPO, DROZER_AGENT_COMMIT, DROZER_AGENT_LICENSE, DROZER_AGENT_PACKAGE,
    DROZER_MODULES_REPO, DROZER_MODULES_COMMIT, DROZER_MODULES_LICENSE,
    DROZER_PORT,
    enumerate_core_modules, enumerate_external_modules,
)
from drozer_risk import get_risk, get_attck, load_overrides  # noqa: E402

PROVIDER_ID = "drozer"
PROVIDER_LABEL = "Drozer"
SCRIPT_PREFIX = "DROZER - "
CATEGORY_PREFIX = "mobile/drozer"

# Package-level runtime tags shared by every executable Script.
BASE_TAGS = {
    "drozer_serial": {
        "key": "drozer_serial",
        "label": "ADB Serial / Device",
        "description": "ADB serial of the Android device (emulator or physical). Blank auto-selects the single connected device.",
        "default": "", "example": "emulator-5554", "sensitive": False, "required": False, "parameter_class": "value",
    },
    "drozer_runtime_dir": {
        "key": "drozer_runtime_dir",
        "label": "Drozer Runtime Dir",
        "description": "Path to the isolated pinned drozer runtime on the Mobile Lab Host (e.g. C:/ProgramData/Morgana/mobile-lab/runtimes/drozer/3.2.0).",
        "default": "C:/ProgramData/Morgana/mobile-lab/runtimes/drozer/3.2.0",
        "example": "C:/ProgramData/Morgana/mobile-lab/runtimes/drozer/3.2.0",
        "sensitive": False, "required": False, "parameter_class": "value",
    },
}

RISK_ORDER = ("observe", "interact", "modify", "disrupt")


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _compact(text: str, limit: int) -> str:
    text = (text or "").strip().replace("\n", " ").replace("\r", " ")
    return text if len(text) <= limit else text[: limit - 3] + "..."


def _slug(value: str) -> str:
    import re
    return re.sub(r"[^a-z0-9_]+", "_", (value or "").lower()).strip("_")


def option_tag(arg: dict, key: str) -> dict:
    t = str(arg.get("type") or "string").lower()
    return {
        "key": key,
        "label": arg.get("name", key).replace("_", " ").title(),
        "description": _compact(arg.get("help") or arg.get("name") or key, 300),
        "default": "" if arg.get("default") is None else str(arg.get("default")),
        "example": "",
        "sensitive": False,
        "required": bool(arg.get("required")),
        "parameter_class": "value",
        "tag_type": t if t in {"string", "boolean", "integer", "float"} else "string",
        "_flag": arg.get("flag"),
        "_positional": bool(arg.get("positional")),
    }


def _runner_command(record: dict) -> str:
    """Build the `python -c` command executed by the Morgana python executor.

    Imports the runner asset, resolves the drozer console binary, performs the
    ADB forward, invokes `drozer console connect -c "run <fqmn> <args>"`, and
    prints a MORGANA_RESULT_METADATA marker line.
    """
    fqmn = record["fqmn"]
    lines = [
        "import importlib.util as _iu, json as _j, os as _o, sys as _s",
        "_spec=_iu.spec_from_file_location('_mdr', r'{{asset:drozer_runner}}')",
        "_m=_iu.module_from_spec(_spec);_spec.loader.exec_module(_m)",
        "_serial=str('#{drozer_serial}'.strip())",
        "_runtime=str('#{drozer_runtime_dir}'.strip())",
        "_args=[]",
    ]
    for arg in record.get("options", []):
        name = arg.get("name") or ""
        flag = arg.get("flag")
        action = arg.get("action")
        positional = bool(arg.get("positional"))
        key = f"drozer_{_slug(fqmn)}_{_slug(name)}"
        if positional:
            lines.append(f"_args.append(str('#{{{key}}}'.strip())) if '#{{{key}}}'.strip() else None")
        elif action == "store_true":
            lines.append(f"_args.append('{flag}') if '#{{{key}}}'.strip().lower() in ('1','true','yes','on') else None")
        else:
            lines.append(f"_args.append('{flag}') if '#{{{key}}}'.strip() else None")
            lines.append(f"_args.append(str('#{{{key}}}'.strip())) if '#{{{key}}}'.strip() else None")
    lines += [
        f"_r=_m.run_drozer_module(fqmn={fqmn!r}, args=_args, serial=_serial, runtime_dir=_runtime)",
        "print('MORGANA_RESULT_METADATA='+_j.dumps(_r))",
        "_s.exit(0 if _r.get('success') else 1)",
    ]
    return "\n".join(lines)


def script_from(record: dict, overrides: dict) -> dict[str, Any]:
    fqmn = record["fqmn"]
    attck = get_attck(fqmn)
    tcode = attck.get("tcode", "T0000")
    tactic = attck.get("tactic", "Mobile Application Security Assessment")
    risk = get_risk(fqmn, record.get("name") or "", overrides)
    collection = record["collection"]
    repo = DROZER_REPO if collection == "core" else DROZER_MODULES_REPO
    commit = record["commit"]

    options = record.get("options", [])
    required_tags = ["drozer_serial", "drozer_runtime_dir"]
    for arg in options:
        required_tags.append(f"drozer_{_slug(fqmn)}_{_slug(arg.get('name') or '')}")

    license_ = record.get("license") or (DROZER_LICENSE if collection == "core" else "UNSET")

    return {
        "id": record["script_id"],
        "name": f"{SCRIPT_PREFIX}{fqmn}",
        "description": _compact(record.get("description") or record.get("name") or fqmn, 900),
        "tactic": tactic,
        "tcode": tcode,
        "executor": "python",
        "executor_config": {"timeout_seconds": 180, "result_parser": "morgana-marker-v1"},
        "platform": "all",
        "command": _runner_command(record),
        "cleanup_command": None,
        "required_tags": required_tags,
        "required_assets": ["drozer_runner"],
        "operational_risk": risk,
        "source_metadata": {
            "provider": PROVIDER_ID,
            "source_provider": "drozer",
            "source_id": record["script_id"],
            "source_repository": f"https://github.com/{repo}",
            "source_commit": commit,
            "source_release": DROZER_VERSION,
            "source_path": record.get("source_path"),
            "source_file": record.get("source_file"),
            "source_sha256": record.get("source_sha256"),
            "code_sha256": record.get("code_sha256"),
            "module_name": record.get("name"),
            "namespace": record.get("namespace"),
            "fqmn": fqmn,
            "source_collection": collection,
            "target_platform": "android",
            "execution_platform": "host-agent",
            "runtime_mode": "drozer-console-noninteractive",
            "requires_drozer": True,
            "mobile_lab_compatible": True,
            "has_options": bool(options),
            "options": options,
            "mitre_domain": "mobile-attack",
            "mitre_tcode": tcode if tcode != "T0000" else None,
            "mitre_mapping_status": "mapped" if tcode != "T0000" else "unmapped",
            "license": license_,
            "distribution_status": "vendored",
            "readiness": "ready_with_target",
            "quality_tier": "A" if collection == "core" else "B",
            "author": record.get("author") or "Unspecified",
        },
    }


def build_packages(scripts: list[dict]) -> list[tuple[dict, str]]:
    groups: dict[str, list[dict]] = defaultdict(list)
    for s in scripts:
        ns = (s["source_metadata"].get("namespace") or "uncategorized").split(".")[0]
        groups[ns].append(s)

    packages: list[tuple[dict, str]] = []
    for namespace, group in sorted(groups.items()):
        package_id = f"drozer-{namespace}-v1"
        risks = sorted({s["operational_risk"] for s in group}, key=RISK_ORDER.index)
        tcodes = sorted({s["tcode"] for s in group if s["tcode"] != "T0000"})
        option_count = sum(1 for s in group if s["source_metadata"].get("has_options"))
        core_count = sum(1 for s in group if s["source_metadata"].get("source_collection") == "core")
        ext_count = len(group) - core_count

        tags = [dict(BASE_TAGS["drozer_serial"]), dict(BASE_TAGS["drozer_runtime_dir"])]
        seen_keys = {"drozer_serial", "drozer_runtime_dir"}
        for s in group:
            for opt in s["source_metadata"].get("options") or []:
                key = f"drozer_{_slug(s['source_metadata']['fqmn'])}_{_slug(opt.get('name') or '')}"
                if key and key not in seen_keys:
                    seen_keys.add(key)
                    tags.append(option_tag(opt, key))

        package = {
            "package_id": package_id,
            "package_name": f"Drozer - {namespace.title()}",
            "version": "1.0.0",
            "summary": f"{len(group)} Drozer modules in the {namespace} namespace ({core_count} core, {ext_count} external).",
            "description": "Source-faithful Drozer Android application-security modules (ReversecLabs/drozer + drozer-modules) executed through the pinned drozer runtime on a Morgana Mobile Lab Host.",
            "purpose": "Run authorized Android application-model assessment: packages, activities, services, broadcast receivers, content providers, permissions, Intents/IPC, and scanners.",
            "capabilities": [
                f"Contains {len(group)} Drozer modules ({option_count} with runtime Options).",
                f"Target platform: android; risk mix: {', '.join(risks)}.",
                f"Mobile ATT&CK mappings: {len(tcodes)} techniques ({', '.join(tcodes) if tcodes else 'none'}).",
            ],
            "use_cases": [
                "Assess an explicitly authorized Android application through a Morgana Mobile Lab device.",
                "Enumerate package/component/permission attack surface and validate detection coverage.",
            ],
            "prerequisites": [
                "Morgana Mobile Lab Host with an isolated pinned drozer runtime and drozer-agent installed on the target device.",
                "Authorized Android Emulator or Physical Android device.",
                "drozer console connect over ADB forward tcp:31415.",
            ],
            "safety_notes": [
                "Modules in the exploit/shell namespaces can modify or disrupt device/app state; review risk metadata before execution.",
                "Use only on authorized targets; physical devices are non-destructive by default.",
            ],
            "author": "MWR InfoSecurity / ReversecLabs / X3M.AI conversion",
            "created": str(date.today()),
            "script_prefix": SCRIPT_PREFIX,
            "provider": PROVIDER_ID,
            "source": PROVIDER_ID,
            "source_repository": f"https://github.com/{DROZER_REPO}",
            "source_license": DROZER_LICENSE,
            "documentation_url": f"https://github.com/{DROZER_REPO}",
            "mitre_domain": "mobile-attack",
            "mitre_tactic": "Mobile Application Security Assessment",
            "mitre_tcodes": tcodes,
            "platform": ["android"],
            "risk_badges": risks,
            "category": f"{CATEGORY_PREFIX}/{namespace}",
            "target_platform_counts": {"android": len(group)},
            "frameworks": ["drozer"],
            "tag_categories": [{
                "category_id": f"drozer_{namespace}_params",
                "label": f"Drozer {namespace.title()} Parameters",
                "description": f"Host-to-device Drozer target and {namespace} module arguments.",
                "scope": "local",
                "tags": tags,
            }],
            "assets": [{
                "id": "drozer_runner",
                "name": "morgana_drozer_runner.py",
                "filename": "morgana_drozer_runner.py",
                "platform": "all",
                "architecture": "any",
                "url": f"{CATALOG_BASE_URL}/runtime/morgana_drozer_runner.py",
                "sha256": _runner_sha256(),
                "size": RUNNER_ASSET.stat().st_size if RUNNER_ASSET.exists() else None,
                "executable": False,
                "source": f"https://github.com/{DROZER_REPO}",
                "license": DROZER_LICENSE,
            }],
            "scripts": group,
            "chains": [],
        }
        relative = f"{namespace}/{package_id}.json"
        packages.append((package, relative))
    return packages


def _runner_sha256() -> str:
    if RUNNER_ASSET.exists():
        return hashlib.sha256(RUNNER_ASSET.read_bytes()).hexdigest()
    return "pending-build"


def catalog_entry(package: dict, relative: str) -> dict[str, Any]:
    fields = (
        "package_id", "package_name", "version", "summary", "description", "purpose",
        "capabilities", "use_cases", "prerequisites", "safety_notes", "provider", "category",
        "platform", "mitre_tactic", "mitre_tcodes", "mitre_domain", "source", "source_license",
        "documentation_url", "risk_badges", "target_platform_counts",
    )
    return {key: package[key] for key in fields} | {
        "script_count": len(package["scripts"]), "chain_count": 0,
        "asset_count": len(package.get("assets", [])),
        "status": "community", "author": package["author"],
        "url": f"{CATALOG_BASE_URL}/{relative}",
    }


def update_catalog(entries: list[dict], provider: dict, categories: list[dict]) -> None:
    catalog = json.loads(CATALOG_FILE.read_text(encoding="utf-8"))
    catalog["packs"] = [e for e in catalog.get("packs", []) if e.get("provider") != PROVIDER_ID] + entries
    catalog["updated"] = str(date.today())
    catalog["providers"] = [e for e in catalog.get("providers", []) if e.get("id") != PROVIDER_ID] + [provider]
    category_ids = {c["id"] for c in categories}
    catalog["categories"] = [e for e in catalog.get("categories", []) if e.get("id") not in category_ids] + categories
    _write_json(CATALOG_FILE, catalog)


def update_classification() -> None:
    text = CLASSIFICATION_FILE.read_text(encoding="utf-8")

    # 1. facet_metadata.providers (after medusa)
    if '"id": "drozer"' not in text:
        anchor = '{"id": "medusa",            "label": "MEDUSA"}\n    ],'
        if anchor in text:
            text = text.replace(
                anchor,
                '{"id": "medusa",            "label": "MEDUSA"},\n'
                '      {"id": "drozer",           "label": "Drozer"}\n    ],',
            )

    # 2. provider_overrides (after medusa block)
    po_anchor = (
        '    "medusa": {\n'
        '      "package_types":      ["runtime-instrumentation", "procedure-library"],\n'
        '      "specialties":        ["mobile", "runtime-instrumentation"],\n'
        '      "execution_platforms":["host-agent"]\n'
        '    }\n'
        '  },'
    )
    if po_anchor in text:
        text = text.replace(
            po_anchor,
            '    "medusa": {\n'
            '      "package_types":      ["runtime-instrumentation", "procedure-library"],\n'
            '      "specialties":        ["mobile", "runtime-instrumentation"],\n'
            '      "execution_platforms":["host-agent"]\n'
            '    },\n'
            '    "drozer": {\n'
            '      "package_types":      ["application-security", "procedure-library"],\n'
            '      "specialties":        ["mobile", "android", "application-security"],\n'
            '      "execution_platforms":["host-agent"],\n'
            '      "target_environments":["android"]\n'
            '    }\n'
            '  },',
        )

    # 3. category_overrides (after mobile/medusa lines)
    co_anchor = '"mobile/medusa/ios":'
    if co_anchor in text and '"mobile/drozer/app":' not in text:
        line_anchor = None
        for line in text.splitlines():
            if line.lstrip().startswith('"mobile/medusa/ios":'):
                line_anchor = line
                break
        if line_anchor is not None:
            drozer_ns = ["app", "auxiliary", "exploit", "information", "post", "scanner", "shell", "tools"]
            extra = "\n".join(
                f'    "mobile/drozer/{ns}":                   {{"target_environments": ["android"], "specialties": ["mobile", "android", "application-security"]}},'
                for ns in drozer_ns
            )
            text = text.replace(line_anchor, line_anchor + "\n" + extra)

    CLASSIFICATION_FILE.write_text(text, encoding="utf-8")


def reconcile(records: list[dict]) -> dict:
    core = [r for r in records if r.get("collection") == "core"]
    ext = [r for r in records if r.get("collection") == "drozer-modules"]

    def summary(rs):
        c = Counter(r.get("status") for r in rs)
        return {
            "candidates": len(rs),
            "executable": c.get("EXECUTABLE", 0),
            "manual": c.get("MANUAL", 0),
            "support": c.get("SUPPORT", 0),
            "framework_internal": c.get("FRAMEWORK_INTERNAL", 0),
            "aliases": c.get("ALIAS", 0),
            "legacy": c.get("LEGACY_COMPATIBLE", 0),
            "incompatible": c.get("INCOMPATIBLE", 0),
            "license_blocked": c.get("LICENSE_BLOCKED", 0),
            "parse_errors": c.get("PARSE_ERROR", 0),
        }

    core_sum = summary(core)
    ext_sum = summary(ext)

    def accounted(s):
        return (s["executable"] + s["manual"] + s["support"] + s["framework_internal"]
                + s["aliases"] + s["legacy"] + s["incompatible"]
                + s["license_blocked"] + s["parse_errors"])

    core_ok = accounted(core_sum) == core_sum["candidates"]
    ext_ok = accounted(ext_sum) == ext_sum["candidates"]
    return {
        "core": core_sum, "external": ext_sum,
        "core_reconciled": core_ok, "external_reconciled": ext_ok,
        "silent_loss": 0 if (core_ok and ext_ok) else (core_sum["candidates"] + ext_sum["candidates"] - accounted(core_sum) - accounted(ext_sum)),
        "suppressed_medusa": 0, "suppressed_frida_mobile": 0, "suppressed_semantic": 0,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the complete Drozer provider corpus")
    parser.add_argument("--core-source", type=Path, default=DEFAULT_CORE_SOURCE)
    parser.add_argument("--modules-source", type=Path, default=DEFAULT_MODULES_SOURCE)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--no-update-catalog", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if not (args.core_source / "src" / "drozer" / "modules").is_dir():
        print(f"[FAIL] drozer core source not found: {args.core_source}")
        return 1

    overrides = load_overrides()
    core, core_err = enumerate_core_modules(args.core_source)
    ext, ext_err = enumerate_external_modules(args.modules_source)
    records = core + ext

    executable = [r for r in records if r.get("status") == "EXECUTABLE"]
    scripts = [script_from(r, overrides) for r in executable]
    packages = build_packages(scripts)
    recon = reconcile(records)

    # Write inventory + conversion report + reconciliation
    inventory = {
        "generated": str(date.today()),
        "drozer": {"repository": f"https://github.com/{DROZER_REPO}", "commit": DROZER_COMMIT,
                    "version": DROZER_VERSION, "license": DROZER_LICENSE},
        "drozer_agent": {"repository": f"https://github.com/{DROZER_AGENT_REPO}", "commit": DROZER_AGENT_COMMIT,
                          "license": DROZER_AGENT_LICENSE, "package": DROZER_AGENT_PACKAGE},
        "drozer_modules": {"repository": f"https://github.com/{DROZER_MODULES_REPO}", "commit": DROZER_MODULES_COMMIT,
                            "license": DROZER_MODULES_LICENSE},
        "candidates": records,
    }
    report = {
        "generated": str(date.today()),
        "core": recon["core"],
        "external": recon["external"],
        "total_candidates": len(records),
        "published_scripts": len(scripts),
        "packages": len(packages),
        "namespaces": sorted({p[0]["category"].split("/")[-1] for p in packages}),
        "modules_with_parameters": sum(1 for s in scripts if s["source_metadata"]["has_options"]),
        "unique_parameters": len({t["key"] for p in packages for t in p[0]["tag_categories"][0]["tags"]}),
        "reconciliation": recon,
    }

    if args.dry_run:
        print(json.dumps(report, indent=2))
        return 0

    out = args.out_dir
    _write_json(out / "drozer-source-inventory.json", inventory)
    _write_json(out / "drozer-conversion-report.json", report)
    for package, relative in packages:
        _write_json(out / relative, package)

    entries = [catalog_entry(p, rel) for p, rel in packages]
    if not args.no_update_catalog:
        provider = {
            "id": PROVIDER_ID, "label": PROVIDER_LABEL,
            "description": "Drozer Android application-security modules (core + drozer-modules).",
            "source_repository": f"https://github.com/{DROZER_REPO}",
            "source_license": DROZER_LICENSE,
        }
        categories = [{"id": f"{CATEGORY_PREFIX}/{ns}", "label": f"Drozer {ns.title()}"}
                      for ns in sorted({p[0]["category"].split("/")[-1] for p in packages})]
        update_catalog(entries, provider, categories)
        update_classification()

    print(f"[DROZER] core candidates={recon['core']['candidates']} executable={recon['core']['executable']}")
    print(f"[DROZER] external candidates={recon['external']['candidates']} executable={recon['external']['executable']}")
    print(f"[DROZER] published scripts={len(scripts)} packages={len(packages)}")
    print(f"[DROZER] reconciled core={recon['core_reconciled']} external={recon['external_reconciled']} silent_loss={recon['silent_loss']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
