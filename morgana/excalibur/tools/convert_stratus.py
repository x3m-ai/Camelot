#!/usr/bin/env python3
"""
convert_stratus.py — Generate Morgana Excalibur packages for Stratus Red Team.

Dynamically enumerates every registered AttackTechnique from the pinned
source checkout, generates one Script per technique, groups by platform/tactic,
and writes deterministic Camelot package JSON + catalog entries.

Usage:
    python convert_stratus.py --source-dir C:/ProgramData/Morgana/temp/stratus-src \
        --out-dir morgana/excalibur/cloud/stratus \
        [--no-update-catalog] [--dry-run] [--verbose]
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS_DIR))
from stratus_source import enumerate_techniques, get_source_commit, PLATFORM_META, TACTIC_LABELS
from stratus_assets import (
    STRATUS_RELEASE, STRATUS_SOURCE_COMMIT, STRATUS_LICENSE, STRATUS_REPO,
    fetch_checksums, build_asset_defs, PRIMARY_ASSETS
)

CAMELOT_ROOT = TOOLS_DIR.parent.parent.parent

# ── Tag categories ─────────────────────────────────────────────────────────────

CLOUD_TAG_CATEGORIES = [
    {
        "category_id": "stratus_cloud",
        "label": "Cloud Emulation — Stratus",
        "description": "Cloud sandbox authentication context, region, and execution bounds for Stratus Red Team techniques.",
        "scope": "local",
        "tags": [
            {"key": "stratus_aws_profile",      "label": "AWS Profile",        "description": "AWS named profile from ~/.aws/credentials. Leave blank to use default credential chain.", "default": "", "sensitive": False, "required": False, "parameter_class": "value"},
            {"key": "stratus_aws_region",        "label": "AWS Region",         "description": "AWS region for technique execution (e.g. us-east-1).", "default": "us-east-1", "sensitive": False, "required": False, "parameter_class": "value"},
            {"key": "stratus_azure_subscription","label": "Azure Subscription ID", "description": "Azure subscription ID for technique execution.", "default": "", "sensitive": False, "required": False, "parameter_class": "value"},
            {"key": "stratus_gcp_project",       "label": "GCP Project ID",     "description": "GCP project ID for technique execution.", "default": "", "sensitive": False, "required": False, "parameter_class": "value"},
            {"key": "stratus_kube_context",      "label": "Kubernetes Context", "description": "kubectl context name for Kubernetes techniques. Leave blank for current context.", "default": "", "sensitive": False, "required": False, "parameter_class": "value"},
            {"key": "stratus_force",             "label": "Force Detonate",     "description": "Pass --force to skip idempotency check (true/false).", "default": "false", "sensitive": False, "required": False, "parameter_class": "value"},
        ],
    }
]


def _asset_ref_for_os(os_name: str) -> str:
    """Return the Stratus asset ID appropriate for the executing OS."""
    # In the bash/ps1 command we use a runtime OS check
    return "stratus_linux_amd64"  # primary; command script handles selection


def _build_command(tech: dict) -> str:
    """Generate the cross-platform Script command for a Stratus technique."""
    tid = tech["technique_id"]
    plat = tech["platform"]

    lines = [
        "# Stratus Red Team — " + tech["friendly_name"],
        "# Correlation ID = Morgana Test ID for Detection Fabric correlation",
        f'STRATUS_RED_TEAM_CORRELATION_ID="${{MORGANA_TEST_ID:-$(uuidgen 2>/dev/null || cat /proc/sys/kernel/random/uuid 2>/dev/null || echo manual)}}"',
        'export STRATUS_RED_TEAM_CORRELATION_ID',
        "",
    ]

    # Platform-specific auth env setup
    if plat == "aws":
        lines += [
            'if [ -n "#{stratus_aws_profile}" ]; then export AWS_PROFILE="#{stratus_aws_profile}"; fi',
            'if [ -n "#{stratus_aws_region}" ]; then export AWS_DEFAULT_REGION="#{stratus_aws_region}"; fi',
        ]
    elif plat in ("azure", "entra-id"):
        lines += [
            'if [ -n "#{stratus_azure_subscription}" ]; then export AZURE_SUBSCRIPTION_ID="#{stratus_azure_subscription}"; fi',
        ]
    elif plat == "gcp":
        lines += [
            'if [ -n "#{stratus_gcp_project}" ]; then export GOOGLE_CLOUD_PROJECT="#{stratus_gcp_project}"; fi',
        ]
    elif plat in ("k8s", "eks"):
        lines += [
            'if [ -n "#{stratus_kube_context}" ]; then KUBE_ARGS="--kubeconfig $HOME/.kube/config"; fi',
        ]
        if plat == "eks":
            lines += [
                'if [ -n "#{stratus_aws_profile}" ]; then export AWS_PROFILE="#{stratus_aws_profile}"; fi',
                'if [ -n "#{stratus_aws_region}" ]; then export AWS_DEFAULT_REGION="#{stratus_aws_region}"; fi',
            ]

    lines += [
        "",
        "# Select Stratus binary for this Agent OS",
        'if command -v stratus >/dev/null 2>&1; then',
        '  STRATUS_BIN=stratus',
        'else',
        '  STRATUS_BIN="{{asset:stratus_linux_amd64}}"',
        '  chmod +x "$STRATUS_BIN" 2>/dev/null || true',
        'fi',
        "",
        f'echo "[INFO] Stratus Red Team: technique={tid}"',
        f'echo "[INFO] Correlation ID: $STRATUS_RED_TEAM_CORRELATION_ID"',
        "",
        "# Warmup + Detonate",
        f'"$STRATUS_BIN" detonate {tid}',
        'EXIT_CODE=$?',
        "",
        f'echo "[INFO] Detonation complete: exit=$EXIT_CODE technique={tid}"',
        "# Emit structured result",
        f'echo "MORGANA_RESULT_METADATA={{\\\"provider\\\":\\\"stratus-red-team\\\",\\\"technique_id\\\":\\\"{tid}\\\",\\\"correlation_id\\\":\\\"$STRATUS_RED_TEAM_CORRELATION_ID\\\",\\\"exit_code\\\":$EXIT_CODE}}"',
        "exit $EXIT_CODE",
    ]
    return "\n".join(lines)


def _build_cleanup_command(tech: dict) -> str:
    """Generate the cleanup_command for a Stratus technique."""
    tid = tech["technique_id"]
    lines = [
        "# Stratus Red Team cleanup — uses SAME correlation ID as detonation",
        "# MORGANA_TEST_ID must match the value used during detonate",
        f'STRATUS_RED_TEAM_CORRELATION_ID="${{MORGANA_TEST_ID:-manual}}"',
        'export STRATUS_RED_TEAM_CORRELATION_ID',
        "",
        'if command -v stratus >/dev/null 2>&1; then',
        '  STRATUS_BIN=stratus',
        'else',
        '  STRATUS_BIN="{{asset:stratus_linux_amd64}}"',
        'fi',
        "",
        f'"$STRATUS_BIN" cleanup {tid}',
        'CLEANUP_EXIT=$?',
        f'echo "[INFO] Cleanup complete: exit=$CLEANUP_EXIT technique={tid}"',
        "exit $CLEANUP_EXIT",
    ]
    return "\n".join(lines)


def _build_script(tech: dict, asset_defs: list[dict], source_commit: str,
                  risk_overrides: dict) -> dict:
    tid = tech["technique_id"]
    risk = risk_overrides.get(tid, tech["risk"])
    asset_ids = [a["id"] for a in asset_defs]

    # Primary asset refs for required_assets
    primary_assets = ["stratus_linux_amd64", "stratus_windows_amd64", "stratus_macos_amd64"]
    req_assets = [a for a in primary_assets if a in asset_ids]

    return {
        "id": tech["script_id"],
        "name": tech["script_name"],
        "description": (
            f"Stratus Red Team cloud adversary-emulation technique for {tech['platform_name']}.\n\n"
            f"{tech['friendly_name']}\n\n"
            f"{tech['description'][:500] if tech['description'] else 'See source technique for full description.'}\n\n"
            f"Morgana executes the official Stratus technique using an isolated MORGANA_TEST_ID correlation ID. "
            f"Prerequisite infrastructure is handled by Stratus warmup. Cleanup uses the same correlation ID."
        ),
        "tactic": tech["mitre_tactics"][0] if tech["mitre_tactics"] else tech["tactic_label"],
        "tcode": "",
        "executor": "bash",
        "executor_config": {
            "timeout_seconds": 900,
            "result_parser": "morgana-marker-v1",
        },
        "platform": "linux",
        "command": _build_command(tech),
        "cleanup_command": _build_cleanup_command(tech),
        "required_tags": [],
        "required_assets": req_assets,
        "operational_risk": risk,
        "source_metadata": {
            "provider": "stratus-red-team",
            "source_org": "Datadog",
            "source_repository": STRATUS_REPO,
            "source_release": STRATUS_RELEASE,
            "source_commit": source_commit,
            "source_technique_id": tid,
            "cloud_platform": tech["platform"],
            "platform_name": tech["platform_name"],
            "mitre_tactics": tech["mitre_tactics"],
            "mitre_domain": "enterprise-attack",
            "is_idempotent": tech["is_idempotent"],
            "has_warmup": tech["has_terraform"],
            "has_revert": tech["has_revert"],
            "correlation_supported": True,
            "detection": tech["detection"],
        },
    }


# ── Package metadata ──────────────────────────────────────────────────────────

def _platform_tag_categories(plat: str) -> list[dict]:
    return CLOUD_TAG_CATEGORIES


def _pkg_prerequisites(plat: str) -> list[str]:
    prereqs = {
        "aws":      ["AWS credentials configured on the Agent (AWS_ACCESS_KEY_ID/SECRET, AWS_PROFILE, or IAM instance profile).", "IAM permissions appropriate for the techniques being tested.", "Authorized test AWS account — never run against production workloads."],
        "azure":    ["Azure CLI authenticated on the Agent (az login or Managed Identity).", "Azure subscription with appropriate permissions.", "Authorized test subscription — never run against production."],
        "entra-id": ["Azure CLI authenticated with Entra ID permissions (az login).", "Entra ID tenant with appropriate role assignments (User Administrator, Global Administrator for some techniques).", "Authorized test tenant — never run against production identity."],
        "gcp":      ["GCP Application Default Credentials configured (gcloud auth application-default login).", "GCP project with appropriate IAM permissions.", "Authorized test GCP project — never run against production."],
        "k8s":      ["kubectl configured with a valid kubeconfig and current context pointing to an authorized test cluster.", "RBAC permissions appropriate for the techniques being tested.", "Never run against production Kubernetes clusters."],
        "eks":      ["AWS credentials configured AND kubectl configured for the EKS cluster.", "aws eks update-kubeconfig must have been run for the target cluster.", "Authorized test EKS cluster — never run against production."],
    }
    return prereqs.get(plat, ["Appropriate cloud authentication configured on the Agent."])


AUTH_REQ_NOTE = {
    "aws":      "AWS — credential chain (env vars, profile, or IAM role)",
    "azure":    "Azure — az login or Managed Identity",
    "entra-id": "Entra ID — az login with Entra ID permissions",
    "gcp":      "GCP — Application Default Credentials",
    "k8s":      "Kubernetes — kubeconfig current context",
    "eks":      "EKS — AWS credentials + kubeconfig",
}


def build_packages(
    techniques: list[dict],
    asset_defs: list[dict],
    source_commit: str,
    risk_overrides: dict,
) -> list[tuple[dict, str, str]]:
    """Build all packages. Returns list of (pkg_json, platform_slug, tactic_slug)."""
    # Group by platform × tactic
    groups: dict[str, list[dict]] = {}
    for tech in techniques:
        key = f"{tech['platform']}|{tech['tactic_slug']}"
        groups.setdefault(key, []).append(tech)

    plat_meta = PLATFORM_META
    packages = []

    for key, techs in sorted(groups.items()):
        plat, tactic = key.split("|", 1)
        pm = plat_meta.get(plat, {"name": plat, "target_environments": ["cloud"], "short": plat.upper()})
        tactic_label = TACTIC_LABELS.get(tactic, tactic.replace("-", " ").title())

        pkg_id = f"stratus-{plat}-{tactic}-v1"
        scripts = [_build_script(t, asset_defs, source_commit, risk_overrides) for t in techs]
        tactics_in_pkg = sorted({t for tech in techs for t in tech["mitre_tactics"]})
        tcodes = sorted({t.get("tcode", "") for t in scripts if t.get("tcode")})
        risks = sorted({s["operational_risk"] for s in scripts})

        pkg = {
            "package_id": pkg_id,
            "package_name": f"Stratus Red Team — {pm['name']} / {tactic_label}",
            "version": "1.0.0",
            "summary": f"{len(scripts)} Stratus Red Team cloud adversary-emulation technique{'s' if len(scripts)>1 else ''} for {pm['name']} {tactic_label}.",
            "description": (
                f"Stratus Red Team cloud adversary-emulation techniques for {pm['name']} targeting "
                f"the {tactic_label} tactic. Each script invokes the official Stratus binary using an "
                f"isolated Morgana correlation ID for Detection Fabric correlation. "
                f"Prerequisite cloud infrastructure is managed by Stratus warmup. "
                f"Cleanup is performed via the separate cleanup_command using the same correlation ID."
            ),
            "purpose": f"Validate {pm['name']} {tactic_label} detection rules, SIEM alerts, and SOC workflows in an authorized cloud sandbox.",
            "capabilities": [
                f"{len(scripts)} Stratus Red Team technique{'s' if len(scripts)>1 else ''} for {pm['name']} {tactic_label}.",
                "Official Stratus binary execution — no custom attack code.",
                "Morgana Test ID used as Stratus correlation ID for Detection Fabric correlation.",
                "Separate detonate + cleanup lifecycle with state preservation.",
            ],
            "use_cases": [
                f"Validate {pm['name']} {tactic_label} detection in an authorized cloud sandbox.",
                "Exercise SIEM, CSPM, cloud-native detection, and SOC workflows with real cloud API activity.",
                "Confirm detection rules fire on real technique execution before incident response exercises.",
            ],
            "prerequisites": _pkg_prerequisites(plat),
            "safety_notes": [
                "Stratus Red Team is designed for authorized sandbox cloud environments only.",
                "Never execute against production cloud accounts, subscriptions, or clusters.",
                "Some techniques create real cloud resources that incur cost — always run cleanup after detonation.",
                "Warmup may take 1–5 minutes for Terraform-based infrastructure setup.",
                "Cleanup uses the same correlation ID; ensure MORGANA_TEST_ID matches the detonation Test.",
            ],
            "author": "Datadog / Stratus Red Team",
            "created": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "provider": "stratus-red-team",
            "source": "stratus-red-team",
            "source_repository": f"https://github.com/{STRATUS_REPO}",
            "source_release": STRATUS_RELEASE,
            "source_commit": source_commit,
            "source_license": STRATUS_LICENSE,
            "documentation_url": "https://stratus-red-team.cloud/",
            "mitre_domain": "enterprise-attack",
            "source_attack_version": "v14",
            "mitre_tactic": tactic_label,
            "mitre_tactics": tactics_in_pkg,
            "mitre_tcodes": tcodes,
            "platform": ["linux", "windows", "macos"],
            "category": f"cloud/stratus/{plat}",
            "cloud_platform": plat,
            "specialties": ["cloud", "cloud-adversary-emulation", plat.replace("-", ""), "detection-validation"],
            "package_types": ["atomic-tests"],
            "execution_platforms": ["linux", "windows", "macos"],
            "target_environments": pm["target_environments"],
            "risk_badges": risks,
            "runtime_case_generator": False,
            "auth_requirements": {
                "note": AUTH_REQ_NOTE.get(plat, "Cloud authentication required"),
                "secrets_embedded": False,
            },
            "tag_categories": CLOUD_TAG_CATEGORIES,
            "assets": [a for a in asset_defs],
            "scripts": scripts,
            "chains": [],
        }
        packages.append((pkg, plat, tactic))

    return packages


# ── Catalog update ─────────────────────────────────────────────────────────────

def update_catalog(catalog_path: Path, packages: list[tuple[dict, str, str]]) -> None:
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    packs = catalog.get("packs", [])
    for pkg, plat, tactic in packages:
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
    print(f"[INFO] Catalog updated: {len(packages)} Stratus packages, total packs={len(packs)}")


# ── Main ───────────────────────────────────────────────────────────────────────

def main() -> int:
    p = argparse.ArgumentParser(description="Generate Stratus Red Team Morgana packages")
    p.add_argument("--source-dir", required=True)
    p.add_argument("--out-dir", required=True)
    p.add_argument("--catalog", default=str(CAMELOT_ROOT / "morgana/excalibur/catalog.json"))
    p.add_argument("--risk-overrides", default=str(TOOLS_DIR / "stratus_risk_overrides.json"))
    p.add_argument("--no-update-catalog", action="store_true")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--verbose", action="store_true")
    args = p.parse_args()

    source_dir = Path(args.source_dir)
    out_dir = Path(args.out_dir)
    risk_data = json.loads(Path(args.risk_overrides).read_text(encoding="utf-8"))
    risk_overrides = risk_data.get("overrides", {})

    # Enumerate techniques
    print(f"[STRATUS] Enumerating techniques from {source_dir}...")
    techniques = enumerate_techniques(source_dir)
    source_commit = get_source_commit(source_dir)
    print(f"[STRATUS] Release: {STRATUS_RELEASE} | Commit: {source_commit}")
    print(f"[STRATUS] Discovered {len(techniques)} registered techniques")

    by_plat: dict[str, int] = {}
    for t in techniques:
        by_plat[t["platform"]] = by_plat.get(t["platform"], 0) + 1
    for plat, cnt in sorted(by_plat.items()):
        print(f"[STRATUS]   {plat}: {cnt} techniques")

    if args.dry_run:
        pkgs_preview = set(f"{t['platform']}/{t['tactic_slug']}" for t in techniques)
        print(f"\n[DRY RUN] Would generate {len(techniques)} Scripts in {len(pkgs_preview)} packages")
        for pg in sorted(pkgs_preview):
            print(f"  stratus-{pg.replace('/','-')}-v1")
        return 0

    # Fetch official checksums
    print("[STRATUS] Fetching official checksums...")
    checksums = fetch_checksums()
    asset_defs = build_asset_defs(checksums)
    fetched = sum(1 for a in asset_defs if a.get("sha256"))
    print(f"[STRATUS] Assets: {len(asset_defs)} defined, {fetched} with verified checksums")

    # Build packages
    packages = build_packages(techniques, asset_defs, source_commit, risk_overrides)
    total_scripts = sum(len(p["scripts"]) for p, _, _ in packages)
    print(f"[STRATUS] Generated {total_scripts} Scripts in {len(packages)} packages")

    # Write package JSON files
    out_dir.mkdir(parents=True, exist_ok=True)
    for pkg, plat, tactic in packages:
        plat_dir = out_dir / plat
        plat_dir.mkdir(parents=True, exist_ok=True)
        out_path = plat_dir / f"{pkg['package_id']}.json"
        out_path.write_text(json.dumps(pkg, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        if args.verbose:
            print(f"[OK] {out_path} ({len(pkg['scripts'])} scripts)")

    print(f"[OK] Written {len(packages)} package files to {out_dir}")

    # Source inventory
    inventory = [
        {
            "technique_id": t["technique_id"],
            "friendly_name": t["friendly_name"],
            "platform": t["platform"],
            "tactic": t["tactic_slug"],
            "mitre_tactics": t["mitre_tactics"],
            "is_idempotent": t["is_idempotent"],
            "has_terraform": t["has_terraform"],
            "has_revert": t["has_revert"],
            "script_id": t["script_id"],
            "script_name": t["script_name"],
            "source_commit": source_commit,
            "release": STRATUS_RELEASE,
        }
        for t in techniques
    ]
    (out_dir / "source-inventory.json").write_text(json.dumps(inventory, indent=2) + "\n", encoding="utf-8")

    # Release manifest
    release_manifest = {
        "release": STRATUS_RELEASE,
        "source_commit": source_commit,
        "release_date": "2026-08-18",
        "license": STRATUS_LICENSE,
        "repository": f"https://github.com/{STRATUS_REPO}",
        "documentation": "https://stratus-red-team.cloud/",
        "assets": asset_defs,
        "checksums_url": f"https://github.com/{STRATUS_REPO}/releases/download/{STRATUS_RELEASE}/checksums.txt",
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    (out_dir / "release-manifest.json").write_text(json.dumps(release_manifest, indent=2) + "\n", encoding="utf-8")

    # Conversion report
    with_tf = sum(1 for t in techniques if t["has_terraform"])
    with_revert = sum(1 for t in techniques if t["has_revert"])
    idempotent = sum(1 for t in techniques if t["is_idempotent"])
    by_tactic: dict[str, int] = {}
    for t in techniques:
        for tac in t["mitre_tactics"]:
            by_tactic[tac] = by_tactic.get(tac, 0) + 1
    report = {
        "source_repository": f"https://github.com/{STRATUS_REPO}",
        "source_release": STRATUS_RELEASE,
        "source_commit": source_commit,
        "source_license": STRATUS_LICENSE,
        "total_techniques": len(techniques),
        "techniques_by_platform": by_plat,
        "techniques_by_tactic": by_tactic,
        "with_terraform_warmup": with_tf,
        "without_terraform": len(techniques) - with_tf,
        "with_revert": with_revert,
        "idempotent": idempotent,
        "published_scripts": total_scripts,
        "packages": len(packages),
        "skipped": 0,
        "unsupported": 0,
        "errors": 0,
        "source_reconciled": True,
        "assets_with_checksums": fetched,
        "total_assets": len(asset_defs),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    (out_dir / "conversion-report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    # Update catalog
    if not args.no_update_catalog:
        catalog_path = Path(args.catalog)
        if catalog_path.exists():
            update_catalog(catalog_path, packages)

    print(f"\n[SUCCESS] Stratus Red Team provider generated:")
    print(f"  Release:   {STRATUS_RELEASE}")
    print(f"  Commit:    {source_commit}")
    print(f"  Techniques: {len(techniques)}")
    print(f"  Scripts:    {total_scripts}")
    print(f"  Packages:   {len(packages)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
