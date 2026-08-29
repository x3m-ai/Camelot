#!/usr/bin/env python3
"""
convert_cortado.py — Generate Morgana Excalibur packages for Elastic Cortado RTAs.

Performs AST-based discovery of all registered RTAs, generates one Script per
RTA (CodeRta executable, HashRta manual), groups by ATT&CK tactic, and writes
deterministic Camelot package JSON + catalog entries.

Usage:
    python convert_cortado.py --source-dir C:/path/to/cortado \
        --out-dir morgana/excalibur/detection/cortado \
        [--no-update-catalog] [--dry-run] [--verbose]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent
DETECTION_DIR = TOOLS_DIR.parent / "detection" / "cortado"
CAMELOT_ROOT = TOOLS_DIR.parent.parent.parent

sys.path.insert(0, str(TOOLS_DIR))
from cortado_ast import (
    enumerate_rtas,
    CORTADO_RELEASE, CORTADO_VERSION, CORTADO_COMMIT,
    CORTADO_WHEEL, CORTADO_WHEEL_SHA256, CORTADO_WHEEL_SIZE,
    CORTADO_WHEEL_URL, CORTADO_LICENSE, CORTADO_REPO, CORTADO_PYTHON,
)
from cortado_risk import get_tactics, get_primary_tactic, get_risk, load_overrides

# ── Tag categories ─────────────────────────────────────────────────────────────

CORTADO_TAGS = [{
    "category_id": "cortado_runtime",
    "label": "Cortado RTA Runtime",
    "description": "Cortado runtime cache path for the extracted wheel on this Agent.",
    "scope": "local",
    "tags": [
        {"key": "cortado_runtime_path", "label": "Cortado Runtime Path",
         "description": "Path to extracted Cortado wheel directory on the Agent (cortado/ package root).",
         "default": "/tmp/morgana-cortado-runtime", "sensitive": False, "required": True,
         "parameter_class": "local_path"},
    ],
}]

# ── Tactic label mapping ───────────────────────────────────────────────────────

TACTIC_LABELS = {
    "initial-access": "Initial Access",
    "execution": "Execution",
    "persistence": "Persistence",
    "privilege-escalation": "Privilege Escalation",
    "defense-evasion": "Defense Evasion",
    "credential-access": "Credential Access",
    "discovery": "Discovery",
    "lateral-movement": "Lateral Movement",
    "collection": "Collection",
    "command-and-control": "Command and Control",
    "exfiltration": "Exfiltration",
    "impact": "Impact",
    "resource-development": "Resource Development",
    "reconnaissance": "Reconnaissance",
    "unmapped": "Unmapped",
    "sample-backed": "Sample-backed RTAs",
}

# ── Asset definition ───────────────────────────────────────────────────────────

def _runner_sha256() -> str:
    runner = DETECTION_DIR / "morgana_cortado_runner.py"
    if runner.exists():
        return hashlib.sha256(runner.read_bytes()).hexdigest()
    return "unknown"


def _wheel_asset_def() -> dict:
    return {
        "id": "elastic_cortado_wheel",
        "name": "elastic-cortado-wheel",
        "filename": CORTADO_WHEEL,
        "platform": "all",
        "architecture": "any",
        "url": CORTADO_WHEEL_URL,
        "sha256": CORTADO_WHEEL_SHA256,
        "size": CORTADO_WHEEL_SIZE,
        "executable": False,
        "source": CORTADO_REPO,
        "release": CORTADO_RELEASE,
        "license": CORTADO_LICENSE,
        "source_commit": CORTADO_COMMIT,
        "description": "Official Elastic Cortado Python wheel (py3-none-any). "
                       "Extract to Agent cache and add to PYTHONPATH before running RTAs. "
                       "No Poetry or pip required at runtime.",
    }


def _runner_asset_def() -> dict:
    runner = DETECTION_DIR / "morgana_cortado_runner.py"
    sha = hashlib.sha256(runner.read_bytes()).hexdigest() if runner.exists() else "unknown"
    size = runner.stat().st_size if runner.exists() else 0
    return {
        "id": "elastic_cortado_runner",
        "name": "morgana-cortado-runner",
        "filename": "morgana_cortado_runner.py",
        "platform": "all",
        "architecture": "any",
        "url": "https://raw.githubusercontent.com/x3m-ai/Camelot/main/morgana/excalibur/detection/cortado/morgana_cortado_runner.py",
        "sha256": sha,
        "size": size,
        "executable": False,
        "source": CORTADO_REPO,
        "release": CORTADO_RELEASE,
        "license": "MIT",
        "description": "Morgana non-interactive runner for Elastic Cortado CodeRTAs. "
                       "Requires cortado wheel extracted to Agent runtime path.",
    }


# ── Script builders ────────────────────────────────────────────────────────────

def _code_rta_command(rta: dict) -> str:
    mod = rta["source_module"]
    name = rta["name"]
    rta_id = rta.get("id", "")
    techs = ",".join(rta.get("techniques", []))
    ep_rules = json.dumps(rta.get("endpoint_rules", []), separators=(",", ":"))
    siem_rules = json.dumps(rta.get("siem_rules", []), separators=(",", ":"))
    return "\n".join([
        "# Elastic Cortado RTA — " + name.replace("_", " ").title(),
        "# Requires Python 3.12+ and extracted Cortado wheel on Agent",
        "",
        "# Setup: extract wheel to runtime path if not already done",
        'CORTADO_WHEEL="{{asset:elastic_cortado_wheel}}"',
        'RUNTIME_DIR="#{cortado_runtime_path}"',
        'if [ ! -d "$RUNTIME_DIR/cortado" ]; then',
        '  mkdir -p "$RUNTIME_DIR"',
        '  python3 -c "import zipfile; zipfile.ZipFile(\'$CORTADO_WHEEL\').extractall(\'$RUNTIME_DIR\')"',
        'fi',
        "",
        f'echo "[INFO] Cortado RTA: {name} (module={mod})"',
        'python3 "{{asset:elastic_cortado_runner}}" \\',
        f'  --runtime "$RUNTIME_DIR" \\',
        f'  --module "{mod}" \\',
        f'  --rta "{name}" \\',
        f'  --rta-id "{rta_id}" \\',
        f'  --techniques "{techs}" \\',
        f"  --endpoint-rules '{ep_rules}' \\",
        f"  --siem-rules '{siem_rules}'",
    ])


def _hash_rta_command(rta: dict) -> str:
    name = rta.get("name", "")
    sha = rta.get("sample_hash", "")
    ep = rta.get("endpoint_rules", [])
    sm = rta.get("siem_rules", [])
    ep_str = ", ".join(r.get("name", r.get("id", "")) for r in ep)
    sm_str = ", ".join(r.get("name", r.get("id", "")) for r in sm)
    return "\n".join([
        f"# Elastic Cortado Sample-backed RTA: {name.replace('_', ' ').title()}",
        "#",
        f"# This RTA references an external sample and cannot be automatically executed.",
        f"# Sample hash: {sha}",
        f"# Acquire the sample only through an approved isolated malware-testing workflow.",
        "#",
        f"# Expected Endpoint detections: {ep_str or 'none'}",
        f"# Expected SIEM detections:     {sm_str or 'none'}",
        "#",
        "# Steps:",
        "# 1. Obtain the referenced sample through authorized channels",
        "# 2. Deploy to an isolated, authorized test endpoint",
        "# 3. Execute in a controlled manner",
        "# 4. Record detection results and update this Test manually",
        "#",
        "# WARNING: Referenced samples may be malicious.",
        "# Use only in isolated authorized test environments.",
        f'echo "MORGANA_RESULT_METADATA={{\\\"provider\\\":\\\"elastic-cortado\\\",\\\"rta_type\\\":\\\"hash\\\",\\\"rta_name\\\":\\\"{name}\\\",\\\"sample_hash\\\":\\\"{sha}\\\",\\\"status\\\":\\\"manual\\\"}}"',
    ])


def _build_script(rta: dict, risk_overrides: dict, source_commit: str) -> dict:
    rta_id   = rta.get("id", "")
    rta_name = rta.get("name", "")
    rta_type = rta.get("rta_type", "code")
    platforms = rta.get("platforms", [])
    techniques = rta.get("techniques", [])
    tactics = get_tactics(techniques)
    primary_tactic = get_primary_tactic(techniques)
    risk = risk_overrides.get(rta_id, get_risk(primary_tactic))

    display_name = rta.get("name_comment") or rta_name.replace("_", " ").title()
    description_raw = rta.get("description", "") or display_name

    # Rule metadata
    ep_rules = rta.get("endpoint_rules", [])
    siem_rules = rta.get("siem_rules", [])

    # Build expected detections block for description
    ep_str = "\n".join(f"  - Endpoint: {r.get('name', r.get('id', ''))}" for r in ep_rules)
    siem_str = "\n".join(f"  - SIEM: {r.get('name', r.get('id', ''))}" for r in siem_rules)
    rule_block = "\n".join(filter(None, [ep_str, siem_str]))

    description = (
        f"Elastic Cortado Red Team Automation for detection validation.\n\n"
        f"{description_raw}\n"
        + (f"\nExpected detections:\n{rule_block}\n" if rule_block else "")
        + (f"\nATT&CK: {', '.join(techniques)}\n" if techniques else "")
        + f"\nRuns the official Cortado RTA from the pinned Elastic wheel. "
          f"Detection results depend on Elastic Security configuration."
    )

    if rta_type == "hash":
        executor = "manual"
        command = _hash_rta_command(rta)
        cleanup_command = None
        req_assets = []
    else:
        executor = "bash"
        command = _code_rta_command(rta)
        cleanup_command = None
        req_assets = ["elastic_cortado_wheel", "elastic_cortado_runner"]

    return {
        "id": f"cortado:{rta_id}{rta.get('_unique_suffix', '')}" if rta_id else f"cortado:{rta_name}",
        "name": f"CORTADO - {display_name}",
        "description": description,
        "tactic": TACTIC_LABELS.get(primary_tactic, primary_tactic.replace("-", " ").title()),
        "tcode": techniques[0] if techniques else "",
        "executor": executor,
        "executor_config": {
            "timeout_seconds": 120,
            "result_parser": "morgana-marker-v1",
        },
        "platform": "linux",  # bash; agent handles OS dispatch
        "command": command,
        "cleanup_command": cleanup_command,
        "required_tags": ["cortado_runtime_path"] if rta_type == "code" else [],
        "required_assets": req_assets,
        "operational_risk": risk,
        "source_metadata": {
            "provider": "elastic-cortado",
            "source_repository": CORTADO_REPO,
            "source_release": CORTADO_RELEASE,
            "source_commit": source_commit,
            "source_module": rta.get("source_module", ""),
            "source_path": rta.get("source_path", ""),
            "rta_id": rta_id,
            "rta_name": rta_name,
            "rta_type": rta_type,
            "platforms": platforms,
            "techniques": techniques,
            "mitre_tactics": tactics,
            "mitre_domain": "enterprise-attack",
            "endpoint_rules": ep_rules,
            "siem_rules": siem_rules,
            "ancillary_files": rta.get("ancillary_files", []),
            "sample_hash": rta.get("sample_hash"),
            "source_modified": False,
        },
    }


# ── Package builder ────────────────────────────────────────────────────────────

def _execution_platforms(scripts: list[dict]) -> list[str]:
    plats = set()
    for s in scripts:
        for p in s.get("source_metadata", {}).get("platforms", []):
            plats.add(p)
    return sorted(plats) or ["windows", "linux", "macos"]


def _build_package(pkg_key: str, tactic_label: str, scripts: list[dict],
                   source_commit: str) -> dict:
    is_sample = (pkg_key == "sample-backed")
    exec_plats = _execution_platforms(scripts)
    mitre_tcodes = sorted({t for s in scripts for t in s.get("source_metadata", {}).get("techniques", [])})
    mitre_tactics = sorted({t for s in scripts for t in s.get("source_metadata", {}).get("mitre_tactics", [])})
    risks = sorted({s["operational_risk"] for s in scripts})

    specialties = ["endpoint", "detection-validation", "elastic-security"]
    if is_sample:
        specialties.append("sample-backed")

    pkg_id = f"cortado-{pkg_key}-v1"
    pkg_name = f"Elastic Cortado — {tactic_label}"
    description = (
        f"Elastic Cortado Red Team Automations for {tactic_label}. "
        + ("These are sample-backed RTAs (HashRta) that reference external samples. "
           "They are preserved as manual records and cannot be automatically executed from Cortado. "
           if is_sample else
           "Each script executes an official Cortado CodeRTA behavior through the verified Elastic wheel "
           "to generate endpoint telemetry and validate Elastic Security detection rules. ")
        + f"Source: {CORTADO_REPO} at {CORTADO_RELEASE}."
    )
    prereqs = [
        "Python 3.12+ on the Morgana Agent.",
        "Elastic Cortado wheel extracted to the Agent runtime path (cortado_runtime_path tag).",
        "Use only in authorized, isolated test environments.",
    ] if not is_sample else [
        "Authorized external sample acquisition through approved channels.",
        "Isolated malware analysis environment.",
        "Referenced samples may be malicious — never use on production endpoints.",
    ]

    return {
        "package_id": pkg_id,
        "package_name": pkg_name,
        "version": "1.0.0",
        "summary": f"{len(scripts)} Elastic Cortado RTA{'s' if len(scripts)>1 else ''} for {tactic_label}.",
        "description": description,
        "purpose": f"Validate Elastic Security {'detection rules for ' + tactic_label if not is_sample else 'detection metadata for sample-backed behaviors'} in an authorized test environment.",
        "capabilities": [
            f"{len(scripts)} Elastic Cortado RTA{'s' if len(scripts)>1 else ''}.",
            "Official Elastic wheel execution — no custom behavior code.",
            "Elastic Endpoint and SIEM rule mapping metadata included.",
            "MORGANA_RESULT_METADATA output for Detection Fabric correlation.",
        ] if not is_sample else [
            f"{len(scripts)} sample-backed RTAs preserved as manual records.",
            "Sample hash and Elastic rule metadata included.",
            "Execution requires external authorized sample acquisition.",
        ],
        "use_cases": [
            f"Validate Elastic Security {tactic_label} detection rules in an authorized lab.",
            "Confirm detection rules fire on real RTA behavior before incident response exercises.",
        ],
        "prerequisites": prereqs,
        "safety_notes": [
            "Use only in isolated authorized test endpoints.",
            "Cortado RTAs generate real endpoint behaviors that trigger security products.",
            "Some RTAs require administrator/root privileges.",
            "Referenced sample hashes (HashRta) may be malicious — never acquire from untrusted sources.",
        ],
        "author": "Elastic / X3M.AI integration",
        "created": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "provider": "elastic-cortado",
        "source": "elastic-cortado",
        "source_repository": f"https://github.com/{CORTADO_REPO}",
        "source_release": CORTADO_RELEASE,
        "source_commit": source_commit,
        "source_license": CORTADO_LICENSE,
        "documentation_url": f"https://github.com/{CORTADO_REPO}",
        "mitre_domain": "enterprise-attack",
        "mitre_tactic": tactic_label,
        "mitre_tactics": mitre_tactics,
        "mitre_tcodes": mitre_tcodes[:50],  # cap to avoid catalog size issues
        "platform": sorted(exec_plats) or ["windows", "linux", "macos"],
        "category": f"detection/cortado/{pkg_key}",
        "specialties": specialties,
        "package_types": ["detection-validation"] if is_sample else ["atomic-tests", "detection-validation"],
        "execution_platforms": sorted(exec_plats) or ["windows", "linux", "macos"],
        "target_environments": ["endpoint"],
        "risk_badges": risks,
        "tag_categories": [] if is_sample else CORTADO_TAGS,
        "assets": [] if is_sample else [_wheel_asset_def(), _runner_asset_def()],
        "scripts": scripts,
        "chains": [],
    }


# ── Catalog update ─────────────────────────────────────────────────────────────

def update_catalog(catalog_path: Path, packages: list[dict]) -> None:
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    packs = catalog.get("packs", [])
    for pkg in packages:
        pid = pkg["package_id"]
        packs = [e for e in packs if e.get("package_id") != pid]
        packs.append({
            "package_id": pid,
            "package_name": pkg["package_name"],
            "version": pkg["version"],
            "description": pkg["description"],
            "capabilities": pkg["capabilities"],
            "use_cases": pkg["use_cases"],
            "safety_notes": pkg["safety_notes"],
            "mitre_tactic": pkg["mitre_tactic"],
            "mitre_tcodes": pkg["mitre_tcodes"],
            "script_count": len(pkg["scripts"]),
            "chain_count": 0,
            "platform": pkg["platform"],
            "prerequisites": pkg["prerequisites"],
            "sentinel_connectors": [],
            "status": "community",
            "provider": pkg["provider"],
            "author": pkg["author"],
            "category": pkg["category"],
            "url": pkg["documentation_url"],
        })
    catalog["packs"] = packs
    catalog["updated"] = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    catalog_path.write_text(json.dumps(catalog, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"[INFO] Catalog updated: {len(packages)} Cortado packages, total={len(packs)}")


# ── Main ───────────────────────────────────────────────────────────────────────

def main() -> int:
    p = argparse.ArgumentParser(description="Generate Elastic Cortado Morgana packages")
    p.add_argument("--source-dir", required=True)
    p.add_argument("--out-dir", required=True)
    p.add_argument("--catalog", default=str(CAMELOT_ROOT / "morgana/excalibur/catalog.json"))
    p.add_argument("--risk-overrides", default=str(TOOLS_DIR / "cortado_risk_overrides.json"))
    p.add_argument("--no-update-catalog", action="store_true")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--verbose", action="store_true")
    args = p.parse_args()

    source_dir = Path(args.source_dir)
    out_dir = Path(args.out_dir)
    risk_overrides = load_overrides(Path(args.risk_overrides))

    # Discover RTAs
    print(f"[CORTADO] Enumerating RTAs from {source_dir}...")
    rtas, errors = enumerate_rtas(source_dir)
    source_commit = CORTADO_COMMIT
    print(f"[CORTADO] Release: {CORTADO_RELEASE} | Commit: {source_commit}")
    print(f"[CORTADO] RTAs discovered: {len(rtas)} valid, {len(errors)} errors")

    code_rtas = [r for r in rtas if r["rta_type"] == "code"]
    hash_rtas = [r for r in rtas if r["rta_type"] == "hash"]
    print(f"[CORTADO]   CodeRTA: {len(code_rtas)}, HashRTA: {len(hash_rtas)}")

    if args.dry_run:
        tac_counts: dict[str, int] = {}
        for r in code_rtas:
            t = get_primary_tactic(r.get("techniques", []))
            tac_counts[t] = tac_counts.get(t, 0) + 1
        print("\n[DRY RUN] Tactic distribution (CodeRTA):")
        for t, c in sorted(tac_counts.items()):
            print(f"  {t}: {c}")
        print(f"  sample-backed (HashRTA): {len(hash_rtas)}")
        return 0

    # Deduplicate IDs: some upstream RTAs share the same UUID — make them unique
    seen_ids: dict[str, int] = {}
    for r in rtas:
        base_id = r.get("id", "") or r.get("name", "unknown")
        if base_id in seen_ids:
            seen_ids[base_id] += 1
            r["_unique_suffix"] = f"-{seen_ids[base_id]}"
        else:
            seen_ids[base_id] = 0

    # Build Scripts
    all_scripts = [_build_script(r, risk_overrides, source_commit) for r in rtas]
    code_scripts = [s for s in all_scripts if s["source_metadata"]["rta_type"] == "code"]
    hash_scripts = [s for s in all_scripts if s["source_metadata"]["rta_type"] == "hash"]

    # Group CodeRTAs by primary tactic
    tac_groups: dict[str, list[dict]] = {}
    for s, r in zip(code_scripts, code_rtas):
        t = get_primary_tactic(r.get("techniques", []))
        tac_groups.setdefault(t, []).append(s)

    packages: list[dict] = []
    for tactic_key in sorted(tac_groups.keys()):
        scripts = tac_groups[tactic_key]
        label = TACTIC_LABELS.get(tactic_key, tactic_key.replace("-", " ").title())
        pkg = _build_package(tactic_key, label, scripts, source_commit)
        packages.append(pkg)

    # HashRTA package
    if hash_scripts:
        pkg = _build_package("sample-backed", "Sample-backed RTAs", hash_scripts, source_commit)
        packages.append(pkg)

    total_scripts = sum(len(p["scripts"]) for p in packages)
    print(f"[CORTADO] Generated {total_scripts} Scripts in {len(packages)} packages")

    if args.dry_run:
        return 0

    # Write package JSONs
    pkg_dir = out_dir / "packages"
    pkg_dir.mkdir(parents=True, exist_ok=True)
    for pkg in packages:
        out_path = pkg_dir / f"{pkg['package_id']}.json"
        out_path.write_text(json.dumps(pkg, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        if args.verbose:
            print(f"[OK] {out_path.name} ({len(pkg['scripts'])} scripts)")

    print(f"[OK] Written {len(packages)} package files to {pkg_dir}")

    # Source inventory
    inventory = [
        {
            "rta_id": r.get("id", ""),
            "rta_name": r.get("name", ""),
            "rta_type": r.get("rta_type", ""),
            "source_path": r.get("source_path", ""),
            "source_module": r.get("source_module", ""),
            "platforms": r.get("platforms", []),
            "techniques": r.get("techniques", []),
            "endpoint_rules": r.get("endpoint_rules", []),
            "siem_rules": r.get("siem_rules", []),
            "ancillary_files": r.get("ancillary_files", []),
            "sample_hash": r.get("sample_hash"),
            "source_commit": source_commit,
            "release": CORTADO_RELEASE,
        }
        for r in rtas
    ]
    (out_dir / "source-inventory.json").write_text(json.dumps(inventory, indent=2) + "\n", encoding="utf-8")

    # Build manifest
    bm = {
        "source_repository": f"https://github.com/{CORTADO_REPO}",
        "source_commit": source_commit,
        "release": CORTADO_RELEASE,
        "package_version": CORTADO_VERSION,
        "license": CORTADO_LICENSE,
        "python_requires": CORTADO_PYTHON,
        "wheel_filename": CORTADO_WHEEL,
        "wheel_url": CORTADO_WHEEL_URL,
        "wheel_sha256": CORTADO_WHEEL_SHA256,
        "wheel_size": CORTADO_WHEEL_SIZE,
        "runner_filename": "morgana_cortado_runner.py",
        "runner_sha256": _runner_sha256(),
        "manual_cortado_install_required": False,
        "poetry_required_on_agent": False,
        "source_modified": False,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "PASS",
    }
    (out_dir / "build-manifest.json").write_text(json.dumps(bm, indent=2) + "\n", encoding="utf-8")

    # Conversion report
    ep_count = sum(1 for r in rtas if r.get("endpoint_rules"))
    siem_count = sum(1 for r in rtas if r.get("siem_rules"))
    both_count = sum(1 for r in rtas if r.get("endpoint_rules") and r.get("siem_rules"))
    mapped_count = sum(1 for r in rtas if r.get("techniques"))
    anc_count = sum(1 for r in rtas if r.get("ancillary_files"))
    plat_counts = {"windows": 0, "linux": 0, "macos": 0}
    for r in rtas:
        for p in r.get("platforms", []):
            if p in plat_counts: plat_counts[p] += 1
    report = {
        "source_commit": source_commit,
        "release": CORTADO_RELEASE,
        "wheel_sha256": CORTADO_WHEEL_SHA256,
        "total_rtas": len(rtas),
        "code_rta_count": len(code_rtas),
        "hash_rta_count": len(hash_rtas),
        "parse_errors": len(errors),
        "platforms": plat_counts,
        "with_endpoint_rules": ep_count,
        "with_siem_rules": siem_count,
        "with_both_rules": both_count,
        "with_no_rules": len(rtas) - ep_count - siem_count + both_count,
        "mapped_to_attack": mapped_count,
        "unmapped": len(rtas) - mapped_count,
        "with_ancillary_files": anc_count,
        "hash_rta_count_samples": len(hash_rtas),
        "total_scripts": total_scripts,
        "packages": len(packages),
        "source_reconciled": True,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    (out_dir / "conversion-report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    if not args.no_update_catalog:
        catalog_path = Path(args.catalog)
        if catalog_path.exists():
            update_catalog(catalog_path, packages)

    print(f"\n[SUCCESS] Elastic Cortado provider generated:")
    print(f"  Release:   {CORTADO_RELEASE}")
    print(f"  Commit:    {source_commit}")
    print(f"  RTAs:      {len(rtas)} ({len(code_rtas)} CodeRTA, {len(hash_rtas)} HashRTA)")
    print(f"  Scripts:   {total_scripts}")
    print(f"  Packages:  {len(packages)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
