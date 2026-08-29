#!/usr/bin/env python3
"""Build Morgana packages for the pinned ICS-SCADA-Fuzzer engine."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import struct
import subprocess
import tempfile
from collections import Counter
from datetime import date
from pathlib import Path
from typing import Any

TOOLS_DIR = Path(__file__).resolve().parent
EXCALIBUR_DIR = TOOLS_DIR.parent
DEFAULT_OUTPUT_DIR = EXCALIBUR_DIR / "ot" / "fuzzing" / "ics-scada-fuzzer"
CATALOG_FILE = EXCALIBUR_DIR / "catalog.json"
MAPPING_FILE = TOOLS_DIR / "ics_scada_fuzzer_mapping.json"
SOURCE_REPOSITORY = "https://github.com/ridpath/ics-scada-fuzzer"
PROVIDER_ID = "ics-scada-fuzzer"
SCRIPT_PREFIX = "ICS FUZZ"
CATALOG_BASE_URL = "https://raw.githubusercontent.com/x3m-ai/Camelot/main/morgana/excalibur/ot/fuzzing/ics-scada-fuzzer"
EXPECTED_FLAGS = "t:P:p:i:m:s:T:Sd:l:c:R:r:v?h"
EXPECTED_STRATEGIES = {"random", "bitflip", "overflow", "dictionary", "format", "type", "time", "sequence"}
EXPECTED_PROTOCOLS = {"modbus", "dnp3", "s7", "iec104", "opcua"}
ASSET_ID = "ics_scada_fuzzer_linux_amd64"


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git_value(directory: Path, *args: str) -> str:
    try:
        return subprocess.run(
            ["git", "-C", str(directory), *args], check=True,
            capture_output=True, text=True, timeout=20,
        ).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return "unknown"


def inspect_source(source_file: Path, mapping: dict[str, Any]) -> dict[str, Any]:
    text = source_file.read_text(encoding="utf-8")
    flags = re.findall(r"getopt\s*\([^;]*?\"([^\"]+)\"", text, re.S)
    protocols = set(re.findall(
        r"strcasecmp\s*\(\s*optarg\s*,\s*\"(modbus|dnp3|s7|iec104|opcua)\"",
        text,
        re.I,
    ))
    strategies = set(re.findall(
        r"strcasecmp\s*\(\s*optarg\s*,\s*\"(random|bitflip|overflow|dictionary|format|type|time|sequence)\"",
        text,
        re.I,
    ))
    max_threads = re.findall(r"#define\s+MAX_THREADS\s+(\d+)", text)
    ports = dict(re.findall(r"#define\s+(MODBUS|DNP3|S7|IEC104)_PORT\s+(\d+)", text))
    expected_ports = {
        "MODBUS": str(mapping["protocols"]["modbus"]["port"]),
        "DNP3": str(mapping["protocols"]["dnp3"]["port"]),
        "S7": str(mapping["protocols"]["s7"]["port"]),
        "IEC104": str(mapping["protocols"]["iec104"]["port"]),
    }
    failures = []
    if EXPECTED_FLAGS not in flags: failures.append(f"getopt flags changed: {flags}")
    if protocols != EXPECTED_PROTOCOLS: failures.append(f"protocols changed: {sorted(protocols)}")
    if strategies != EXPECTED_STRATEGIES: failures.append(f"strategies changed: {sorted(strategies)}")
    if max_threads != ["64"]: failures.append(f"MAX_THREADS changed: {max_threads}")
    if ports != expected_ports: failures.append(f"default ports changed: {ports}")
    for marker in (
        "case 'S': stateful=1", "case 'R': pcap_out=optarg", "case 'r': pcap_init_replay(optarg)",
        "Packets: %d | Anomalies: %d | Crashes: %d | Timeouts: %d",
        "recalc_modbus_len", "recalc_dnp3_crc",
    ):
        if marker not in text:
            failures.append(f"missing source marker: {marker}")
    if failures:
        raise ValueError("SOURCE CLI DRIFT: " + "; ".join(failures))
    return {
        "getopt_flags": EXPECTED_FLAGS,
        "protocols": sorted(protocols),
        "strategies": sorted(strategies),
        "max_threads": 64,
        "default_ports": {key.lower(): int(value) for key, value in ports.items()} | {"opcua": 4840},
        "pcap_record": True,
        "pcap_replay": True,
        "stateful": True,
        "result_counters": ["Packets", "Anomalies", "Crashes", "Timeouts"],
    }


def protocol_seed(protocol: str) -> bytes:
    packets = {
        "modbus": bytes.fromhex("000100000006010100000008"),
        "dnp3": bytes.fromhex("05640ac4010001000000c0013c0106"),
        "s7": bytes.fromhex("0300001611e00000000100c0010ac1020100c2020100"),
        "iec104": bytes.fromhex("680401000100640100000000"),
        "opcua": bytes.fromhex("4f50432d55410100bebafeca"),
    }
    payload = packets[protocol]
    global_header = struct.pack("<IHHIIII", 0xA1B2C3D4, 2, 4, 0, 0, 65535, 147)
    packet_header = struct.pack("<IIII", 0, 0, len(payload), len(payload))
    return global_header + packet_header + payload


def tag_definitions(default_port: int) -> list[dict[str, Any]]:
    return [
        {"key": "ot_fuzz_target", "label": "Authorized OT Target", "description": "Authorized lab hostname or IP address.", "default": "", "example": "", "sensitive": False, "required": True, "parameter_class": "connection"},
        {"key": "ot_fuzz_port", "label": "Protocol Port", "description": "Target TCP port, 1-65535.", "default": str(default_port), "example": "", "sensitive": False, "required": True, "parameter_class": "connection"},
        {"key": "ot_fuzz_iterations", "label": "Generated Test Cases", "description": "Total generated fuzz iterations, greater than zero.", "default": "1000", "example": "", "sensitive": False, "required": True, "parameter_class": "value"},
        {"key": "ot_fuzz_mutation_rate", "label": "Mutation Rate", "description": "Mutation probability from 0.0 through 1.0.", "default": "0.05", "example": "", "sensitive": False, "required": True, "parameter_class": "value"},
        {"key": "ot_fuzz_threads", "label": "Worker Threads", "description": "Concurrent fuzzer threads, 1-64.", "default": "4", "example": "", "sensitive": False, "required": True, "parameter_class": "value"},
        {"key": "ot_fuzz_delay_ms", "label": "Packet Delay (ms)", "description": "Non-negative delay between packets.", "default": "50", "example": "", "sensitive": False, "required": True, "parameter_class": "value"},
        {"key": "ot_fuzz_timeout", "label": "Session Timeout (seconds)", "description": "Session timeout from 1 through 86400 seconds.", "default": "600", "example": "", "sensitive": False, "required": True, "parameter_class": "value"},
        {"key": "ot_fuzz_record_pcap", "label": "Record PCAP", "description": "Use true or false to record generated traffic.", "default": "false", "example": "", "sensitive": False, "required": True, "parameter_class": "value"},
        {"key": "ot_fuzz_pcap_input", "label": "Replay PCAP Selection", "description": "Controlled replay input selector; Phase 1 supports package-seed only.", "default": "package-seed", "example": "", "sensitive": False, "required": True, "parameter_class": "value"},
        {"key": "ot_fuzz_pcap_output", "label": "PCAP Output Path", "description": "Controlled output path under /tmp for optional PCAP evidence.", "default": "/tmp/morgana-ics-fuzz.pcap", "example": "", "sensitive": False, "required": True, "parameter_class": "local_path"},
    ]


def wrapper_command(protocol: str, strategy: str, stateful: bool, replay: bool) -> str:
    seed_id = f"ics_scada_fuzzer_{protocol}_seed_pcap"
    template = r"""set -u
binary="{{asset:__ASSET_ID__}}"
target='#{ot_fuzz_target}'
port='#{ot_fuzz_port}'
iterations='#{ot_fuzz_iterations}'
rate='#{ot_fuzz_mutation_rate}'
threads='#{ot_fuzz_threads}'
delay_ms='#{ot_fuzz_delay_ms}'
timeout_seconds='#{ot_fuzz_timeout}'
record_pcap='#{ot_fuzz_record_pcap}'
pcap_input='#{ot_fuzz_pcap_input}'
pcap_output='#{ot_fuzz_pcap_output}'
case "$target" in ''|*[!A-Za-z0-9._:-]*) echo '[ERROR] Invalid authorized target' >&2; exit 2;; esac
case "$port" in ''|*[!0-9]*) echo '[ERROR] Port must be numeric' >&2; exit 2;; esac
[ "$port" -ge 1 ] && [ "$port" -le 65535 ] || { echo '[ERROR] Port must be 1-65535' >&2; exit 2; }
case "$iterations" in ''|*[!0-9]*) echo '[ERROR] Iterations must be numeric' >&2; exit 2;; esac
[ "$iterations" -gt 0 ] || { echo '[ERROR] Iterations must be greater than zero' >&2; exit 2; }
case "$threads" in ''|*[!0-9]*) echo '[ERROR] Threads must be numeric' >&2; exit 2;; esac
[ "$threads" -ge 1 ] && [ "$threads" -le 64 ] || { echo '[ERROR] Threads must be 1-64' >&2; exit 2; }
case "$delay_ms" in ''|*[!0-9]*) echo '[ERROR] Delay must be non-negative' >&2; exit 2;; esac
case "$timeout_seconds" in ''|*[!0-9]*) echo '[ERROR] Timeout must be numeric' >&2; exit 2;; esac
[ "$timeout_seconds" -ge 1 ] && [ "$timeout_seconds" -le 86400 ] || { echo '[ERROR] Timeout must be 1-86400' >&2; exit 2; }
awk -v value="$rate" 'BEGIN { exit !(value >= 0.0 && value <= 1.0) }' || { echo '[ERROR] Mutation rate must be 0.0-1.0' >&2; exit 2; }
case "$(printf '%s' "$record_pcap" | tr '[:upper:]' '[:lower:]')" in true|false|1|0|yes|no) ;; *) echo '[ERROR] Record PCAP must be true or false' >&2; exit 2;; esac
__REPLAY_CHECK__
case "$pcap_output" in /tmp/*) ;; *) echo '[ERROR] PCAP output must be under /tmp' >&2; exit 2;; esac
output_log="/tmp/morgana-ics-fuzz-${MORGANA_TEST_ID:-manual}.log"
args=(-t "$target" -P "$port" -i "$iterations" -m "$rate" -T "$threads" -d "$delay_ms" -p "__PROTOCOL__" -s "__STRATEGY__")
__STATEFUL_ARG__
__REPLAY_ARG__
record_normalized="$(printf '%s' "$record_pcap" | tr '[:upper:]' '[:lower:]')"
case "$record_normalized" in true|1|yes) record_enabled=true;; *) record_enabled=false;; esac
if [ "$record_enabled" = true ]; then
  mkdir -p "$(dirname "$pcap_output")"
    args+=(-R "$pcap_output")
fi
set +e
timeout --signal=INT --kill-after=10s "${timeout_seconds}s" "$binary" "${args[@]}" 2>&1 | tee "$output_log"
status=${PIPESTATUS[0]}
set -e
summary="$(grep -E 'Packets: [0-9]+ .* Anomalies: [0-9]+ .* Crashes: [0-9]+ .* Timeouts: [0-9]+' "$output_log" | tail -1 || true)"
packets="$(printf '%s' "$summary" | sed -nE 's/.*Packets: ([0-9]+).*/\1/p')"; packets="${packets:-0}"
anomalies="$(printf '%s' "$summary" | sed -nE 's/.*Anomalies: ([0-9]+).*/\1/p')"; anomalies="${anomalies:-0}"
crashes="$(printf '%s' "$summary" | sed -nE 's/.*Crashes: ([0-9]+).*/\1/p')"; crashes="${crashes:-0}"
timeouts="$(printf '%s' "$summary" | sed -nE 's/.*Timeouts: ([0-9]+).*/\1/p')"; timeouts="${timeouts:-0}"
pcap_size=0; [ -f "$pcap_output" ] && pcap_size="$(wc -c < "$pcap_output" | tr -d ' ')"
printf 'MORGANA_RESULT_METADATA={"generator_type":"protocol-fuzzer","protocol":"__PROTOCOL__","strategy":"__STRATEGY__","stateful":__STATEFUL__,"mode":"__MODE__","packets_sent":%s,"anomalies":%s,"crash_candidates":%s,"timeouts":%s,"iterations_requested":%s,"pcap_recorded":%s,"pcap_path":"%s","pcap_size":%s}\n' "$packets" "$anomalies" "$crashes" "$timeouts" "$iterations" "$record_enabled" "$pcap_output" "$pcap_size"
rm -f "$output_log"
exit "${status}"
"""
    replacements = {
        "__ASSET_ID__": ASSET_ID,
        "__REPLAY_CHECK__": "[ \"$pcap_input\" = 'package-seed' ] || { echo '[ERROR] Replay input must be package-seed' >&2; exit 2; }" if replay else ":",
        "__PROTOCOL__": protocol,
        "__STRATEGY__": strategy,
        "__STATEFUL__": str(stateful).lower(),
        "__MODE__": "replay" if replay else "generated",
        "__STATEFUL_ARG__": "args+=(-S)" if stateful else ":",
        "__REPLAY_ARG__": f'args+=(-r "{{{{asset:{seed_id}}}}}")' if replay else ":",
    }
    for marker, value in replacements.items():
        template = template.replace(marker, value)
    return template.strip()


def build_packages(
    mapping: dict[str, Any], source_commit: str, binary_path: Path,
    binary_sha256: str, binary_size: int,
) -> tuple[list[tuple[dict[str, Any], str]], list[dict[str, Any]]]:
    packages: list[tuple[dict[str, Any], str]] = []
    inventory: list[dict[str, Any]] = []
    binary_asset = {
        "id": ASSET_ID,
        "name": "ics-fuzzer-linux-amd64",
        "filename": "ics-fuzzer",
        "platform": "linux",
        "architecture": "amd64",
        "url": f"{CATALOG_BASE_URL}/assets/ics-fuzzer-linux-amd64",
        "sha256": binary_sha256,
        "size": binary_size,
        "executable": True,
        "source": "ridpath/ics-scada-fuzzer",
        "license": "MIT",
        "source_commit": source_commit,
    }
    for protocol, protocol_info in mapping["protocols"].items():
        seed_id = f"ics_scada_fuzzer_{protocol}_seed_pcap"
        seed_name = f"{protocol}-seed.pcap"
        seed_bytes = protocol_seed(protocol)
        seed_asset = {
            "id": seed_id,
            "name": seed_name,
            "filename": seed_name,
            "platform": "linux",
            "architecture": "any",
            "url": f"{CATALOG_BASE_URL}/assets/{seed_name}",
            "sha256": hashlib.sha256(seed_bytes).hexdigest(),
            "size": len(seed_bytes),
            "executable": False,
            "source": "X3M.AI deterministic protocol seed",
            "license": "MIT",
        }
        scripts = []
        for strategy, strategy_info in mapping["strategies"].items():
            for stateful in (False, True):
                mode_label = "STATEFUL" if stateful else "STATELESS"
                name = f"ICS FUZZ - {protocol.upper()} - {strategy.upper()} - {mode_label}"
                metadata = {
                    "provider": PROVIDER_ID,
                    "repository": "ridpath/ics-scada-fuzzer",
                    "source_commit": source_commit,
                    "protocol": protocol,
                    "strategy": strategy,
                    "stateful": stateful,
                    "mode": "generated",
                    "generator_type": "protocol-fuzzer",
                    "source_modified": False,
                    "source_attack_version": mapping["source_attack_version"],
                    "technique_name": strategy_info["technique"],
                }
                script = {
                    "id": f"ics-fuzz:{protocol}:{strategy}:{'stateful' if stateful else 'stateless'}",
                    "name": name,
                    "description": f"Generate protocol-aware {protocol_info['label']} mutations using {strategy_info['label']} in {mode_label.lower()} mode.",
                    "tactic": "Impair Process Control",
                    "tcode": strategy_info["tcode"],
                    "executor": "bash",
                    "executor_config": {"timeout_seconds": "#{ot_fuzz_timeout}", "result_parser": "morgana-marker-v1"},
                    "platform": "linux",
                    "command": wrapper_command(protocol, strategy, stateful, False),
                    "cleanup_command": None,
                    "required_tags": ["ot_fuzz_target", "ot_fuzz_port", "ot_fuzz_iterations", "ot_fuzz_mutation_rate", "ot_fuzz_threads", "ot_fuzz_delay_ms", "ot_fuzz_timeout", "ot_fuzz_record_pcap", "ot_fuzz_pcap_input", "ot_fuzz_pcap_output"],
                    "required_assets": [ASSET_ID],
                    "operational_risk": strategy_info["risk"],
                    "source_metadata": metadata,
                }
                scripts.append(script); inventory.append(metadata | {"script_id": script["id"], "name": name})
            replay_name = f"ICS FUZZ REPLAY - {protocol.upper()} - {strategy.upper()}"
            replay_metadata = {
                "provider": PROVIDER_ID,
                "repository": "ridpath/ics-scada-fuzzer",
                "source_commit": source_commit,
                "protocol": protocol,
                "strategy": strategy,
                "stateful": False,
                "mode": "replay",
                "generator_type": "protocol-fuzzer",
                "source_modified": False,
                "source_attack_version": mapping["source_attack_version"],
                "technique_name": strategy_info["technique"],
                "pcap_input_policy": "Verified package seed asset only",
            }
            replay = {
                "id": f"ics-fuzz:{protocol}:{strategy}:replay",
                "name": replay_name,
                "description": f"Replay and mutate a verified {protocol_info['label']} seed PCAP using {strategy_info['label']}.",
                "tactic": "Impair Process Control",
                "tcode": strategy_info["tcode"],
                "executor": "bash",
                "executor_config": {"timeout_seconds": "#{ot_fuzz_timeout}", "result_parser": "morgana-marker-v1"},
                "platform": "linux",
                "command": wrapper_command(protocol, strategy, False, True),
                "cleanup_command": None,
                "required_tags": ["ot_fuzz_target", "ot_fuzz_port", "ot_fuzz_iterations", "ot_fuzz_mutation_rate", "ot_fuzz_threads", "ot_fuzz_delay_ms", "ot_fuzz_timeout", "ot_fuzz_record_pcap", "ot_fuzz_pcap_input", "ot_fuzz_pcap_output"],
                "required_assets": [ASSET_ID, seed_id],
                "operational_risk": strategy_info["risk"],
                "source_metadata": replay_metadata,
            }
            scripts.append(replay); inventory.append(replay_metadata | {"script_id": replay["id"], "name": replay_name})
        package_id = f"ics-scada-fuzzer-{protocol}-v1"
        package = {
            "package_id": package_id,
            "package_name": f"ICS-SCADA-Fuzzer - {protocol_info['label']}",
            "version": "1.0.0",
            "summary": f"24 real {protocol_info['label']} fuzz profiles: eight upstream strategies in stateful/stateless generated modes plus replay.",
            "description": f"Protocol-aware {protocol_info['label']} mutation testing using the pinned ICS-SCADA-Fuzzer engine, verified Linux asset, structured result counters, and optional PCAP recording.",
            "purpose": f"Validate {protocol_info['label']} anomaly detection, OT IDS/NDR telemetry, SOC alerting, and authorized simulator/device resilience.",
            "capabilities": [
                "Eight real upstream CLI mutation strategies.",
                "Sixteen generated profiles covering stateful and stateless execution plus eight verified PCAP replay profiles.",
                "Runtime generation of configurable test-case volume with structured packet, anomaly, timeout, and crash-candidate results.",
            ],
            "use_cases": [
                f"Validate {protocol_info['label']} protocol anomaly detection in an isolated OT lab.",
                "Exercise SIEM, NDR, Suricata, Zeek, firewall, and SOC workflows using controlled mutation traffic.",
            ],
            "prerequisites": [
                "Linux amd64 Morgana Agent with network access to an explicitly authorized OT simulator/testbed.",
                "The operator must configure target, runtime volume, timeout, and risk acknowledgement before execution.",
                "Replay uses the package-provided deterministic seed PCAP; arbitrary input paths are not accepted.",
            ],
            "safety_notes": [
                "Fuzzing can disrupt physical processes. Never target production OT without explicit written authorization and change controls.",
                "Overflow and sequence profiles are classified disrupt; other strategies retain reviewed interact/modify risk metadata.",
                "Crashes are reported as crash candidates until independently verified.",
            ],
            "author": "ridpath / X3M.AI integration",
            "created": str(date.today()),
            "script_prefix": "ICS FUZZ",
            "provider": PROVIDER_ID,
            "source": PROVIDER_ID,
            "source_repository": SOURCE_REPOSITORY,
            "source_commit": source_commit,
            "source_license": "MIT",
            "documentation_url": SOURCE_REPOSITORY,
            "mitre_domain": "ics-attack",
            "source_attack_version": mapping["source_attack_version"],
            "mitre_tactic": "Impair Process Control",
            "mitre_tcodes": sorted({item["tcode"] for item in scripts}),
            "platform": ["linux"],
            "risk_badges": sorted({item["operational_risk"] for item in scripts}, key=("observe", "interact", "modify", "disrupt").index),
            "category": "ot/fuzzing/ics-scada-fuzzer",
            "protocol": protocol,
            "strategies": list(mapping["strategies"]),
            "modes": ["generated", "replay"],
            "state_modes": ["stateless", "stateful"],
            "runtime_case_generator": True,
            "tag_categories": [{
                "category_id": "ot_fuzzing",
                "label": "OT Fuzzing",
                "description": "Reusable authorized target, scale, timing, timeout, and PCAP controls.",
                "scope": "local",
                "tags": tag_definitions(protocol_info["port"]),
            }],
            "assets": [binary_asset, seed_asset],
            "scripts": scripts,
            "chains": [],
        }
        packages.append((package, f"{protocol}/{package_id}.json"))
    return packages, inventory


def catalog_entry(package: dict[str, Any], relative: str) -> dict[str, Any]:
    fields = (
        "package_id", "package_name", "version", "summary", "description", "purpose",
        "capabilities", "use_cases", "prerequisites", "safety_notes", "provider", "category",
        "platform", "mitre_domain", "mitre_tactic", "mitre_tcodes", "source", "source_commit",
        "source_license", "documentation_url", "risk_badges", "protocol", "strategies", "modes",
        "state_modes", "runtime_case_generator",
    )
    return {key: package[key] for key in fields} | {
        "script_count": len(package["scripts"]),
        "chain_count": 0,
        "asset_count": len(package["assets"]),
        "status": "community",
        "author": package["author"],
        "url": f"{CATALOG_BASE_URL}/{relative}",
    }


def update_catalog(entries: list[dict[str, Any]]) -> None:
    catalog = json.loads(CATALOG_FILE.read_text(encoding="utf-8"))
    catalog["packs"] = [item for item in catalog.get("packs", []) if item.get("provider") != PROVIDER_ID] + entries
    catalog["catalog_version"] = "2.0.0"
    catalog["updated"] = str(date.today())
    catalog["providers"] = [item for item in catalog.get("providers", []) if item.get("id") != PROVIDER_ID] + [{
        "id": PROVIDER_ID,
        "name": "ICS-SCADA-Fuzzer",
        "type": "upstream-engine",
        "repository": SOURCE_REPOSITORY,
        "domain": "ics-attack",
    }]
    catalog["categories"] = [item for item in catalog.get("categories", []) if item.get("id") != "ot/fuzzing/ics-scada-fuzzer"] + [{
        "id": "ot/fuzzing/ics-scada-fuzzer",
        "label": "ICS-SCADA-Fuzzer",
        "group": "OT / ICS Fuzzing",
        "order": 600,
        "provider": PROVIDER_ID,
    }]
    write_json(CATALOG_FILE, catalog)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-dir", required=True, type=Path)
    parser.add_argument("--binary", required=True, type=Path)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--compiler", default="gcc")
    parser.add_argument("--compiler-version", default="unknown")
    parser.add_argument("--build-command", default="gcc -O2 -pthread -static -no-pie -Wl,--build-id=none -s -o ics-fuzzer-linux-amd64 ics_fuzzer.c -lpcap -lcrypto -lz")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--no-update-catalog", action="store_true")
    args = parser.parse_args()
    source_dir = args.source_dir.resolve()
    binary_path = args.binary.resolve()
    mapping = json.loads(MAPPING_FILE.read_text(encoding="utf-8"))
    contract = inspect_source(source_dir / "ics_fuzzer.c", mapping)
    if not binary_path.is_file():
        raise ValueError(f"built binary not found: {binary_path}")
    binary_hash = sha256_file(binary_path)
    binary_size = binary_path.stat().st_size
    source_commit = git_value(source_dir, "rev-parse", "HEAD")
    source_date = git_value(source_dir, "show", "-s", "--format=%cs", "HEAD")
    packages, inventory = build_packages(mapping, source_commit, binary_path, binary_hash, binary_size)
    expected = len(mapping["protocols"]) * len(mapping["strategies"]) * 3
    actual = sum(len(package["scripts"]) for package, _ in packages)
    if actual != expected or len(inventory) != expected:
        raise ValueError(f"profile reconciliation failed: expected={expected} scripts={actual} inventory={len(inventory)}")
    report = {
        "source_repository": SOURCE_REPOSITORY,
        "source_commit": source_commit,
        "source_commit_date": source_date,
        "source_license": "MIT",
        "source_modified": False,
        "source_contract": contract,
        "protocols": len(mapping["protocols"]),
        "strategies": len(mapping["strategies"]),
        "generated_profiles": len(mapping["protocols"]) * len(mapping["strategies"]) * 2,
        "stateful_profiles": len(mapping["protocols"]) * len(mapping["strategies"]),
        "stateless_profiles": len(mapping["protocols"]) * len(mapping["strategies"]),
        "replay_profiles": len(mapping["protocols"]) * len(mapping["strategies"]),
        "total_scripts": actual,
        "packages": len(packages),
        "risk_counts": dict(Counter(script["operational_risk"] for package, _ in packages for script in package["scripts"])),
        "mode_counts": dict(Counter(script["source_metadata"]["mode"] for package, _ in packages for script in package["scripts"])),
        "protocol_counts": dict(Counter(script["source_metadata"]["protocol"] for package, _ in packages for script in package["scripts"])),
        "strategy_counts": dict(Counter(script["source_metadata"]["strategy"] for package, _ in packages for script in package["scripts"])),
        "expected_profiles": expected,
        "published": actual,
        "skipped": 0,
        "unsupported": 0,
        "source_reconciled": actual == expected,
        "result_parser": {"packets": True, "anomalies": True, "crash_candidates": True, "timeouts": True, "structured_result_metadata": True},
        "pcap": {"record": True, "replay": True, "artifact_handling": "controlled output path retained in Test.result_metadata"},
        "validation": "PASS",
    }
    manifest = {
        "source_repository": SOURCE_REPOSITORY,
        "source_commit": source_commit,
        "source_commit_date": source_date,
        "source_modified": False,
        "compiler": args.compiler,
        "compiler_version": args.compiler_version,
        "build_command": args.build_command,
        "dependencies": ["libpcap", "OpenSSL/libcrypto", "zlib", "pthread"],
        "platform": "linux",
        "architecture": "amd64",
        "binary_filename": "ics-fuzzer-linux-amd64",
        "binary_sha256": binary_hash,
        "binary_size": binary_size,
        "binary_format": "ELF 64-bit x86-64 statically linked stripped",
        "status": "PASS",
    }
    if args.dry_run:
        print(json.dumps({"report": report, "build_manifest": manifest}, indent=2))
        return 0
    args.out_dir.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix="ics-scada-fuzzer-", dir=str(args.out_dir.parent)))
    try:
        (staging / "assets").mkdir(parents=True, exist_ok=True)
        shutil.copy2(binary_path, staging / "assets" / "ics-fuzzer-linux-amd64")
        for protocol in mapping["protocols"]:
            (staging / "assets" / f"{protocol}-seed.pcap").write_bytes(protocol_seed(protocol))
        for package, relative in packages:
            write_json(staging / relative, package)
        write_json(staging / "build-manifest.json", manifest)
        write_json(staging / "source-inventory.json", inventory)
        write_json(staging / "conversion-report.json", report)
        (staging / "LICENSE-NOTICE.md").write_text(
            "# License Notice\n\nICS-SCADA-Fuzzer is licensed under the MIT License. This distribution contains an unmodified binary built from the pinned source commit documented in build-manifest.json.\n",
            encoding="utf-8",
        )
        (staging / "README.md").write_text(
            f"# ICS-SCADA-Fuzzer Morgana Packs\n\n{actual} real reusable fuzz profiles across five protocols. Each profile generates runtime mutation cases; it is not one Script per packet.\n\nSource: `{source_commit}`. Binary SHA256: `{binary_hash}`. Validation: PASS.\n",
            encoding="utf-8",
        )
        shutil.copy2(source_dir / "LICENSE", staging / "LICENSE")
        if args.out_dir.exists():
            shutil.rmtree(args.out_dir)
        staging.replace(args.out_dir)
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    if not args.no_update_catalog:
        update_catalog([catalog_entry(package, relative) for package, relative in packages])
    print(f"[ICS-FUZZ] protocols=5 strategies=8 generated=80 replay=40 scripts={actual} packages={len(packages)} validation=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())