#!/usr/bin/env python3
"""
Excalibur STIX Pack Generator
==============================
Reads MITRE ATT&CK STIX v19.0 datasets (enterprise, mobile, ics) and
generates Excalibur pack JSON files for every technique/sub-technique
that is NOT already covered by an existing pack.

Deduplication key: (tcode, platform_slug)
  - Same TCode on different platforms = separate scripts (correct behaviour)
  - TCode+platform already in an existing pack = skipped (never overwritten)

Behaviour:
  - enterprise/windows existing packs  -> PATCHED (new scripts appended)
  - All other domain/platform combos   -> NEW files created per tactic
  - catalog.json                       -> Updated with new pack entries

Run from any directory:
  python generate_from_stix.py

Author: X3M.AI
Created: 2026-06-17
"""

import json
import os
import re
import glob
from datetime import date
from collections import defaultdict

TODAY = "2026-06-17"

STIX_DIR = r"C:\Users\ninoc\OfficeAddinApps\Merlino\stix_data"
EXCALIBUR_DIR = r"C:\Users\ninoc\OfficeAddinApps\Camelot\morgana\excalibur"
CATALOG_FILE = os.path.join(EXCALIBUR_DIR, "catalog.json")

# ---------------------------------------------------------------------------
# Platform slug mapping  (STIX name -> excalibur slug)
# ---------------------------------------------------------------------------
PLATFORM_SLUG = {
    "Windows":              "windows",
    "Linux":                "linux",
    "macOS":                "macos",
    "IaaS":                 "iaas",
    "Containers":           "containers",
    "Network Devices":      "network-devices",
    "Office Suite":         "office-suite",
    "SaaS":                 "saas",
    "Identity Provider":    "identity-provider",
    "ESXi":                 "esxi",
    "PRE":                  "pre",
    "Android":              "android",
    "iOS":                  "ios",
    # ICS-specific (will be normalised below)
    "Engineering Workstation":                      "ics-ew",
    "Field Controller/RTU/PLC/IED":                 "ics-plc",
    "Human-Machine Interface":                      "ics-hmi",
    "Control Server":                               "ics-cs",
    "Data Historian":                               "ics-historian",
    "Safety Instrumented System/Protection Relay":  "ics-sis",
    "Input/Output Server":                          "ics-io",
    "Remote Terminal Unit":                         "ics-rtu",
    "Actuators":                                    "ics-actuators",
    "Sensors":                                      "ics-sensors",
    "Routers":                                      "ics-routers",
}

# ---------------------------------------------------------------------------
# Folder layout:  (domain_key, platform_slug) -> subfolder relative to EXCALIBUR_DIR
# ---------------------------------------------------------------------------
PLATFORM_FOLDER_MAP = {
    # Enterprise
    ("enterprise", "windows"):           "enterprise/windows",
    ("enterprise", "linux"):             "enterprise/linux",
    ("enterprise", "macos"):             "enterprise/macos",
    ("enterprise", "pre"):               "enterprise/pre",
    ("enterprise", "iaas"):              "technology/cloud-iaas",
    ("enterprise", "saas"):              "technology/saas",
    ("enterprise", "containers"):        "technology/containers",
    ("enterprise", "network-devices"):   "technology/network-devices",
    ("enterprise", "office-suite"):      "technology/office-suite",
    ("enterprise", "identity-provider"): "technology/identity-provider",
    ("enterprise", "esxi"):              "technology/esxi",
    # Mobile
    ("mobile", "android"):               "mobile/android",
    ("mobile", "ios"):                   "mobile/ios",
    # ICS  – all OT-specific slugs go to ics/ot, Windows/Linux get own folders
    ("ics", "windows"):                  "ics/windows",
    ("ics", "linux"):                    "ics/linux",
    ("ics", "ics-general"):              "ics/ot",
    ("ics", "ics-ew"):                   "ics/ot",
    ("ics", "ics-plc"):                  "ics/ot",
    ("ics", "ics-hmi"):                  "ics/ot",
    ("ics", "ics-cs"):                   "ics/ot",
    ("ics", "ics-historian"):            "ics/ot",
    ("ics", "ics-sis"):                  "ics/ot",
    ("ics", "ics-io"):                   "ics/ot",
    ("ics", "ics-rtu"):                  "ics/ot",
    ("ics", "ics-actuators"):            "ics/ot",
    ("ics", "ics-sensors"):              "ics/ot",
    ("ics", "ics-routers"):              "ics/ot",
}

# Group ICS OT platforms into a single slug for pack generation purposes
ICS_OT_SLUGS = {
    "ics-ew", "ics-plc", "ics-hmi", "ics-cs", "ics-historian",
    "ics-sis", "ics-io", "ics-rtu", "ics-actuators", "ics-sensors",
    "ics-routers", "ics-general",
}

# ---------------------------------------------------------------------------
# Executor by platform
# ---------------------------------------------------------------------------
PLATFORM_EXECUTOR = {
    "windows":           "powershell",
    "linux":             "bash",
    "macos":             "bash",
    "iaas":              "powershell",
    "saas":              "powershell",
    "containers":        "bash",
    "network-devices":   "bash",
    "office-suite":      "powershell",
    "identity-provider": "powershell",
    "esxi":              "bash",
    "pre":               "powershell",
    "android":           "bash",
    "ios":               "bash",
    "ics-general":       "bash",
}
# All ICS OT slugs default to bash
for _slug in ICS_OT_SLUGS:
    PLATFORM_EXECUTOR.setdefault(_slug, "bash")

# ---------------------------------------------------------------------------
# Sentinel connector by platform
# ---------------------------------------------------------------------------
PLATFORM_SENTINEL = {
    "windows":           "Microsoft Defender for Endpoint",
    "linux":             "Syslog",
    "macos":             "Syslog",
    "iaas":              "Azure Activity",
    "saas":              "Microsoft 365 Defender",
    "containers":        "Container Insights",
    "network-devices":   "Network device logs",
    "office-suite":      "Microsoft 365 Defender",
    "identity-provider": "Microsoft Entra ID",
    "esxi":              "VMware ESXi logs",
    "pre":               "Threat Intelligence",
    "android":           "Mobile device logs",
    "ios":               "Mobile device logs",
    "ics-general":       "OT/ICS monitoring",
}
for _slug in ICS_OT_SLUGS:
    PLATFORM_SENTINEL.setdefault(_slug, "OT/ICS monitoring")

# ---------------------------------------------------------------------------
# Map tactic_id -> existing enterprise/windows pack filename
# (only packs that already exist on disk)
# ---------------------------------------------------------------------------
EXISTING_WINDOWS_PACKS = {
    "TA0043": "excalibur-reconnaissance-emulation-pack.json",
    "TA0002": "excalibur-execution-emulation-pack.json",
    "TA0003": "excalibur-persistence-emulation-pack.json",
    "TA0004": "excalibur-privesc-emulation-pack.json",
    "TA0005": "excalibur-defenseevasion-emulation-pack.json",
    "TA0006": "excalibur-credaccess-emulation-pack.json",
    "TA0007": "excalibur-discovery-emulation-pack.json",
    "TA0008": "excalibur-lateralmovement-emulation-pack.json",
    "TA0009": "excalibur-collection-emulation-pack.json",
    "TA0011": "excalibur-c2-emulation-pack.json",
    "TA0010": "excalibur-exfiltration-emulation-pack.json",
    "TA0040": "excalibur-impact-emulation-pack.json",
}


# ===========================================================================
# Helper functions
# ===========================================================================

def clean_description(text: str) -> str:
    """Return a clean, single-sentence description safe for JSON values."""
    if not text:
        return ""
    # Strip markdown links  [label](url)
    text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)
    # Strip citation references  (Citation: ...)
    text = re.sub(r'\(Citation:[^)]*\)', '', text)
    # Collapse whitespace / newlines
    text = re.sub(r'\s+', ' ', text).strip()
    # First sentence only
    parts = re.split(r'(?<=[.!?])\s+', text)
    result = parts[0] if parts else text
    if len(result) > 280:
        result = result[:277] + "..."
    return result


def safe_name(text: str) -> str:
    """Remove characters that would break command strings or script IDs."""
    return re.sub(r"['\"\\\n\r\t]", '', text)


def make_command(tcode: str, technique_name: str, tactic: str, executor: str, platform: str) -> str:
    n = safe_name(technique_name)
    t = safe_name(tactic)
    if executor == "powershell":
        return (
            f"Write-Host '[START] {tcode} - {n}'; "
            f"Write-Host '[INFO] Emulating {tcode} ({n}) tactic={t} platform={platform}'; "
            f"Write-Host '[SUCCESS] {tcode} emulation event logged'"
        )
    else:
        return (
            f"echo '[START] {tcode} - {n}'; "
            f"echo '[INFO] Emulating {tcode} ({n}) tactic={t} platform={platform}'; "
            f"echo '[SUCCESS] {tcode} emulation event logged'"
        )


def make_cleanup(tcode: str, executor: str) -> str:
    if executor == "powershell":
        return f"Write-Host '[INFO] {tcode} cleanup: no persistent artefacts'"
    else:
        return f"echo '[INFO] {tcode} cleanup: no persistent artefacts'"


def make_script(tcode, technique_name, tactic_name, executor, platform, description):
    n = safe_name(technique_name)
    t = safe_name(tactic_name)
    script_id = f"Excalibur - {t}-{tcode}-{n}"
    short_desc = clean_description(description) or f"Simulates {technique_name} ({tcode}) on {platform}."
    sentinel = PLATFORM_SENTINEL.get(platform, "Security monitoring")
    return {
        "id":               script_id,
        "name":             script_id,
        "description":      short_desc,
        "tactic":           tactic_name,
        "tcode":            tcode,
        "technique_name":   technique_name,
        "executor":         executor,
        "platform":         platform,
        "required_tags":    [],
        "command":          make_command(tcode, technique_name, tactic_name, executor, platform),
        "cleanup_command":  make_cleanup(tcode, executor),
        "detection_rule":   f"Detect {n} ({tcode})",
        "sentinel_connector": sentinel,
        "package":          "excalibur",
    }


def make_chain(script_id, tcode, technique_name, tactic_name):
    n = safe_name(technique_name)
    t = safe_name(tactic_name)
    return {
        "name":         f"Excalibur - {t}-{tcode}-{n}",
        "description":  f"Emulation chain for {tcode}: {technique_name}.",
        "package":      "excalibur",
        "tcode":        tcode,
        "tactic":       tactic_name,
        "script_refs":  [script_id],
    }


def make_new_pack(package_id, package_name, domain_key, tactic_id, tactic_name,
                  platform, stix_domain, scripts, chains):
    return {
        "package_id":       package_id,
        "package_name":     package_name,
        "version":          "1.0.0",
        "description": (
            f"Auto-generated from MITRE ATT&CK STIX v19.0 ({stix_domain}). "
            f"{len(scripts)} techniques for {tactic_name} ({tactic_id}) on {platform}."
        ),
        "author":           "X3M.AI",
        "created":          TODAY,
        "mitre_domain":     stix_domain,
        "mitre_tactic":     tactic_id,
        "mitre_tactic_name": tactic_name,
        "platform":         platform,
        "prerequisites":    ["Morgana agent installed on target machine"],
        "tag_categories":   [],
        "scripts":          scripts,
        "chains":           chains,
    }


def tactic_slug(tactic_name: str) -> str:
    return re.sub(r'[^a-z0-9]+', '-', tactic_name.lower()).strip('-')


# ===========================================================================
# STIX parsing
# ===========================================================================

def parse_stix(domain_key: str, kill_chain_name: str) -> list:
    """
    Returns list of dicts:
      tcode, name, description, platforms (list of STIX platform strings), tactics (list of (tactic_id, tactic_name))
    """
    fname_map = {
        "enterprise": "enterprise-attack-19.0.json",
        "mobile":     "mobile-attack-19.0.json",
        "ics":        "ics-attack-19.0.json",
    }
    stix_file = os.path.join(STIX_DIR, fname_map[domain_key])
    with open(stix_file, encoding="utf-8") as f:
        stix = json.load(f)

    # Build tactic phase_name -> (tactic_id, tactic_display_name)
    tactic_map = {}
    for obj in stix["objects"]:
        if obj.get("type") != "x-mitre-tactic":
            continue
        phase = obj.get("x_mitre_shortname", "")
        name  = obj.get("name", "")
        ext_id = next(
            (r.get("external_id", "") for r in obj.get("external_references", [])
             if r.get("source_name") == "mitre-attack"), ""
        )
        if phase:
            tactic_map[phase] = (ext_id, name)

    techniques = []
    for obj in stix["objects"]:
        if obj.get("type") != "attack-pattern":
            continue
        if obj.get("revoked") or obj.get("x_mitre_deprecated"):
            continue

        tcode = next(
            (r.get("external_id", "") for r in obj.get("external_references", [])
             if r.get("source_name") == "mitre-attack"), ""
        )
        if not tcode:
            continue

        # Clean platforms: filter None values
        raw_platforms = obj.get("x_mitre_platforms") or []
        platforms = [p for p in raw_platforms if p is not None]

        tactics = []
        for kcp in obj.get("kill_chain_phases", []):
            if kcp.get("kill_chain_name") == kill_chain_name:
                phase = kcp.get("phase_name", "")
                if phase in tactic_map:
                    tactics.append(tactic_map[phase])

        techniques.append({
            "tcode":       tcode,
            "name":        obj.get("name", ""),
            "description": obj.get("description", ""),
            "platforms":   platforms,
            "tactics":     tactics,
        })

    return techniques


# ===========================================================================
# Load existing coverage
# ===========================================================================

def load_existing_covered() -> set:
    """Return set of (tcode, platform_slug) already present in existing packs."""
    covered = set()
    for fpath in glob.glob(os.path.join(EXCALIBUR_DIR, "**", "*.json"), recursive=True):
        if os.path.basename(fpath) in ("catalog.json",):
            continue
        try:
            with open(fpath, encoding="utf-8") as f:
                data = json.load(f)
            for s in data.get("scripts", []):
                tc = s.get("tcode") or s.get("technique_id", "")
                pl = s.get("platform", "")
                if tc and pl:
                    covered.add((tc, pl))
        except Exception as exc:
            print(f"  [WARN] Cannot read {fpath}: {exc}")
    return covered


# ===========================================================================
# Main
# ===========================================================================

def main():
    print("=" * 60)
    print("  Excalibur STIX Pack Generator")
    print("=" * 60)
    print(f"  STIX source : {STIX_DIR}")
    print(f"  Output      : {EXCALIBUR_DIR}")
    print(f"  Date        : {TODAY}")
    print()

    # -----------------------------------------------------------------------
    # Load existing coverage
    # -----------------------------------------------------------------------
    print("[1/4] Loading existing coverage...")
    covered = load_existing_covered()
    print(f"      {len(covered)} (tcode, platform) pairs already covered - will be skipped")

    # -----------------------------------------------------------------------
    # Load existing enterprise/windows packs for patching
    # -----------------------------------------------------------------------
    print("[2/4] Loading existing Windows packs for patching...")
    windows_packs = {}  # tactic_id -> {filepath, data}
    for tactic_id, fname in EXISTING_WINDOWS_PACKS.items():
        fpath = os.path.join(EXCALIBUR_DIR, "enterprise", "windows", fname)
        if os.path.exists(fpath):
            with open(fpath, encoding="utf-8") as f:
                windows_packs[tactic_id] = {"filepath": fpath, "data": json.load(f)}
            print(f"      Loaded {fname}")

    # -----------------------------------------------------------------------
    # Load catalog
    # -----------------------------------------------------------------------
    with open(CATALOG_FILE, encoding="utf-8") as f:
        catalog = json.load(f)
    existing_catalog_ids = {p["package_id"] for p in catalog["packs"]}

    # -----------------------------------------------------------------------
    # Process each domain
    # -----------------------------------------------------------------------
    print("[3/4] Generating scripts from STIX...")
    print()

    DOMAIN_CONFIGS = [
        ("enterprise", "enterprise-attack",  "mitre-attack"),
        ("mobile",     "mobile-attack",      "mitre-mobile-attack"),
        ("ics",        "ics-attack",          "mitre-ics-attack"),
    ]

    total_new_scripts = 0
    total_new_packs   = 0
    catalog_additions = []

    for domain_key, stix_domain, kill_chain_name in DOMAIN_CONFIGS:
        print(f"  --- {stix_domain} ---")
        techniques = parse_stix(domain_key, kill_chain_name)
        print(f"  Active techniques: {len(techniques)}")

        # Group missing techniques by (platform_slug_effective, tactic_id, tactic_name)
        # For ICS OT slugs: all map to "ics-general" effective slug for pack grouping
        groups = defaultdict(list)

        for t in techniques:
            platforms = t["platforms"]
            tactics   = t["tactics"]

            if not tactics:
                continue

            # Determine platform slugs to generate
            if not platforms:
                if domain_key == "ics":
                    plat_slugs = ["ics-general"]
                else:
                    continue
            else:
                plat_slugs = []
                for p in platforms:
                    slug = PLATFORM_SLUG.get(p)
                    if slug is None:
                        continue
                    # ICS OT slugs normalise to ics-general for pack grouping
                    if domain_key == "ics" and slug in ICS_OT_SLUGS:
                        slug = "ics-general"
                    plat_slugs.append(slug)
                plat_slugs = list(dict.fromkeys(plat_slugs))  # deduplicate, preserve order
                if not plat_slugs:
                    continue

            for plat_slug in plat_slugs:
                folder_key = (domain_key, plat_slug)
                if folder_key not in PLATFORM_FOLDER_MAP:
                    continue

                for (tactic_id, tactic_name) in tactics:
                    # Skip already covered
                    if (t["tcode"], plat_slug) in covered:
                        continue
                    groups[(domain_key, plat_slug, tactic_id, tactic_name)].append(t)

        print(f"  New (platform, tactic) groups: {len(groups)}")

        # -----------------------------------------------------------------------
        # For each group: patch existing or create new
        # -----------------------------------------------------------------------
        for (dom, plat_slug, tactic_id, tactic_name), techs in sorted(groups.items()):
            folder_rel = PLATFORM_FOLDER_MAP[(dom, plat_slug)]
            folder_abs = os.path.join(EXCALIBUR_DIR, folder_rel.replace("/", os.sep))
            executor   = PLATFORM_EXECUTOR.get(plat_slug, "bash")

            is_patchable_windows = (
                dom == "enterprise"
                and plat_slug == "windows"
                and tactic_id in windows_packs
            )

            if is_patchable_windows:
                # ---- PATCH existing enterprise/windows pack ----
                pack_info = windows_packs[tactic_id]
                fpath = pack_info["filepath"]
                data  = pack_info["data"]
                existing_ids   = {s["id"] for s in data["scripts"]}
                existing_chains = {c.get("name", "") for c in data["chains"]}

                added_s = []
                added_c = []
                for t in techs:
                    s_obj = make_script(t["tcode"], t["name"], tactic_name, executor, plat_slug, t["description"])
                    c_obj = make_chain(s_obj["id"], t["tcode"], t["name"], tactic_name)
                    if s_obj["id"] not in existing_ids:
                        added_s.append(s_obj)
                        added_c.append(c_obj)

                if added_s:
                    data["scripts"].extend(added_s)
                    data["chains"].extend(added_c)
                    with open(fpath, "w", encoding="utf-8") as f:
                        json.dump(data, f, indent=2, ensure_ascii=False)
                    total_new_scripts += len(added_s)
                    print(f"  [PATCH] enterprise/windows/{os.path.basename(fpath)}"
                          f"  +{len(added_s)} scripts  (tactic={tactic_id})")

            else:
                # ---- CREATE or MERGE new pack file ----
                os.makedirs(folder_abs, exist_ok=True)
                t_slug      = tactic_slug(tactic_name)
                package_id  = f"excalibur-{dom}-{plat_slug}-{tactic_id}-{t_slug}"
                fname       = f"{package_id}.json"
                fpath       = os.path.join(folder_abs, fname)

                new_scripts = []
                new_chains  = []
                for t in techs:
                    s_obj = make_script(t["tcode"], t["name"], tactic_name, executor, plat_slug, t["description"])
                    c_obj = make_chain(s_obj["id"], t["tcode"], t["name"], tactic_name)
                    new_scripts.append(s_obj)
                    new_chains.append(c_obj)

                if not new_scripts:
                    continue

                if os.path.exists(fpath):
                    # MERGE into existing new-style pack
                    with open(fpath, encoding="utf-8") as f:
                        existing = json.load(f)
                    existing_ids    = {s["id"] for s in existing["scripts"]}
                    existing_chains = {c.get("name", "") for c in existing["chains"]}
                    ms = [s for s in new_scripts if s["id"] not in existing_ids]
                    mc = [c for c in new_chains  if c.get("name", "") not in existing_chains]
                    existing["scripts"].extend(ms)
                    existing["chains"].extend(mc)
                    with open(fpath, "w", encoding="utf-8") as f:
                        json.dump(existing, f, indent=2, ensure_ascii=False)
                    total_new_scripts += len(ms)
                    if ms:
                        print(f"  [MERGE] {folder_rel}/{fname}  +{len(ms)} scripts")
                else:
                    # CREATE brand new pack
                    pack = make_new_pack(
                        package_id,
                        f"Excalibur - {dom.title()} {plat_slug.title()} {tactic_name} ({tactic_id})",
                        dom, tactic_id, tactic_name, plat_slug, stix_domain,
                        new_scripts, new_chains,
                    )
                    with open(fpath, "w", encoding="utf-8") as f:
                        json.dump(pack, f, indent=2, ensure_ascii=False)
                    total_new_scripts += len(new_scripts)
                    total_new_packs   += 1
                    print(f"  [NEW]   {folder_rel}/{fname}  {len(new_scripts)} scripts  {len(new_chains)} chains")

                    # Register in catalog
                    if package_id not in existing_catalog_ids:
                        url = (
                            f"https://raw.githubusercontent.com/x3m-ai/Camelot/main/"
                            f"morgana/excalibur/{folder_rel}/{fname}"
                        )
                        catalog_additions.append({
                            "package_id":        package_id,
                            "package_name":      f"Excalibur - {dom.title()} {plat_slug.title()} {tactic_name} ({tactic_id})",
                            "version":           "1.0.0",
                            "description":       (
                                f"STIX v19.0 auto-generated. {len(new_scripts)} techniques "
                                f"for {tactic_name} ({tactic_id}) on {plat_slug}."
                            ),
                            "mitre_tactic":      f"{tactic_name} ({tactic_id})",
                            "mitre_tcodes":      [s["tcode"] for s in new_scripts],
                            "script_count":      len(new_scripts),
                            "chain_count":       len(new_chains),
                            "platform":          [plat_slug],
                            "prerequisites":     ["Morgana agent installed on target machine"],
                            "sentinel_connectors": [],
                            "status":            "stable",
                            "category":          folder_rel.split("/")[0],
                            "url":               url,
                        })
                        existing_catalog_ids.add(package_id)

        print()

    # -----------------------------------------------------------------------
    # Update catalog.json
    # -----------------------------------------------------------------------
    print("[4/4] Updating catalog.json...")
    if catalog_additions:
        catalog["packs"].extend(catalog_additions)
        catalog["catalog_version"] = "1.2.0"
        catalog["updated"] = TODAY
        with open(CATALOG_FILE, "w", encoding="utf-8") as f:
            json.dump(catalog, f, indent=2, ensure_ascii=False)
        print(f"      Added {len(catalog_additions)} new catalog entries")
    else:
        print("      No new catalog entries needed")

    # -----------------------------------------------------------------------
    # Validate generated JSON (quick check)
    # -----------------------------------------------------------------------
    print("\nValidating generated files...")
    errors = 0
    for fpath in glob.glob(os.path.join(EXCALIBUR_DIR, "**", "*.json"), recursive=True):
        try:
            with open(fpath, encoding="utf-8") as f:
                json.load(f)
        except Exception as exc:
            print(f"  [ERROR] {fpath}: {exc}")
            errors += 1
    if errors == 0:
        print(f"  All JSON files valid")
    else:
        print(f"  {errors} JSON files have errors - fix before committing")

    print()
    print("=" * 60)
    print(f"  COMPLETED")
    print(f"  New scripts added   : {total_new_scripts}")
    print(f"  New pack files      : {total_new_packs}")
    print(f"  Catalog entries     : {len(catalog_additions)}")
    print("=" * 60)


if __name__ == "__main__":
    main()
