#!/usr/bin/env python3
"""
Red Canary Atomic Red Team -> Morgana Excalibur Pack converter.

Reads YAML files from a local Red Canary atomic-red-team/atomics/ checkout
and outputs Morgana Excalibur Pack JSON files grouped by MITRE ATT&CK tactic.

Requirements:
    pip install pyyaml

Usage:
    # Convert all tactics
    python convert_atomics.py --atomics-dir C:\\path\\to\\atomic-red-team\\atomics

    # Convert one tactic only
    python convert_atomics.py --atomics-dir ... --tactic TA0002

    # Windows only, dry run
    python convert_atomics.py --atomics-dir ... --platform windows --dry-run

    # Skip catalog update
    python convert_atomics.py --atomics-dir ... --no-update-catalog

Output goes to: Camelot/morgana/excalibur/art/
"""

import argparse
import json
import os
import re
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path
from typing import Any

try:
    from catalog_guidance import art_guidance
except ImportError:
    from morgana.excalibur.tools.catalog_guidance import art_guidance

try:
    import yaml
except ImportError:
    print("[ERROR] PyYAML required. Run: pip install pyyaml")
    sys.exit(1)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
TOOLS_DIR = Path(__file__).parent
EXCALIBUR_DIR = TOOLS_DIR.parent
OUTPUT_DIR = EXCALIBUR_DIR / "art"
CATALOG_FILE = EXCALIBUR_DIR / "catalog.json"
CATALOG_BASE_URL = "https://raw.githubusercontent.com/x3m-ai/Camelot/main/morgana/excalibur/art"

# ---------------------------------------------------------------------------
# Executor name normalisation: Red Canary → Morgana
# ---------------------------------------------------------------------------
EXECUTOR_MAP: dict[str, str] = {
    "powershell": "powershell",
    "command_prompt": "cmd",
    "sh": "bash",
    "bash": "bash",
    "python": "python",
    "manual": "manual",
}

# Platform name normalisation
PLATFORM_MAP: dict[str, str] = {
    "windows": "windows",
    "linux": "linux",
    "macos": "linux",   # bash executor, treat as linux
    "office-365": "windows",
    "azure": "windows",
    "azure-ad": "windows",
    "google-workspace": "windows",
    "saas": "windows",
    "iaas": "windows",
    "containers": "linux",
}

# ---------------------------------------------------------------------------
# MITRE ATT&CK Enterprise v15 technique -> (tactic_id, tactic_name, tactic_slug)
# Multi-tactic techniques are assigned to their most operationally significant tactic.
# ---------------------------------------------------------------------------
TACTIC_MAP: dict[str, tuple[str, str, str]] = {}

def _add(tcode: str, tactic_id: str, tactic_name: str, tactic_slug: str) -> None:
    TACTIC_MAP[tcode] = (tactic_id, tactic_name, tactic_slug)

# TA0001 Initial Access
for t in ["T1078","T1078.001","T1078.002","T1078.003","T1078.004","T1091",
          "T1133","T1189","T1190","T1195","T1195.001","T1195.002","T1195.003",
          "T1200","T1566","T1566.001","T1566.002","T1566.003","T1566.004"]:
    _add(t, "TA0001", "Initial Access", "initial_access")

# TA0002 Execution
for t in ["T1047","T1053","T1053.001","T1053.002","T1053.003","T1053.004",
          "T1053.005","T1053.006","T1053.007",
          "T1059","T1059.001","T1059.002","T1059.003","T1059.004","T1059.005",
          "T1059.006","T1059.007","T1059.008","T1059.009","T1059.010","T1059.011",
          "T1072","T1106","T1129","T1203",
          "T1204","T1204.001","T1204.002","T1204.003",
          "T1559","T1559.001","T1559.002","T1559.003",
          "T1569","T1569.001","T1569.002",
          "T1620","T1648","T1651"]:
    _add(t, "TA0002", "Execution", "exec")

# TA0003 Persistence
for t in ["T1037","T1037.001","T1037.002","T1037.003","T1037.004","T1037.005",
          "T1098","T1098.001","T1098.002","T1098.003","T1098.004","T1098.005",
          "T1136","T1136.001","T1136.002","T1136.003",
          "T1176","T1176.001","T1176.002",
          "T1197",
          "T1505","T1505.001","T1505.002","T1505.003","T1505.004",
          "T1525",
          "T1542","T1542.001","T1542.002","T1542.003","T1542.004","T1542.005",
          "T1543","T1543.001","T1543.002","T1543.003","T1543.004",
          "T1546","T1546.001","T1546.002","T1546.003","T1546.004","T1546.005",
          "T1546.006","T1546.007","T1546.008","T1546.009","T1546.010",
          "T1546.011","T1546.012","T1546.013","T1546.014","T1546.015","T1546.016",
          "T1547","T1547.001","T1547.002","T1547.003","T1547.004","T1547.005",
          "T1547.006","T1547.007","T1547.008","T1547.009","T1547.010",
          "T1547.011","T1547.012","T1547.013","T1547.014","T1547.015",
          "T1554",
          "T1574","T1574.001","T1574.002","T1574.004","T1574.005","T1574.006",
          "T1574.007","T1574.008","T1574.009","T1574.010","T1574.011","T1574.012","T1574.013"]:
    _add(t, "TA0003", "Persistence", "persist")

# TA0004 Privilege Escalation
for t in ["T1055","T1055.001","T1055.002","T1055.003","T1055.004","T1055.005",
          "T1055.008","T1055.009","T1055.011","T1055.012","T1055.013","T1055.014","T1055.015",
          "T1068",
          "T1134","T1134.001","T1134.002","T1134.003","T1134.004","T1134.005",
          "T1548","T1548.001","T1548.002","T1548.003","T1548.004","T1548.005",
          "T1611"]:
    _add(t, "TA0004", "Privilege Escalation", "privesc")

# TA0005 Defense Evasion
for t in ["T1006","T1014",
          "T1027","T1027.001","T1027.002","T1027.003","T1027.004","T1027.005",
          "T1027.006","T1027.007","T1027.008","T1027.009","T1027.010","T1027.011","T1027.012",
          "T1036","T1036.001","T1036.002","T1036.003","T1036.004","T1036.005",
          "T1036.006","T1036.007","T1036.008","T1036.009","T1036.010",
          "T1070","T1070.001","T1070.002","T1070.003","T1070.004","T1070.005",
          "T1070.006","T1070.007","T1070.008","T1070.009",
          "T1112","T1127","T1127.001","T1140",
          "T1202","T1205","T1205.001","T1205.002","T1207","T1211","T1212",
          "T1216","T1216.001","T1216.002",
          "T1218","T1218.001","T1218.002","T1218.003","T1218.004","T1218.005",
          "T1218.007","T1218.008","T1218.009","T1218.010","T1218.011","T1218.012",
          "T1218.013","T1218.014",
          "T1220","T1221",
          "T1222","T1222.001","T1222.002",
          "T1480","T1480.001",
          "T1497","T1497.001","T1497.002","T1497.003",
          "T1550","T1550.001","T1550.002","T1550.003","T1550.004",
          "T1553","T1553.001","T1553.002","T1553.003","T1553.004","T1553.005","T1553.006",
          "T1556","T1556.001","T1556.002","T1556.003","T1556.004","T1556.005",
          "T1556.006","T1556.007","T1556.008",
          "T1562","T1562.001","T1562.002","T1562.003","T1562.004","T1562.006",
          "T1562.007","T1562.008","T1562.009","T1562.010","T1562.011","T1562.012",
          "T1564","T1564.001","T1564.002","T1564.003","T1564.004","T1564.005",
          "T1564.006","T1564.007","T1564.008","T1564.009","T1564.010","T1564.011",
          "T1578","T1578.001","T1578.002","T1578.003","T1578.004","T1578.005",
          "T1600","T1600.001","T1600.002",
          "T1601","T1601.001","T1601.002",
          "T1610","T1612","T1622","T1647","T1656"]:
    _add(t, "TA0005", "Defense Evasion", "evasion")

# TA0006 Credential Access
for t in ["T1003","T1003.001","T1003.002","T1003.003","T1003.004","T1003.005",
          "T1003.006","T1003.007","T1003.008",
          "T1040",
          "T1056","T1056.001","T1056.002","T1056.003","T1056.004",
          "T1110","T1110.001","T1110.002","T1110.003","T1110.004",
          "T1111","T1187",
          "T1528","T1539",
          "T1552","T1552.001","T1552.002","T1552.003","T1552.004","T1552.005",
          "T1552.006","T1552.007",
          "T1555","T1555.001","T1555.002","T1555.003","T1555.004","T1555.005","T1555.006",
          "T1557","T1557.001","T1557.002","T1557.003",
          "T1558","T1558.001","T1558.002","T1558.003","T1558.004",
          "T1606","T1606.001","T1606.002",
          "T1621","T1649"]:
    _add(t, "TA0006", "Credential Access", "credaccess")

# TA0007 Discovery
for t in ["T1007","T1010","T1012",
          "T1016","T1016.001","T1016.002",
          "T1018","T1033","T1046","T1049","T1057",
          "T1069","T1069.001","T1069.002","T1069.003",
          "T1082","T1083",
          "T1087","T1087.001","T1087.002","T1087.003","T1087.004",
          "T1120","T1124","T1135","T1201",
          "T1217","T1217.001","T1217.002",
          "T1482",
          "T1518","T1518.001",
          "T1526","T1538","T1580","T1613",
          "T1614","T1614.001",
          "T1619"]:
    _add(t, "TA0007", "Discovery", "discovery")

# TA0008 Lateral Movement
for t in ["T1021","T1021.001","T1021.002","T1021.003","T1021.004","T1021.005",
          "T1021.006","T1021.007","T1021.008",
          "T1080","T1210","T1534","T1534.001",
          "T1563","T1563.001","T1563.002","T1570"]:
    _add(t, "TA0008", "Lateral Movement", "lateral")

# TA0009 Collection
for t in ["T1005","T1025","T1039",
          "T1074","T1074.001","T1074.002",
          "T1113",
          "T1114","T1114.001","T1114.002","T1114.003",
          "T1115","T1119","T1123","T1125","T1185",
          "T1213","T1213.001","T1213.002","T1213.003","T1213.004","T1213.005",
          "T1530",
          "T1560","T1560.001","T1560.002","T1560.003",
          "T1602","T1602.001","T1602.002"]:
    _add(t, "TA0009", "Collection", "collection")

# TA0010 Exfiltration
for t in ["T1011","T1011.001","T1020","T1020.001","T1022","T1029","T1030","T1041",
          "T1048","T1048.001","T1048.002","T1048.003",
          "T1052","T1052.001",
          "T1567","T1567.001","T1567.002","T1567.003","T1567.004"]:
    _add(t, "TA0010", "Exfiltration", "exfil")

# TA0011 Command and Control
for t in ["T1001","T1001.001","T1001.002","T1001.003","T1008",
          "T1071","T1071.001","T1071.002","T1071.003","T1071.004",
          "T1090","T1090.001","T1090.002","T1090.003","T1090.004",
          "T1092","T1095",
          "T1102","T1102.001","T1102.002","T1102.003",
          "T1104","T1105",
          "T1132","T1132.001","T1132.002",
          "T1219","T1219.001","T1219.002","T1219.003",
          "T1568","T1568.001","T1568.002","T1568.003",
          "T1571","T1572",
          "T1573","T1573.001","T1573.002"]:
    _add(t, "TA0011", "Command and Control", "c2")

# TA0040 Impact
for t in ["T1485","T1486","T1489","T1490",
          "T1491","T1491.001","T1491.002",
          "T1495","T1496",
          "T1498","T1498.001","T1498.002",
          "T1499","T1499.001","T1499.002","T1499.003","T1499.004",
          "T1529","T1531",
          "T1561","T1561.001","T1561.002",
          "T1565","T1565.001","T1565.002","T1565.003",
          "T1657"]:
    _add(t, "TA0040", "Impact", "impact")

# TA0042 Resource Development
for t in ["T1583","T1583.001","T1583.002","T1583.003","T1583.004","T1583.005","T1583.006","T1583.007",
          "T1584","T1585","T1586","T1587","T1588","T1608"]:
    _add(t, "TA0042", "Resource Development", "resource_dev")

# TA0043 Reconnaissance
for t in ["T1589","T1589.001","T1589.002","T1589.003",
          "T1590","T1590.001","T1590.002","T1590.003","T1590.004","T1590.005","T1590.006",
          "T1591","T1592","T1593","T1594",
          "T1595","T1596","T1597","T1598"]:
    _add(t, "TA0043", "Reconnaissance", "recon")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def sanitize_key(s: str) -> str:
    """Lowercase, replace non-alnum with underscore, collapse runs."""
    s = s.lower()
    s = re.sub(r"[^a-z0-9]+", "_", s)
    s = s.strip("_")
    return s


def tcode_to_key_part(tcode: str) -> str:
    """T1059.001 -> 1059_001"""
    return tcode.lstrip("T").replace(".", "_")


def make_tag_key(tactic_slug: str, tcode: str, arg_name: str) -> str:
    """art_exec_1059_001_input_file (max ~60 chars)."""
    part = f"art_{tactic_slug}_{tcode_to_key_part(tcode)}_{sanitize_key(arg_name)}"
    return part[:64]


def normalize_platform(platforms: list[str]) -> str:
    """Return the best Morgana platform string from a list of Red Canary platforms."""
    if not platforms:
        return "windows"
    for p in platforms:
        mapped = PLATFORM_MAP.get(p.lower(), "")
        if mapped:
            return mapped
    return "windows"


def normalize_executor(executor_name: str) -> str:
    return EXECUTOR_MAP.get(executor_name.lower(), "manual")


def truncate(s: str, n: int = 100) -> str:
    if len(s) <= n:
        return s
    return s[:n - 3] + "..."


def rename_placeholders(text: str, arg_rename: dict[str, str]) -> str:
    """Replace #{old_name} with #{new_key} in a command string."""
    for old, new in arg_rename.items():
        text = text.replace(f"#{{#{old}}}", f"#{{{new}}}")  # #{#{arg}} edge case
        text = text.replace(f"#{{{old}}}", f"#{{{new}}}")
    return text


def parse_atomic_file(yaml_path: Path) -> dict | None:
    with open(yaml_path, encoding="utf-8", errors="replace") as f:
        try:
            return yaml.safe_load(f)
        except yaml.YAMLError as e:
            print(f"  [WARN] YAML parse error in {yaml_path.name}: {e}")
            return None


# ---------------------------------------------------------------------------
# Core conversion logic
# ---------------------------------------------------------------------------

def convert_atomic_test(
    tcode: str,
    tactic_id: str,
    tactic_name: str,
    tactic_slug: str,
    test: dict,
    platform_filter: str | None,
) -> dict | None:
    """
    Convert one atomic_test dict into a Morgana script entry.
    Returns None if the test should be skipped.
    """
    executor_block = test.get("executor", {})
    if not executor_block:
        return None

    executor_name = executor_block.get("name", "")
    executor = normalize_executor(executor_name)

    if executor == "manual" and platform_filter:
        # skip manual tests when a specific platform is requested
        return None

    raw_command: str = executor_block.get("command", "") or ""
    raw_cleanup: str = executor_block.get("cleanup_command", "") or ""

    if not raw_command.strip() and executor != "manual":
        return None

    platforms: list[str] = test.get("supported_platforms", ["windows"])
    platform = normalize_platform(platforms)

    if platform_filter and platform != platform_filter:
        return None

    # Build arg rename map and tag_category entries for this test
    input_args: dict[str, Any] = test.get("input_arguments", {}) or {}
    arg_rename: dict[str, str] = {}
    arg_entries: list[dict] = []

    for arg_name, arg_info in input_args.items():
        if not isinstance(arg_info, dict):
            continue
        new_key = make_tag_key(tactic_slug, tcode, arg_name)
        arg_rename[arg_name] = new_key

        default_val = str(arg_info.get("default", "")) if arg_info.get("default") is not None else ""
        arg_entries.append({
            "key": new_key,
            "label": arg_name.replace("_", " ").title(),
            "description": truncate(str(arg_info.get("description", "")), 200),
            "default": default_val,
            "example": default_val,
            "sensitive": False,
            "required": False,
        })

    command = rename_placeholders(raw_command.strip(), arg_rename)
    cleanup = rename_placeholders(raw_cleanup.strip(), arg_rename) if raw_cleanup.strip() else ""

    test_name = truncate(test.get("name", "Unnamed Test"), 60)
    script_name = f"ART - {tcode} - {test_name}"

    description = truncate(
        test.get("description", f"Red Canary Atomic Red Team test for {tcode}."),
        300,
    )

    return {
        "script_name": script_name,
        "script": {
            "id": script_name,
            "name": script_name,
            "description": description,
            "tactic": tactic_name,
            "tcode": tcode,
            "technique_name": test_name,
            "executor": executor,
            "platform": platform,
            "required_tags": [e["key"] for e in arg_entries],
            "command": command,
            "cleanup_command": cleanup,
            "detection_rule": "See MITRE ATT&CK page for detection guidance",
            "sentinel_connector": "Microsoft Defender for Endpoint",
            "source": "atomic-red-team",
            "atomic_guid": test.get("auto_generated_guid", ""),
        },
        "arg_entries": arg_entries,
    }


def build_pack(
    tactic_id: str,
    tactic_name: str,
    tactic_slug: str,
    scripts: list[dict],
    all_arg_entries: dict[str, dict],
) -> dict:
    """Assemble the Excalibur pack JSON for one tactic."""
    package_id = f"art-{tactic_slug}-v1"
    package_name = f"ART - {tactic_name} Pack (Red Canary)"

    tcodes_seen = sorted({s["tcode"] for s in scripts})
    platforms_seen = sorted({s["platform"] for s in scripts})

    # Build tag_categories: one category per TCode that has args
    tag_cat_by_tcode: dict[str, list[dict]] = defaultdict(list)
    for key, entry in all_arg_entries.items():
        # extract tcode from key: art_{tactic_slug}_{1059_001}_{arg}
        # key format: art_{tactic_slug}_{tcode_key}_{arg_name}
        # we stored the tcode separately in the entry
        tcode_key = entry.get("_tcode", "")
        tag_cat_by_tcode[tcode_key].append(entry)

    tag_categories = []
    for tcode_key, tags in sorted(tag_cat_by_tcode.items()):
        tcode_display = tcode_key.replace("_", ".").upper()
        clean_tags = [{k: v for k, v in t.items() if not k.startswith("_")} for t in tags]
        tag_categories.append({
            "category_id": f"art_{tactic_slug}_{tcode_key}",
            "label": f"{tcode_display} Parameters",
            "description": f"Input parameters for {tcode_display} atomic tests.",
            "scope": "local",
            "used_by_tcodes": [tcode_display],
            "tags": clean_tags,
        })

    script_entries = [{k: v for k, v in s.items() if k not in ("_tcode",)} for s in scripts]

    # One chain per script (1-step chains)
    chains = [
        {
            "name": s["name"],
            "description": f"Single-step chain for {s['tcode']} — {s['technique_name']}",
            "package": package_id,
            "tcode": s["tcode"],
            "tactic": tactic_name,
            "script_refs": [s["name"]],
        }
        for s in script_entries
    ]

    # Full tactic chain (all scripts in sequence)
    if len(script_entries) > 1:
        chains.append({
            "name": f"ART - {tactic_name} - Full Tactic Chain",
            "description": f"Runs all {len(script_entries)} ART scripts for {tactic_name} ({tactic_id}) in sequence.",
            "package": package_id,
            "tcode": tcodes_seen[0],
            "tactic": tactic_name,
            "script_refs": [s["name"] for s in script_entries],
        })

    guidance = art_guidance(tactic_name, len(script_entries), len(tcodes_seen))
    return {
        "package_id": package_id,
        "package_name": package_name,
        "version": "1.0.0",
        "description": (
            f"Red Canary Atomic Red Team scripts for MITRE ATT&CK {tactic_name} ({tactic_id}). "
            f"{len(script_entries)} atomics covering {len(tcodes_seen)} techniques: "
            f"{', '.join(tcodes_seen[:10])}{'...' if len(tcodes_seen) > 10 else ''}. "
            "Converted from Red Canary atomic-red-team YAML. Tag keys prefixed with 'art_'."
        ),
        "author": "Red Canary (converted by X3M.AI)",
        "created": str(date.today()),
        "provider": "atomic-red-team",
        "source": "atomic-red-team",
        "mitre_domain": "enterprise-attack",
        "mitre_tactic": f"{tactic_name} ({tactic_id})",
        "mitre_tactic_name": tactic_name,
        "mitre_tcodes": tcodes_seen,
        "platform": platforms_seen,
        "prerequisites": [
            "Morgana agent installed on target machine",
            "PyYAML not required at runtime — scripts are pre-converted",
        ],
        **guidance,
        "tag_categories": tag_categories,
        "scripts": script_entries,
        "chains": chains,
    }


# ---------------------------------------------------------------------------
# Catalog update
# ---------------------------------------------------------------------------

def update_catalog(packs_meta: list[dict], dry_run: bool) -> None:
    if not CATALOG_FILE.exists():
        print(f"  [WARN] catalog.json not found at {CATALOG_FILE}")
        return

    with open(CATALOG_FILE, encoding="utf-8") as f:
        catalog = json.load(f)

    existing_ids = {p["package_id"] for p in catalog.get("packs", [])}
    added = 0
    updated = 0

    for meta in packs_meta:
        pid = meta["package_id"]
        entry = {
            "package_id": pid,
            "package_name": meta["package_name"],
            "version": meta["version"],
            "description": meta["description"],
            "mitre_tactic": meta["mitre_tactic"],
            "mitre_tcodes": meta["mitre_tcodes"],
            "script_count": meta["script_count"],
            "chain_count": meta["chain_count"],
            "platform": meta["platform"],
            "prerequisites": meta["prerequisites"],
            "capabilities": meta["capabilities"],
            "use_cases": meta["use_cases"],
            "safety_notes": meta["safety_notes"],
            "sentinel_connectors": [],
            "status": "community",
            "provider": "atomic-red-team",
            "author": "Red Canary (converted by X3M.AI)",
            "source": "atomic-red-team",
            "category": "art",
            "url": f"{CATALOG_BASE_URL}/{pid}.json",
        }
        if pid in existing_ids:
            catalog["packs"] = [entry if p["package_id"] == pid else p for p in catalog["packs"]]
            updated += 1
        else:
            catalog["packs"].append(entry)
            added += 1

    from datetime import date as _date
    catalog["catalog_version"] = "1.5.0"
    catalog["updated"] = str(_date.today())

    if not dry_run:
        with open(CATALOG_FILE, "w", encoding="utf-8") as f:
            json.dump(catalog, f, indent=2, ensure_ascii=False)
    print(f"  catalog.json: {added} added, {updated} updated{'  (dry run)' if dry_run else ''}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Convert Red Canary Atomic Red Team YAML to Morgana Excalibur packs")
    parser.add_argument("--atomics-dir", required=True,
                        help="Path to atomic-red-team/atomics/ directory")
    parser.add_argument("--out-dir", default=str(OUTPUT_DIR),
                        help=f"Output directory for pack JSON files (default: {OUTPUT_DIR})")
    parser.add_argument("--tactic", default=None,
                        help="Convert only this tactic (e.g. TA0002)")
    parser.add_argument("--platform", default=None, choices=["windows", "linux"],
                        help="Filter by platform")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show what would be generated without writing files")
    parser.add_argument("--skip-manual", action="store_true", default=True,
                        help="Skip scripts with executor=manual (default: true)")
    parser.add_argument("--no-update-catalog", action="store_true",
                        help="Do not update catalog.json")
    parser.add_argument("--max-per-pack", type=int, default=0,
                        help="Max scripts per pack (0 = unlimited)")
    args = parser.parse_args()

    atomics_dir = Path(args.atomics_dir)
    out_dir = Path(args.out_dir)

    if not atomics_dir.exists():
        print(f"[ERROR] atomics-dir not found: {atomics_dir}")
        sys.exit(1)

    if not args.dry_run:
        out_dir.mkdir(parents=True, exist_ok=True)

    # Scan for T*.yaml files
    yaml_files = sorted(atomics_dir.rglob("T*.yaml"))
    if not yaml_files:
        print(f"[ERROR] No T*.yaml files found in {atomics_dir}")
        sys.exit(1)

    print(f"[INFO] Found {len(yaml_files)} YAML files in {atomics_dir}")

    # Group script entries by tactic
    tactic_scripts: dict[str, list[dict]] = defaultdict(list)
    tactic_args: dict[str, dict[str, dict]] = defaultdict(dict)   # tactic -> {key -> entry}
    tactic_meta: dict[str, tuple[str, str, str]] = {}             # tactic_id -> (id, name, slug)
    skipped = 0
    total_tests = 0

    for yaml_path in yaml_files:
        data = parse_atomic_file(yaml_path)
        if not data:
            continue

        tcode: str = data.get("attack_technique", "")
        if not tcode:
            continue
        tcode = tcode.strip()

        tactic_info = TACTIC_MAP.get(tcode)
        if not tactic_info:
            # try parent technique (T1059.001 -> T1059)
            parent = tcode.split(".")[0]
            tactic_info = TACTIC_MAP.get(parent)
        if not tactic_info:
            skipped += 1
            continue

        tactic_id, tactic_name, tactic_slug = tactic_info

        if args.tactic and tactic_id != args.tactic:
            continue

        tactic_meta[tactic_id] = (tactic_id, tactic_name, tactic_slug)

        for test in data.get("atomic_tests", []):
            total_tests += 1
            result = convert_atomic_test(
                tcode, tactic_id, tactic_name, tactic_slug,
                test, args.platform
            )
            if not result:
                skipped += 1
                continue

            if args.skip_manual and result["script"]["executor"] == "manual":
                skipped += 1
                continue

            # Deduplicate script names within a tactic
            script = result["script"]
            script_name = script["name"]
            existing_names = {s["name"] for s in tactic_scripts[tactic_id]}
            if script_name in existing_names:
                guid = test.get("auto_generated_guid", "")[:8]
                script["name"] = f"{script_name} [{guid}]"
                script["id"] = script["name"]

            tactic_scripts[tactic_id].append(script)

            # Accumulate tag entries, keyed by tag key (dedup by key)
            for entry in result["arg_entries"]:
                key = entry["key"]
                if key not in tactic_args[tactic_id]:
                    tcode_key = tcode_to_key_part(tcode)
                    tactic_args[tactic_id][key] = {**entry, "_tcode": tcode_key}

    print(f"[INFO] Processed {total_tests} tests, skipped {skipped}")
    print(f"[INFO] Tactics with scripts: {sorted(tactic_meta.keys())}")

    # Generate one pack per tactic
    packs_meta: list[dict] = []
    for tactic_id, (tid, tname, tslug) in sorted(tactic_meta.items()):
        scripts = tactic_scripts[tactic_id]
        if args.max_per_pack and len(scripts) > args.max_per_pack:
            scripts = scripts[:args.max_per_pack]

        if not scripts:
            continue

        all_args = tactic_args[tactic_id]
        pack = build_pack(tid, tname, tslug, scripts, all_args)

        filename = f"{pack['package_id']}.json"
        out_path = out_dir / filename

        print(f"\n[PACK] {pack['package_id']}  ({len(scripts)} scripts, {len(pack['chains'])} chains)")
        print(f"       TCodes: {', '.join(pack['mitre_tcodes'][:8])}{'...' if len(pack['mitre_tcodes']) > 8 else ''}")
        print(f"       Output: {out_path}")

        if not args.dry_run:
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(pack, f, indent=2, ensure_ascii=False)
            print(f"       [OK] Written")

        packs_meta.append({
            "package_id": pack["package_id"],
            "package_name": pack["package_name"],
            "version": pack["version"],
            "description": pack["description"],
            "mitre_tactic": pack["mitre_tactic"],
            "mitre_tcodes": pack["mitre_tcodes"],
            "script_count": len(scripts),
            "chain_count": len(pack["chains"]),
            "platform": pack["platform"],
            "prerequisites": pack["prerequisites"],
            "capabilities": pack["capabilities"],
            "use_cases": pack["use_cases"],
            "safety_notes": pack["safety_notes"],
        })

    if packs_meta and not args.no_update_catalog:
        print("\n[CATALOG] Updating catalog.json...")
        update_catalog(packs_meta, args.dry_run)

    total_scripts = sum(m["script_count"] for m in packs_meta)
    total_chains = sum(m["chain_count"] for m in packs_meta)
    print(f"\n[DONE] {len(packs_meta)} packs, {total_scripts} scripts, {total_chains} chains")
    if args.dry_run:
        print("       (dry run — no files written)")


if __name__ == "__main__":
    main()
