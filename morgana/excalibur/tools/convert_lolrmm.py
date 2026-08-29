#!/usr/bin/env python3
"""
convert_lolrmm.py — Generate Morgana Excalibur packages for LOLRMM.

Parses all 320 LOLRMM YAML files, generates one logical profile per tool
(probe-capable bash command or manual intelligence record), groups by platform,
and writes deterministic Camelot package JSON + catalog entries.

Usage:
    python convert_lolrmm.py --source-dir C:/path/to/lolrmm \
        --out-dir morgana/excalibur/lotl/lolrmm \
        [--no-update-catalog] [--dry-run] [--verbose]
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent
CAMELOT_ROOT = TOOLS_DIR.parent.parent.parent

sys.path.insert(0, str(TOOLS_DIR))
from lolrmm_source import (
    enumerate_tools, get_source_commit,
    LOLRMM_COMMIT, LOLRMM_LICENSE, LOLRMM_REPO,
)

# ── ATT&CK enrichment ─────────────────────────────────────────────────────────
# T1219 = Remote Access Software — canonical LOLRMM mapping
T1219_ENRICHMENT = {
    "technique": "T1219",
    "tactic": "command-and-control",
    "mapping_source": "morgana-provider-enrichment",
}

# ── Platform grouping ──────────────────────────────────────────────────────────
def _primary_package(platforms: list[str], probe_capable: bool) -> str:
    if not probe_capable:
        return "manual"
    if not platforms:
        return "manual"
    if "windows" in platforms and len(platforms) == 1:
        return "windows"
    if "linux" in platforms and len(platforms) == 1:
        return "linux"
    if "macos" in platforms and len(platforms) == 1:
        return "macos"
    return "multiplatform"


# ── Script command builders ────────────────────────────────────────────────────

def _manifest_json(tool: dict) -> str:
    """Build a compact inline JSON artifact manifest for the probe command."""
    a = tool["artifacts"]
    manifest = {
        "tool": tool["name"],
        "tool_id": tool["tool_id"],
        "files": [f["path"] for f in a["files"][:20]],
        "filenames": a["filenames"][:20],
        "registry": [r["key"] for r in a["registry"][:15]],
        "domains": a["domains"][:10],
        "file_hashes": [
            {"filename": h["filename"], "sha256": h["sha256"][:16] + "..."}
            for h in tool.get("file_hashes", [])[:5]
        ],
    }
    return json.dumps(manifest, separators=(",", ":"))


def _build_probe_command(tool: dict) -> str:
    """Generate a read-only artifact presence probe command (bash/sh)."""
    name = tool["name"]
    tid  = tool["tool_id"]
    manifest = _manifest_json(tool)
    a = tool["artifacts"]

    lines = [
        f"# LOLRMM Artifact Presence Probe — {name}",
        "# Read-only: checks for known artifacts. Does NOT install or modify anything.",
        "",
        f"TOOL_ID='{tid}'",
        f"TOOL_NAME='{name.replace(chr(39), chr(39)+chr(92)+chr(39)+chr(39))}'",
        "",
        "result_files=(); result_registry=(); result_hashes=(); evidence='no-evidence-found'",
        "",
    ]

    # File/path probes
    paths_to_check = [f["path"] for f in a["files"] if f.get("path")]
    for fn in a["filenames"][:10]:
        # Skip wildcards as direct path checks
        if "*" not in fn and "/" in fn or "\\" in fn:
            paths_to_check.append(fn)
    for p in paths_to_check[:15]:
        safe = p.replace("'", "\\'")
        lines.append(f"[ -e '{safe}' ] && result_files+=(\"{safe}\") && evidence='evidence-found'")

    # Registry (Linux: skip, macOS: skip; Windows via PowerShell would be different)
    # For bash probe we check if running on Windows via $OSTYPE or uname
    if a["registry"]:
        lines += [
            "# Registry check — Windows PowerShell fallback",
            "if command -v powershell.exe >/dev/null 2>&1 || command -v pwsh >/dev/null 2>&1; then",
            "  PS_CMD=$(command -v pwsh 2>/dev/null || command -v powershell.exe)",
        ]
        for reg in a["registry"][:8]:
            key = reg["key"].replace("'", "\\'")
            lines.append(f"  '$PS_CMD' -NoProfile -NonInteractive -Command "
                         f"\"if(Test-Path '{key}'){{Write-Output 'REG_FOUND:{key}'}}\" 2>/dev/null "
                         f"&& result_registry+=('{key}') && evidence='evidence-found'")
        lines.append("fi")

    # Emit structured result
    lines += [
        "",
        "files_json=$(printf '%s\\n' \"${result_files[@]}\" | python3 -c 'import json,sys; print(json.dumps(sys.stdin.read().splitlines()))' 2>/dev/null || echo '[]')",
        "reg_json=$(printf '%s\\n' \"${result_registry[@]}\" | python3 -c 'import json,sys; print(json.dumps(sys.stdin.read().splitlines()))' 2>/dev/null || echo '[]')",
        "",
        f'echo "MORGANA_RESULT_METADATA={{\\\"provider\\\":\\\"lolrmm\\\",\\\"tool\\\":\\\"$TOOL_NAME\\\",\\\"tool_id\\\":\\\"$TOOL_ID\\\",\\\"status\\\":\\\"completed\\\",\\\"presence\\\":\\\"$evidence\\\",\\\"evidence\\\":{{\\\"files\\\":$files_json,\\\"registry\\\":$reg_json}}}}"',
        f'echo "[INFO] LOLRMM probe complete: $TOOL_NAME ($evidence)"',
    ]
    return "\n".join(lines)


def _build_manual_command(tool: dict) -> str:
    name = tool["name"]
    tid  = tool["tool_id"]
    website = tool.get("website","")
    caps = ", ".join(tool.get("capabilities", [])[:5]) or "Remote access"
    domains = ", ".join(tool["artifacts"].get("domains", [])[:5])
    return "\n".join([
        f"# LOLRMM Intelligence Profile — {name}",
        f"# This record contains RMM intelligence but no directly probeable local artifacts.",
        f"# Use this profile for threat hunting, detection engineering, and app-control review.",
        "#",
        f"# Tool: {name}",
        f"# Category: {tool.get('category','')}",
        f"# Website: {website}",
        f"# Capabilities: {caps}",
        f"# Known domains: {domains}" if domains else "# Known domains: (none)",
        f"# Platforms: {', '.join(tool.get('platforms','')) or 'unknown'}",
        "#",
        f'echo "MORGANA_RESULT_METADATA={{\\\"provider\\\":\\\"lolrmm\\\",\\\"tool\\\":\\\"{name}\\\",\\\"tool_id\\\":\\\"{tid}\\\",\\\"status\\\":\\\"manual\\\",\\\"presence\\\":\\\"not-applicable\\\"}}"',
    ])


def _build_script(tool: dict, source_commit: str) -> dict:
    name     = tool["name"]
    probe    = tool["probe_capable"]
    plats    = tool.get("platforms", [])
    a        = tool["artifacts"]
    dets     = tool.get("detections", [])
    caps     = tool.get("capabilities", [])
    domains  = a.get("domains", [])
    ports    = a.get("ports", [])

    if probe:
        executor = "bash"
        cmd      = _build_probe_command(tool)
        script_name = f"LOLRMM - {name} - Artifact Presence Validation"
        description = (
            f"LOLRMM artifact-presence probe for {name}. "
            f"Read-only check of source-described endpoint artifacts. "
            f"{tool.get('description','')[:300]}"
        )
    else:
        executor = "manual"
        cmd      = _build_manual_command(tool)
        script_name = f"LOLRMM - {name} - Detection Profile"
        description = (
            f"LOLRMM intelligence profile for {name} (no probeable local artifacts). "
            f"{tool.get('description','')[:300]}"
        )

    sigma_urls = [d.get("sigma_url","") for d in dets if d.get("sigma_url")]

    return {
        "id": tool["tool_id"],
        "name": script_name,
        "description": description,
        "tactic": "Command and Control",
        "tcode": "T1219",
        "executor": executor,
        "executor_config": {"timeout_seconds": 60, "result_parser": "morgana-marker-v1"},
        "platform": "linux",
        "command": cmd,
        "cleanup_command": None,
        "required_tags": [],
        "required_assets": [],
        "operational_risk": "observe",
        "source_metadata": {
            "provider": "lolrmm",
            "source_repository": LOLRMM_REPO,
            "source_commit": source_commit,
            "source_file": tool["source_file"],
            "source_name": name,
            "source_category": tool.get("category",""),
            "source_author": tool.get("author",""),
            "source_created": tool.get("created",""),
            "source_last_modified": tool.get("last_modified",""),
            "website": tool.get("website",""),
            "platforms": plats,
            "capabilities": caps,
            "privileges": tool.get("privileges",""),
            "probe_mode": "artifact-presence" if probe else "manual-intelligence",
            "artifact_summary": {
                "files": len(a.get("files",[])),
                "filenames": len(a.get("filenames",[])),
                "registry": len(a.get("registry",[])),
                "event_logs": len(a.get("event_logs",[])),
                "domains": len(a.get("domains",[])),
                "file_hashes": len(tool.get("file_hashes",[])),
            },
            "domains": domains[:20],
            "ports": ports[:10],
            "pe_filenames": [pe.get("filename","") for pe in tool.get("pe_metadata",[]) if pe.get("filename")][:10],
            "sigma_urls": sigma_urls[:10],
            "code_signing": tool.get("code_signing",[]),
            "attck_enrichment": [T1219_ENRICHMENT],
            "source_modified": False,
        },
    }


# ── Package builder ────────────────────────────────────────────────────────────

_PKG_META = {
    "windows":      ("lolrmm-windows-v1",      "LOLRMM — Windows",       ["windows"]),
    "linux":        ("lolrmm-linux-v1",         "LOLRMM — Linux",         ["linux"]),
    "macos":        ("lolrmm-macos-v1",         "LOLRMM — macOS",         ["macos"]),
    "multiplatform":("lolrmm-multiplatform-v1", "LOLRMM — Multi-platform",["windows","linux","macos"]),
    "manual":       ("lolrmm-manual-v1",        "LOLRMM — Intelligence Profiles",["windows","linux","macos"]),
}

_PKG_DESC = {
    "windows":       "Read-only artifact-presence probes for Windows RMM/RAT tools from the LOLRMM catalog. Checks file paths, filenames, registry keys, and known artifacts.",
    "linux":         "Read-only artifact-presence probes for Linux RMM/RAT tools from the LOLRMM catalog.",
    "macos":         "Read-only artifact-presence probes for macOS RMM/RAT tools from the LOLRMM catalog.",
    "multiplatform": "Read-only artifact-presence probes for cross-platform RMM/RAT tools from the LOLRMM catalog.",
    "manual":        "Intelligence-only profiles for LOLRMM tools that lack directly probeable local artifacts. Use for threat hunting, detection engineering, and application-control policy design.",
}


def build_packages(tools: list[dict], source_commit: str) -> list[dict]:
    groups: dict[str, list[dict]] = {k: [] for k in _PKG_META}
    for tool in tools:
        key = _primary_package(tool.get("platforms",[]), tool["probe_capable"])
        groups[key].append(_build_script(tool, source_commit))

    packages = []
    for key, scripts in groups.items():
        if not scripts:
            continue
        pkg_id, pkg_name, plats = _PKG_META[key]
        all_domains = []
        for s in scripts:
            all_domains.extend(s["source_metadata"].get("domains", []))
        packages.append({
            "package_id": pkg_id,
            "package_name": pkg_name,
            "version": "1.0.0",
            "summary": f"{len(scripts)} LOLRMM RMM/RAT {'artifact probes' if key != 'manual' else 'intelligence profiles'}.",
            "description": _PKG_DESC[key],
            "purpose": "Threat hunting, detection validation, and application-control policy design for known RMM/RAT tools.",
            "capabilities": [
                f"{len(scripts)} LOLRMM tool profiles.",
                "Read-only artifact-presence validation where source data permits." if key != "manual" else "Intelligence metadata for detection engineering.",
                "Elastic Endpoint/SIEM, Sigma, and ATT&CK metadata included.",
                "T1219 (Remote Access Software) enrichment on all profiles.",
            ],
            "use_cases": [
                "Detect unauthorized RMM tool presence on endpoints.",
                "Validate detection rules for Remote Access Software (T1219).",
                "Design application-control policies using known artifact paths.",
            ],
            "prerequisites": ["Read-only endpoint access."] if key != "manual" else ["Review only — no runtime execution needed."],
            "safety_notes": [
                "Probes are read-only and do not install, modify, or remove software.",
                "LOLRMM catalogs legitimate tools that can be abused. Presence does not imply compromise.",
                "Use only in authorized environments.",
            ],
            "author": "MagicSword / LOLRMM / X3M.AI integration",
            "created": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "provider": "lolrmm",
            "source": "lolrmm",
            "source_repository": f"https://github.com/{LOLRMM_REPO}",
            "source_commit": source_commit,
            "source_license": LOLRMM_LICENSE,
            "documentation_url": "https://lolrmm.io/",
            "mitre_domain": "enterprise-attack",
            "mitre_tactic": "Command and Control",
            "mitre_tcodes": ["T1219"],
            "platform": sorted(set(plats)),
            "category": f"lotl/lolrmm/{key}",
            "specialties": ["living-off-the-land", "remote-access", "rmm", "detection-validation", "threat-hunting"],
            "package_types": ["procedure-library", "detection-validation"],
            "execution_platforms": sorted(set(plats)),
            "target_environments": ["endpoint"] + sorted(set(plats)),
            "risk_badges": ["observe"],
            "tag_categories": [],
            "assets": [],
            "scripts": scripts,
            "chains": [],
        })
    return packages


def update_catalog(catalog_path: Path, packages: list[dict]) -> None:
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    packs = catalog.get("packs", [])
    for pkg in packages:
        pid = pkg["package_id"]
        packs = [e for e in packs if e.get("package_id") != pid]
        packs.append({
            "package_id": pid, "package_name": pkg["package_name"],
            "version": pkg["version"], "description": pkg["description"],
            "capabilities": pkg["capabilities"], "use_cases": pkg["use_cases"],
            "safety_notes": pkg["safety_notes"],
            "mitre_tactic": pkg["mitre_tactic"], "mitre_tcodes": pkg["mitre_tcodes"],
            "script_count": len(pkg["scripts"]), "chain_count": 0,
            "platform": pkg["platform"], "prerequisites": pkg["prerequisites"],
            "sentinel_connectors": [], "status": "community",
            "provider": pkg["provider"], "author": pkg["author"],
            "category": pkg["category"], "url": pkg["documentation_url"],
        })
    catalog["packs"] = packs
    catalog["updated"] = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    catalog_path.write_text(json.dumps(catalog, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"[INFO] Catalog: {len(packages)} LOLRMM packages, total={len(packs)}")


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--source-dir", required=True)
    p.add_argument("--out-dir", required=True)
    p.add_argument("--catalog", default=str(CAMELOT_ROOT / "morgana/excalibur/catalog.json"))
    p.add_argument("--no-update-catalog", action="store_true")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--verbose", action="store_true")
    args = p.parse_args()

    source_dir = Path(args.source_dir)
    out_dir = Path(args.out_dir)
    source_commit = get_source_commit(source_dir)

    print(f"[LOLRMM] Enumerating tools from {source_dir}...")
    tools, errors = enumerate_tools(source_dir, source_commit)
    print(f"[LOLRMM] Commit: {source_commit}")
    print(f"[LOLRMM] Tools: {len(tools)} valid, {len(errors)} errors")

    if args.dry_run:
        for key in ("windows","linux","macos","multiplatform","manual"):
            c = sum(1 for t in tools if _primary_package(t.get("platforms",[]),t["probe_capable"])==key)
            print(f"  {key}: {c}")
        return 0

    packages = build_packages(tools, source_commit)
    total = sum(len(p["scripts"]) for p in packages)
    print(f"[LOLRMM] Generated {total} Scripts in {len(packages)} packages")

    # Write packages
    pkg_dir = out_dir / "packages"
    pkg_dir.mkdir(parents=True, exist_ok=True)
    for pkg in packages:
        out = pkg_dir / f"{pkg['package_id']}.json"
        out.write_text(json.dumps(pkg, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        if args.verbose:
            print(f"[OK] {out.name} ({len(pkg['scripts'])} scripts)")

    # Source inventory
    inventory = [
        {k: v for k, v in t.items()
         if k not in ("artifacts", "pe_metadata", "code_signing", "file_hashes", "acknowledgements")}
        for t in tools
    ]
    (out_dir / "source-inventory.json").write_text(json.dumps(inventory, indent=2, default=str) + "\n", encoding="utf-8")

    # Conversion report
    probe_cnt = sum(1 for t in tools if t["probe_capable"])
    manual_cnt = len(tools) - probe_cnt
    plat_counts = {k: sum(1 for t in tools if k in t.get("platforms",[])) for k in ("windows","linux","macos")}
    multi_cnt = sum(1 for t in tools if len(t.get("platforms",[])) > 1)
    report = {
        "source_repository": f"https://github.com/{LOLRMM_REPO}",
        "source_commit": source_commit,
        "source_license": LOLRMM_LICENSE,
        "total_tools": len(tools),
        "probe_capable": probe_cnt,
        "manual_only": manual_cnt,
        "platforms": plat_counts,
        "multi_platform": multi_cnt,
        "with_pe_metadata": sum(1 for t in tools if t.get("pe_metadata")),
        "with_installation_paths": sum(1 for t in tools if t.get("installation_paths")),
        "with_disk_artifacts": sum(1 for t in tools if t.get("has_files")),
        "with_registry": sum(1 for t in tools if t.get("has_registry")),
        "with_eventlog": sum(1 for t in tools if t.get("has_evtlog")),
        "with_network": sum(1 for t in tools if t.get("has_domains")),
        "with_file_hashes": sum(1 for t in tools if t.get("has_file_hashes")),
        "with_detections": sum(1 for t in tools if t.get("detections")),
        "with_capabilities": sum(1 for t in tools if t.get("capabilities")),
        "parse_errors": len(errors),
        "total_scripts": total,
        "packages": len(packages),
        "source_reconciled": True,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    (out_dir / "conversion-report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    if not args.no_update_catalog:
        catalog_path = Path(args.catalog)
        if catalog_path.exists():
            update_catalog(catalog_path, packages)

    print(f"\n[SUCCESS] LOLRMM provider generated:")
    print(f"  Commit:  {source_commit}")
    print(f"  Tools:   {len(tools)} ({probe_cnt} probe, {manual_cnt} manual)")
    print(f"  Scripts: {total}")
    print(f"  Packages:{len(packages)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
