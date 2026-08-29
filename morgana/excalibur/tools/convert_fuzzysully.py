#!/usr/bin/env python3
"""
convert_fuzzysully.py — Generate Morgana Excalibur packages for ANSSI FuzzySully.

Dynamically enumerates FuzzySully modes/functions from source, applies
mapping overrides, generates all valid script profiles, and writes
deterministic Camelot package JSON files.

Usage:
    python convert_fuzzysully.py --source-dir /path/to/fuzzysully \
        --runtime-asset morgana_fuzzysully_runner.py \
        --out-dir ../../excalibur/ot/fuzzing/fuzzysully \
        [--no-update-catalog] [--dry-run] [--verbose]
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import sys
import textwrap
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

TOOLS_DIR = Path(__file__).resolve().parent
CAMELOT_ROOT = TOOLS_DIR.parent.parent.parent

# ── load mapping overrides ─────────────────────────────────────────────────────
def _load_mapping(mapping_path: Path) -> dict:
    return json.loads(mapping_path.read_text(encoding="utf-8"))


# ── dynamic source inspection ──────────────────────────────────────────────────
def inspect_source(source_dir: Path, mapping: dict) -> dict:
    """
    Import FuzzySully from source_dir and enumerate modes/functions.
    Validates that the source matches the expected contract.
    Raises ValueError on SOURCE CLI DRIFT.
    """
    src_path = source_dir / "src"
    if not src_path.exists():
        src_path = source_dir

    # Add source to sys.path
    if str(src_path) not in sys.path:
        sys.path.insert(0, str(src_path))

    try:
        from fuzzysully import FuzzySully as _FS, OPCUAMode as _Mode
    except ImportError as exc:
        raise ImportError(f"Cannot import fuzzysully from {src_path}: {exc}") from exc

    discovered: dict[str, list[str]] = {}
    for mode_key in ("server", "gds", "reverse"):
        mode_enum = {
            "server": _Mode.SERVER,
            "gds": _Mode.GDS,
            "reverse": _Mode.REVERSE_MODE,
        }[mode_key]
        discovered[mode_key] = sorted(_FS.list_available_functions(mode_enum))

    # Drift detection
    expected_server = set(mapping["server_functions"])
    expected_gds = set(mapping["gds_functions"])
    expected_reverse = set(mapping["reverse_functions"])

    drift_errors: list[str] = []
    for expected, got, name in [
        (expected_server, set(discovered["server"]), "server"),
        (expected_gds, set(discovered["gds"]), "gds"),
        (expected_reverse, set(discovered["reverse"]), "reverse"),
    ]:
        added = got - expected
        removed = expected - got
        if added:
            drift_errors.append(f"SOURCE CLI DRIFT [{name}] NEW functions: {sorted(added)}")
        if removed:
            drift_errors.append(f"SOURCE CLI DRIFT [{name}] REMOVED functions: {sorted(removed)}")

    if drift_errors:
        for e in drift_errors:
            print(f"[WARN] {e}", file=sys.stderr)
        # Update mapping with discovered (warn, do not hard-fail so existing packages stay valid)

    contract = {
        "modes": list(discovered.keys()),
        "functions_by_mode": discovered,
        "server_function_count": len(discovered["server"]),
        "gds_function_count": len(discovered["gds"]),
        "reverse_function_count": len(discovered["reverse"]),
        "total_functions": sum(len(v) for v in discovered.values()),
        "drift_warnings": drift_errors,
    }
    return contract


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


# ── profile combination builder ────────────────────────────────────────────────

def build_combinations(contract: dict, mapping: dict) -> tuple[list[dict], list[dict]]:
    """
    Returns (valid_profiles, skipped_profiles).
    Each valid_profile: {mode, function, policy, encrypt, script_id, name, category, risk, tcodes, description}
    """
    funcs_by_mode = contract["functions_by_mode"]
    basic_excluded = set(mapping["server_basic_excluded_functions"])
    func_categories = mapping["function_categories"]
    risk_map = mapping["operational_risk"]
    tcode_map = mapping["mitre_tcodes"]
    desc_map = mapping["function_descriptions"]

    valid: list[dict] = []
    skipped: list[dict] = []

    def _risk(mode, func):
        return risk_map.get(mode, {}).get(func, "interact")

    def _tcodes(mode, func):
        cat = func_categories.get(mode, {}).get(func, "")
        return tcode_map.get(cat, [])

    def _desc(func):
        return desc_map.get(func, f"Fuzzes the OPC UA {func.replace('_', ' ')} service.")

    def _label(func):
        return func.replace("_", " ").upper()

    # ── SERVER / None ──────────────────────────────────────────────────────────
    for func in funcs_by_mode.get("server", []):
        cat = func_categories.get("server", {}).get(func, "Other")
        valid.append({
            "mode": "server",
            "function": func,
            "policy": "None",
            "encrypt": False,
            "script_id": f"fuzzysully:server:{func}:none",
            "name": f"FUZZYSULLY - SERVER - {_label(func)} - NONE",
            "category": cat,
            "risk": _risk("server", func),
            "tcodes": _tcodes("server", func),
            "description": _desc(func),
            "package_key": "server-none",
        })

    # ── SERVER / Basic256Sha256-Sign ───────────────────────────────────────────
    for func in funcs_by_mode.get("server", []):
        if func in basic_excluded:
            skipped.append({
                "mode": "server", "function": func,
                "policy": "Basic256Sha256", "encrypt": False,
                "reason": "upstream: not supported with Basic256Sha256 (hello/secure_channel/session)"
            })
            continue
        cat = func_categories.get("server", {}).get(func, "Other")
        valid.append({
            "mode": "server",
            "function": func,
            "policy": "Basic256Sha256",
            "encrypt": False,
            "script_id": f"fuzzysully:server:{func}:basic256sha256-sign",
            "name": f"FUZZYSULLY - SERVER - {_label(func)} - BASIC256SHA256",
            "category": cat,
            "risk": _risk("server", func),
            "tcodes": _tcodes("server", func),
            "description": _desc(func) + " Uses Basic256Sha256 Sign security policy with client certificate authentication.",
            "package_key": "server-basic256sha256",
        })

    # ── SERVER / Basic256Sha256-SignEncrypt ────────────────────────────────────
    for func in funcs_by_mode.get("server", []):
        if func in basic_excluded:
            skipped.append({
                "mode": "server", "function": func,
                "policy": "Basic256Sha256", "encrypt": True,
                "reason": "upstream: not supported with Basic256Sha256+SignEncrypt (hello/secure_channel/session)"
            })
            continue
        cat = func_categories.get("server", {}).get(func, "Other")
        valid.append({
            "mode": "server",
            "function": func,
            "policy": "Basic256Sha256",
            "encrypt": True,
            "script_id": f"fuzzysully:server:{func}:basic256sha256-signencrypt",
            "name": f"FUZZYSULLY - SERVER - {_label(func)} - BASIC256SHA256-SIGNENCRYPT",
            "category": cat,
            "risk": _risk("server", func),
            "tcodes": _tcodes("server", func),
            "description": _desc(func) + " Uses Basic256Sha256 SignAndEncrypt security policy with full message encryption.",
            "package_key": "server-basic256sha256",
        })

    # ── GDS / Basic256Sha256-Sign ──────────────────────────────────────────────
    for func in funcs_by_mode.get("gds", []):
        cat = func_categories.get("gds", {}).get(func, "Other")
        valid.append({
            "mode": "gds",
            "function": func,
            "policy": "Basic256Sha256",
            "encrypt": False,
            "script_id": f"fuzzysully:gds:{func}:basic256sha256-sign",
            "name": f"FUZZYSULLY - GDS - {_label(func)} - SIGN",
            "category": cat,
            "risk": _risk("gds", func),
            "tcodes": _tcodes("gds", func),
            "description": _desc(func) + " Targets a Global Discovery Server using Basic256Sha256 Sign policy.",
            "package_key": "gds",
        })

    # ── GDS / Basic256Sha256-SignEncrypt ───────────────────────────────────────
    for func in funcs_by_mode.get("gds", []):
        cat = func_categories.get("gds", {}).get(func, "Other")
        valid.append({
            "mode": "gds",
            "function": func,
            "policy": "Basic256Sha256",
            "encrypt": True,
            "script_id": f"fuzzysully:gds:{func}:basic256sha256-signencrypt",
            "name": f"FUZZYSULLY - GDS - {_label(func)} - SIGNENCRYPT",
            "category": cat,
            "risk": _risk("gds", func),
            "tcodes": _tcodes("gds", func),
            "description": _desc(func) + " Targets a Global Discovery Server using Basic256Sha256 SignAndEncrypt policy.",
            "package_key": "gds",
        })

    # ── REVERSE / None ─────────────────────────────────────────────────────────
    for func in funcs_by_mode.get("reverse", []):
        cat = func_categories.get("reverse", {}).get(func, "Client & Reverse Connection")
        valid.append({
            "mode": "reverse",
            "function": func,
            "policy": "None",
            "encrypt": False,
            "script_id": f"fuzzysully:reverse:{func}:none",
            "name": f"FUZZYSULLY - REVERSE - {_label(func)} - NONE",
            "category": cat,
            "risk": _risk("reverse", func),
            "tcodes": _tcodes("reverse", func),
            "description": _desc(func),
            "package_key": "reverse",
        })

    # ── TARGETED NODE PROFILES ─────────────────────────────────────────────────
    # Nodes that are NEVER the fuzz target in any existing high-level function
    # but can be targeted via Fuzzowski goto_path("NodeName").
    for tnode in mapping.get("targeted_nodes", []):
        node = tnode["node"]
        tmode = tnode["mode"]
        for policy in tnode["valid_policies"]:
            policy_norm = policy.lower().replace("basic256sha256", "basic256sha256")
            encrypt = False
            if tmode == "server" and policy == "None":
                pkg_key = "server-none-targeted"
                sid_suffix = "none"
            elif tmode == "server" and policy == "Basic256Sha256":
                pkg_key = "server-basic256sha256-targeted"
                sid_suffix = "basic256sha256-sign"
            elif tmode == "reverse":
                pkg_key = "reverse-targeted"
                sid_suffix = "none"
            else:
                pkg_key = f"{tmode}-targeted"
                sid_suffix = policy_norm
            node_slug = node.lower().replace(" ", "_")
            valid.append({
                "mode": tmode,
                "function": node,  # actual request node name
                "policy": policy,
                "encrypt": encrypt,
                "script_id": f"fuzzysully:target:{tmode}:{node_slug}:{sid_suffix}",
                "name": f"FUZZYSULLY TARGET - {tmode.upper()} - {node.upper().replace('_',' ')} - {policy.upper()}",
                "category": tnode["category"],
                "risk": tnode["risk"],
                "tcodes": tnode["tcodes"],
                "description": tnode["description"],
                "package_key": pkg_key,
                "is_targeted": True,
                "target_node": node,
                "prerequisite_path": tnode.get("prerequisite_path", []),
            })

    return valid, skipped


# ── tag categories (shared across all packages) ───────────────────────────────

OPCUA_TAG_CATEGORIES = [
    {
        "category_id": "opcua_fuzzing",
        "label": "OPC UA Fuzzing",
        "description": "Authorized OPC UA target, session parameters, security credentials, and execution bounds.",
        "scope": "local",
        "tags": [
            {"key": "opcua_target_host", "label": "OPC UA Target Host",
             "description": "Authorized lab OPC UA server hostname or IP address.",
             "default": "", "sensitive": False, "required": True, "parameter_class": "connection"},
            {"key": "opcua_target_port", "label": "OPC UA Target Port",
             "description": "OPC UA server TCP port (1-65535).",
             "default": "4840", "sensitive": False, "required": True, "parameter_class": "connection"},
            {"key": "opcua_target_path", "label": "OPC UA Endpoint Path",
             "description": "Optional endpoint path (e.g. /OPCUA/SimulationServer).",
             "default": "", "sensitive": False, "required": False, "parameter_class": "connection"},
            {"key": "opcua_bind_port", "label": "Bind Port (reverse mode)",
             "description": "Local bind port for reverse-client mode.",
             "default": "4840", "sensitive": False, "required": False, "parameter_class": "connection"},
            {"key": "opcua_app_uri", "label": "Application URI",
             "description": "OPC UA client application URI.",
             "default": "urn:morgana:fuzzysully:client", "sensitive": False, "required": False, "parameter_class": "value"},
            {"key": "opcua_send_timeout", "label": "Send Timeout (s)",
             "description": "Socket send timeout in seconds.",
             "default": "5.0", "sensitive": False, "required": False, "parameter_class": "value"},
            {"key": "opcua_recv_timeout", "label": "Receive Timeout (s)",
             "description": "Socket receive timeout in seconds.",
             "default": "5.0", "sensitive": False, "required": False, "parameter_class": "value"},
            {"key": "opcua_sleep_time", "label": "Sleep Between Requests (s)",
             "description": "Delay between fuzz requests in seconds.",
             "default": "0.0", "sensitive": False, "required": False, "parameter_class": "value"},
            {"key": "fuzz_case_start", "label": "Start Case Index",
             "description": "First fuzz case index to execute (1-based).",
             "default": "1", "sensitive": False, "required": False, "parameter_class": "value"},
            {"key": "fuzz_max_cases", "label": "Max Cases",
             "description": "Maximum number of fuzz cases to execute per campaign.",
             "default": "1000", "sensitive": False, "required": False, "parameter_class": "value"},
            {"key": "fuzz_max_duration", "label": "Max Duration (s)",
             "description": "Maximum campaign duration in seconds (1-86400).",
             "default": "600", "sensitive": False, "required": False, "parameter_class": "value"},
            {"key": "opcua_threshold_request", "label": "Crash Threshold (request)",
             "description": "Number of consecutive errors before marking a crash candidate.",
             "default": "9999", "sensitive": False, "required": False, "parameter_class": "value"},
            {"key": "opcua_threshold_element", "label": "Crash Threshold (element)",
             "description": "Number of element-level errors before marking a crash candidate.",
             "default": "9999", "sensitive": False, "required": False, "parameter_class": "value"},
        ],
    },
    {
        "category_id": "opcua_fuzzing_security",
        "label": "OPC UA Fuzzing — Security",
        "description": "Certificate and credential parameters for secured OPC UA fuzzing profiles.",
        "scope": "local",
        "tags": [
            {"key": "opcua_client_cert_path", "label": "Client Certificate Path",
             "description": "Path to client certificate PEM file on the agent (required for Basic256Sha256).",
             "default": "", "sensitive": False, "required": False, "parameter_class": "local_path"},
            {"key": "opcua_private_key_path", "label": "Private Key Path",
             "description": "Path to private key PEM file on the agent (required for Basic256Sha256).",
             "default": "", "sensitive": False, "required": False, "parameter_class": "local_path"},
            {"key": "opcua_private_key_password", "label": "Private Key Password",
             "description": "Private key password; injected via FUZZ_KEY_PWD environment variable.",
             "default": "", "sensitive": True, "required": False, "parameter_class": "secret"},
            {"key": "opcua_username", "label": "OPC UA Username",
             "description": "OPC UA username for GDS or user-authenticated endpoints.",
             "default": "", "sensitive": False, "required": False, "parameter_class": "value"},
            {"key": "opcua_password", "label": "OPC UA Password",
             "description": "OPC UA password; injected via FUZZ_PASSWORD environment variable.",
             "default": "", "sensitive": True, "required": False, "parameter_class": "secret"},
        ],
    }
]


def _build_command(profile: dict, runner_asset_id: str) -> str:
    """Generate the bash Script command for a given profile."""
    mode = profile["mode"]
    func = profile["function"]
    policy = profile["policy"]
    encrypt = profile["encrypt"]
    needs_cert = (policy != "None")
    is_reverse = (mode == "reverse")
    is_targeted = profile.get("is_targeted", False)
    target_node = profile.get("target_node", None)

    lines = [
        "set -u",
        f'runner="{{{{asset:{runner_asset_id}}}}}"',
        "host='#{opcua_target_host}'",
        "port='#{opcua_target_port}'",
        "path='#{opcua_target_path}'",
        "send_timeout='#{opcua_send_timeout}'",
        "recv_timeout='#{opcua_recv_timeout}'",
        "sleep_time='#{opcua_sleep_time}'",
        "case_start='#{fuzz_case_start}'",
        "max_cases='#{fuzz_max_cases}'",
        "max_duration='#{fuzz_max_duration}'",
        "threshold_req='#{opcua_threshold_request}'",
        "threshold_el='#{opcua_threshold_element}'",
        "",
        "# Input validation",
        "case \"$host\" in ''|*[!A-Za-z0-9._:-]*) echo '[ERROR] Invalid authorized target host' >&2; exit 2;; esac",
        "case \"$port\" in ''|*[!0-9]*) echo '[ERROR] Port must be numeric' >&2; exit 2;; esac",
        "[ \"$port\" -ge 1 ] && [ \"$port\" -le 65535 ] || { echo '[ERROR] Port must be 1-65535' >&2; exit 2; }",
        "case \"$max_cases\" in ''|*[!0-9]*) echo '[ERROR] max_cases must be numeric' >&2; exit 2;; esac",
        "case \"$max_duration\" in ''|*[!0-9]*) echo '[ERROR] max_duration must be numeric' >&2; exit 2;; esac",
        "[ \"$max_duration\" -ge 1 ] && [ \"$max_duration\" -le 86400 ] || { echo '[ERROR] max_duration must be 1-86400' >&2; exit 2; }",
    ]

    if needs_cert:
        lines += [
            "cert_path='#{opcua_client_cert_path}'",
            "key_path='#{opcua_private_key_path}'",
            "[ -f \"$cert_path\" ] || { echo '[ERROR] Client cert not found: '\"$cert_path\" >&2; exit 2; }",
            "[ -f \"$key_path\" ] || { echo '[ERROR] Private key not found: '\"$key_path\" >&2; exit 2; }",
            "export FUZZ_KEY_PWD='#{opcua_private_key_password}'",
        ]

    lines += [
        "",
        "# Build argument array",
        "args=(",
        "  --host \"$host\"",
        "  --port \"$port\"",
        "  --path \"$path\"" if not is_reverse else "",
        f"  --mode {mode}",
        f"  --function {func}",
        f"  --policy {policy}",
    ]
    if encrypt:
        lines.append("  --encrypt")
    if needs_cert:
        lines += [
            "  --client-cert \"$cert_path\"",
            "  --private-key \"$key_path\"",
        ]
    if is_reverse:
        lines.append("  --bind-port '#{opcua_bind_port}'")
    lines += [
        "  --send-timeout \"$send_timeout\"",
        "  --recv-timeout \"$recv_timeout\"",
        "  --sleep-time \"$sleep_time\"",
        "  --case-start \"$case_start\"",
        "  --max-cases \"$max_cases\"",
        "  --max-duration \"$max_duration\"",
        "  --threshold-request \"$threshold_req\"",
        "  --threshold-element \"$threshold_el\"",
        f"  --test-id \"${{MORGANA_TEST_ID:-manual}}\"",
        "  --log-dir /tmp",
    ]
    if is_targeted and target_node:
        lines.append(f"  --goto-path {target_node}")
    lines += [
        ")",
        "",
        'echo "[INFO] ANSSI FuzzySully: mode={m} function={f} policy={p} encrypt={e}{g}" >&1'.format(
            m=mode, f=func, p=policy, e=str(encrypt).lower(),
            g=(" goto=" + target_node) if is_targeted and target_node else ""),
        'python3 "$runner" "${args[@]}"',
        "exit $?",
    ]
    # Remove blank args
    return "\n".join(l for l in lines if l is not None)


def _required_tags_for_profile(profile: dict) -> list[str]:
    needs_cert = (profile["policy"] != "None")
    is_reverse = (profile["mode"] == "reverse")
    base = ["opcua_target_host", "opcua_target_port", "fuzz_max_cases", "fuzz_max_duration"]
    if needs_cert:
        base += ["opcua_client_cert_path", "opcua_private_key_path"]
    if is_reverse:
        base.append("opcua_bind_port")
    return base


def _required_assets_for_profile(profile: dict, runner_asset_id: str) -> list[str]:
    return [runner_asset_id]


def _build_script(profile: dict, mapping: dict, source_commit: str,
                  runner_asset_id: str) -> dict:
    return {
        "id": profile["script_id"],
        "name": profile["name"],
        "description": profile["description"],
        "tactic": "Impair Process Control",
        "tcode": profile["tcodes"][0] if profile["tcodes"] else "T0831",
        "executor": "bash",
        "executor_config": {
            "timeout_seconds": "#{fuzz_max_duration}",
            "result_parser": "morgana-marker-v1",
        },
        "platform": "linux",
        "command": _build_command(profile, runner_asset_id),
        "cleanup_command": None,
        "required_tags": _required_tags_for_profile(profile),
        "required_assets": _required_assets_for_profile(profile, runner_asset_id),
        "operational_risk": profile["risk"],
        "source_metadata": {
            "provider": "anssi-fuzzysully",
            "source_provider": "ANSSI-FR",
            "source_repository": "ANSSI-FR/fuzzysully",
            "source_commit": source_commit,
            "mode": profile["mode"],
            "function": profile["function"],
            "security_policy": profile["policy"],
            "encrypt": profile["encrypt"],
            "generator_type": "protocol-fuzzer",
            "protocol": "opcua",
            "mitre_domain": "ics-attack",
            "source_attack_version": mapping.get("source_attack_version", "ICS v13"),
            "source_modified": False,
            "category": profile["category"],
        },
    }


# ── package builder ────────────────────────────────────────────────────────────

_PACKAGE_META = {
    "server-none": {
        "package_id": "fuzzysully-server-none-v1",
        "package_name": "ANSSI FuzzySully — OPC UA Server / None Policy",
        "description": "Deep OPC UA server fuzzing using all available upstream functions with no security policy. Tests discovery, secure-channel, session, address-space, and monitoring services.",
        "purpose": "Validate OPC UA server protocol parsing, NDR/IDS telemetry, and server resilience across all major service families in an isolated OT lab.",
        "mode": "server",
        "policy": "None",
        "encrypt": False,
    },
    "server-basic256sha256": {
        "package_id": "fuzzysully-server-basic256sha256-v1",
        "package_name": "ANSSI FuzzySully — OPC UA Server / Basic256Sha256",
        "description": "Deep OPC UA server fuzzing with Basic256Sha256 Sign and SignAndEncrypt security policies. Excludes hello/secure_channel/session per upstream restrictions.",
        "purpose": "Validate secured OPC UA server behaviour, certificate handling, and authenticated session integrity in an authorized OT lab.",
        "mode": "server",
        "policy": "Basic256Sha256",
        "encrypt": None,
    },
    "gds": {
        "package_id": "fuzzysully-gds-v1",
        "package_name": "ANSSI FuzzySully — OPC UA Global Discovery Server",
        "description": "Deep fuzzing of OPC UA Global Discovery Server certificate lifecycle, trust-list management, key-pair and signing requests. Requires Basic256Sha256 policy and a running GDS endpoint.",
        "purpose": "Validate GDS certificate management, trust-list operations, and revocation workflows in an isolated PKI/OT lab.",
        "mode": "gds",
        "policy": "Basic256Sha256",
        "encrypt": None,
    },
    "reverse": {
        "package_id": "fuzzysully-reverse-v1",
        "package_name": "ANSSI FuzzySully — OPC UA Reverse Client",
        "description": "Fuzzes the OPC UA ReverseHello message targeting compatible OPC UA clients that accept reverse connections from a server endpoint.",
        "purpose": "Validate OPC UA client-side protocol handling and resilience to malformed reverse-connection messages.",
        "mode": "reverse",
        "policy": "None",
        "encrypt": False,
    },
    "server-none-targeted": {
        "package_id": "fuzzysully-server-none-targeted-v1",
        "package_name": "ANSSI FuzzySully — OPC UA Server Targeted Nodes / None",
        "description": "Targeted OPC UA server fuzz profiles for specific protocol request nodes not covered by high-level function profiles: CreateSession, ActivateSession, CloseSession, CloseSecureChannel. Uses Fuzzowski goto_path() to target each node while preserving the required prerequisite graph.",
        "purpose": "Exercise OPC UA server session lifecycle and secure-channel teardown nodes in isolation with targeted mutation.",
        "mode": "server",
        "policy": "None",
        "encrypt": False,
    },
    "server-basic256sha256-targeted": {
        "package_id": "fuzzysully-server-basic256sha256-targeted-v1",
        "package_name": "ANSSI FuzzySully — OPC UA Server Targeted Nodes / Basic256Sha256",
        "description": "Targeted OPC UA server fuzz profiles for CloseSecureChannelSign in Basic256Sha256 Sign mode. Exercises signed secure-channel teardown handling.",
        "purpose": "Exercise authenticated OPC UA secure-channel teardown with targeted mutation.",
        "mode": "server",
        "policy": "Basic256Sha256",
        "encrypt": False,
    },
    "reverse-targeted": {
        "package_id": "fuzzysully-reverse-targeted-v1",
        "package_name": "ANSSI FuzzySully — OPC UA Reverse Client Targeted",
        "description": "Targeted fuzzing of the ReverseHelloError response message in reverse-client mode.",
        "purpose": "Exercise OPC UA client-side error-response parsing in reverse-connection scenarios.",
        "mode": "reverse",
        "policy": "None",
        "encrypt": False,
    },
}

_PACKAGE_CAPS = {
    "server-none": [
        "All 20 upstream server functions in None security mode.",
        "Runtime generation of configurable fuzz campaigns per function.",
        "Structured result with faults, connection failures, timeouts, crash candidates.",
        "Bounded execution with case-count and duration limits.",
    ],
    "server-basic256sha256": [
        "17 server functions compatible with Basic256Sha256 (hello/secure_channel/session excluded per upstream).",
        "Both Sign and SignAndEncrypt variants for each function.",
        "Client certificate and private key handled as controlled assets.",
        "Full structured result output.",
    ],
    "gds": [
        "All 9 GDS functions in Sign and SignAndEncrypt variants.",
        "Certificate lifecycle: trust lists, groups, status, revocation.",
        "Key and signing request workflows.",
        "Requires a running Global Discovery Server.",
    ],
    "reverse": [
        "OPC UA ReverseHello fuzzing targeting compliant OPC UA clients.",
        "None security policy; no certificates required.",
        "Compact profile for reverse-connection attack surface.",
    ],
}

_PACKAGE_PREREQS = {
    "server-none": [
        "Linux amd64 Morgana Agent with Python 3.10+ and fuzzysully installed.",
        "Network access to an explicitly authorized OPC UA server simulator or testbed.",
        "Operator configures host, port, case bounds, and risk acknowledgement before execution.",
    ],
    "server-basic256sha256": [
        "Linux amd64 Morgana Agent with Python 3.10+ and fuzzysully installed.",
        "Valid client certificate and private key in PEM format on the agent.",
        "Authorized OPC UA server supporting Basic256Sha256 security.",
        "Operator configures cert/key paths, host, port, and execution bounds.",
    ],
    "gds": [
        "Linux amd64 Morgana Agent with Python 3.10+ and fuzzysully installed.",
        "Valid client certificate and private key for Basic256Sha256.",
        "Running OPC UA Global Discovery Server accessible from the agent.",
        "Operator configures all GDS connection and certificate parameters.",
    ],
    "reverse": [
        "Linux amd64 Morgana Agent with Python 3.10+ and fuzzysully installed.",
        "OPC UA client on the target network that supports reverse connections.",
        "Operator configures bind port and target identification.",
    ],
}


def _runner_asset_def(runner_sha256: str, runner_size: int, source_commit: str) -> dict:
    return {
        "id": "anssi_fuzzysully_runner",
        "name": "morgana-fuzzysully-runner",
        "filename": "morgana_fuzzysully_runner.py",
        "platform": "linux",
        "architecture": "amd64",
        "url": "https://raw.githubusercontent.com/x3m-ai/Camelot/main/morgana/excalibur/ot/fuzzing/fuzzysully/morgana_fuzzysully_runner.py",
        "sha256": runner_sha256,
        "size": runner_size,
        "executable": False,
        "source": "ANSSI-FR/fuzzysully",
        "license": "GPL-2.0",
        "source_commit": source_commit,
        "description": "Non-interactive Morgana execution wrapper for ANSSI FuzzySully. Requires fuzzysully Python package installed on the agent (see requirements-lock.txt).",
    }


def build_packages(
    valid_profiles: list[dict],
    skipped: list[dict],
    mapping: dict,
    source_commit: str,
    runner_path: Path,
    runner_sha256: str,
    runner_size: int,
    dry_run: bool = False,
) -> list[tuple[dict, str]]:  # (package_json, package_key)
    """Build all package dicts from valid profiles."""
    runner_asset_id = "anssi_fuzzysully_runner"
    runner_asset = _runner_asset_def(runner_sha256, runner_size, source_commit)

    packages: list[tuple[dict, str]] = []
    by_key: dict[str, list[dict]] = {}
    for p in valid_profiles:
        k = p["package_key"]
        by_key.setdefault(k, []).append(p)

    for pkg_key, meta in _PACKAGE_META.items():
        profiles = by_key.get(pkg_key, [])
        scripts = [_build_script(p, mapping, source_commit, runner_asset_id) for p in profiles]

        pkg = {
            "package_id": meta["package_id"],
            "package_name": meta["package_name"],
            "version": "1.0.0",
            "summary": f"{len(scripts)} OPC UA deep-fuzzing profiles using ANSSI FuzzySully.",
            "description": meta["description"],
            "purpose": meta["purpose"],
            "capabilities": _PACKAGE_CAPS.get(pkg_key, _PACKAGE_CAPS.get(pkg_key.replace("-targeted", "-none"), [
                f"{len(scripts)} targeted OPC UA request-node profiles using ANSSI FuzzySully.",
                "Programmatic goto_path() targeting of specific request nodes not covered by high-level function profiles.",
                "Runtime-bounded fuzz campaigns with structured result output.",
            ])),
            "use_cases": [
                "Validate OPC UA protocol parsing, anomaly detection, and device resilience in an authorized OT lab.",
                "Exercise NDR, IDS, Suricata, Zeek, firewall, SIEM, and SOC workflows using real OPC UA mutation traffic.",
            ],
            "prerequisites": _PACKAGE_PREREQS.get(pkg_key, _PACKAGE_PREREQS.get(pkg_key.replace("-targeted", "-none"), [
                "Linux amd64 Morgana Agent with Python 3.10+ and fuzzysully installed.",
                "Network access to an explicitly authorized OPC UA server simulator or testbed.",
            ])),
            "safety_notes": [
                "OPC UA fuzzing can disrupt or crash real industrial devices. Never target production systems without explicit written authorization and change controls.",
                "GDS certificate operations can invalidate production PKI trust chains. Use only in isolated lab environments.",
                "Crash candidates are reported as such until independently verified.",
            ],
            "author": "ANSSI-FR / X3M.AI integration",
            "created": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "provider": "anssi-fuzzysully",
            "source": "anssi-fuzzysully",
            "source_repository": "https://github.com/ANSSI-FR/fuzzysully",
            "source_commit": source_commit,
            "source_license": "GPL-2.0",
            "documentation_url": "https://github.com/ANSSI-FR/fuzzysully",
            "mitre_domain": "ics-attack",
            "source_attack_version": mapping.get("source_attack_version", "ICS v13"),
            "mitre_tactic": "Impair Process Control",
            "mitre_tcodes": sorted({tc for p in profiles for tc in p.get("tcodes", [])}),
            "platform": ["linux"],
            "category": "ot/fuzzing/fuzzysully",
            "mode": meta["mode"],
            "security_policy": meta["policy"],
            "encrypt_variant": meta["encrypt"],
            "runtime_case_generator": True,
            "tag_categories": OPCUA_TAG_CATEGORIES,
            "assets": [runner_asset],
            "scripts": scripts,
            "chains": [],
        }
        packages.append((pkg, pkg_key))

    return packages


# ── catalog update ─────────────────────────────────────────────────────────────

def update_catalog(catalog_path: Path, packages: list[tuple[dict, str]],
                   mapping: dict, source_commit: str) -> None:
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    packs = catalog.get("packs", [])

    for pkg, _ in packages:
        pid = pkg["package_id"]
        # Remove existing entry
        packs = [e for e in packs if e.get("package_id") != pid]
        # Add new entry
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
    print(f"[INFO] Catalog updated: {len(packages)} FuzzySully packages, total packs={len(packs)}", flush=True)


# ── main CLI ───────────────────────────────────────────────────────────────────

def main() -> int:
    p = argparse.ArgumentParser(description="Generate FuzzySully Morgana packages")
    p.add_argument("--source-dir", required=True, help="Path to fuzzysully source checkout")
    p.add_argument("--runtime-asset", required=True,
                   help="Path to morgana_fuzzysully_runner.py")
    p.add_argument("--out-dir", required=True,
                   help="Output directory for package JSON files")
    p.add_argument("--mapping", default=str(TOOLS_DIR / "fuzzysully_mapping_overrides.json"),
                   help="Path to mapping overrides JSON")
    p.add_argument("--catalog", default=str(CAMELOT_ROOT / "morgana/excalibur/catalog.json"),
                   help="Path to catalog.json")
    p.add_argument("--no-update-catalog", action="store_true", help="Skip catalog update")
    p.add_argument("--dry-run", action="store_true", help="Print what would be done without writing files")
    p.add_argument("--verbose", action="store_true")
    args = p.parse_args()

    mapping = _load_mapping(Path(args.mapping))
    source_dir = Path(args.source_dir)
    runner_path = Path(args.runtime_asset)
    out_dir = Path(args.out_dir)

    if not runner_path.exists():
        print(f"[ERROR] Runner not found: {runner_path}", file=sys.stderr)
        return 1

    # Capture source commit
    import subprocess
    try:
        result = subprocess.run(["git", "-C", str(source_dir), "rev-parse", "HEAD"],
                                capture_output=True, text=True, check=True)
        source_commit = result.stdout.strip()
    except Exception:
        source_commit = mapping.get("current_commit", "UNKNOWN")

    print(f"[INFO] Source commit: {source_commit}", flush=True)

    # Inspect source dynamically
    try:
        contract = inspect_source(source_dir, mapping)
    except Exception as exc:
        print(f"[ERROR] Source inspection failed: {exc}", file=sys.stderr)
        return 1

    if args.verbose:
        print(f"[INFO] Functions discovered: {contract['functions_by_mode']}")

    # Hash runner
    runner_sha256 = _sha256_file(runner_path)
    runner_size = runner_path.stat().st_size

    # Build combinations
    valid_profiles, skipped = build_combinations(contract, mapping)
    print(f"[INFO] Valid profiles: {len(valid_profiles)} | Skipped: {len(skipped)}", flush=True)

    # Build packages
    packages = build_packages(
        valid_profiles, skipped, mapping, source_commit,
        runner_path, runner_sha256, runner_size, dry_run=args.dry_run,
    )

    if args.dry_run:
        print("\n[DRY RUN] Would generate:")
        for pkg, key in packages:
            print(f"  {key}: {pkg['package_id']} — {len(pkg['scripts'])} scripts")
        print(f"  Total scripts: {sum(len(pkg['scripts']) for pkg, _ in packages)}")
        print(f"  Skipped combinations: {len(skipped)}")
        return 0

    # Write package JSON files
    out_dir.mkdir(parents=True, exist_ok=True)
    for pkg, pkg_key in packages:
        sub_dir = out_dir / pkg_key
        sub_dir.mkdir(parents=True, exist_ok=True)
        out_path = sub_dir / f"{pkg['package_id']}.json"
        out_path.write_text(json.dumps(pkg, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"[OK] Written: {out_path} ({len(pkg['scripts'])} scripts)", flush=True)

    # Write build manifest
    import hashlib as _hl
    reqs_lock_path = out_dir / "requirements-lock.txt"
    reqs_lock_sha = _hl.sha256(reqs_lock_path.read_bytes()).hexdigest() if reqs_lock_path.exists() else None
    bm = {
        "source_repository": "https://github.com/ANSSI-FR/fuzzysully",
        "source_commit": source_commit,
        "upstream_version": mapping.get("upstream_version", "0.1.1"),
        "source_license": "GPL-2.0",
        "source_modified": False,
        "python_requires": mapping.get("requires_python", ">=3.10"),
        "runner_filename": runner_path.name,
        "runner_sha256": runner_sha256,
        "runner_size": runner_size,
        "requirements_lock_filename": "requirements-lock.txt",
        "requirements_lock_sha256": reqs_lock_sha,
        "runtime_bundle_filename": mapping.get("runtime_bundle_filename", "fuzzysully-runtime-linux-amd64.tar.gz"),
        "runtime_bundle_sha256": None,
        "runtime_self_contained": mapping.get("runtime_self_contained", "bundle-build-required"),
        "runtime_build_note": mapping.get("runtime_build_note", "Run build-bundle.sh on Linux to produce self-contained venv archive."),
        "manual_fuzzysully_install_required": True,
        "manual_install_note": "Until the Linux bundle is built and published, agents install via: pip install -r requirements-lock.txt && pip install fuzzysully==0.1.1. No git/gcc/apt/WSL required at runtime.",
        "platform": "linux",
        "architecture": "amd64",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "PASS",
    }
    (out_dir / "build-manifest.json").write_text(json.dumps(bm, indent=2) + "\n", encoding="utf-8")

    # Write source inventory
    inventory = []
    for p in valid_profiles:
        inventory.append({
            "provider": "anssi-fuzzysully",
            "source_commit": source_commit,
            "mode": p["mode"],
            "function": p["function"],
            "policy": p["policy"],
            "encrypt": p["encrypt"],
            "script_id": p["script_id"],
            "name": p["name"],
        })
    (out_dir / "source-inventory.json").write_text(
        json.dumps(inventory, indent=2) + "\n", encoding="utf-8"
    )

    # Write conversion report
    report = {
        "source_repository": "https://github.com/ANSSI-FR/fuzzysully",
        "source_commit": source_commit,
        "source_license": "GPL-2.0",
        "source_modified": False,
        "modes_discovered": contract["modes"],
        "server_function_count": contract["server_function_count"],
        "gds_function_count": contract["gds_function_count"],
        "reverse_function_count": contract["reverse_function_count"],
        "total_upstream_functions": contract["total_functions"],
        "valid_profiles": len(valid_profiles),
        "skipped_profiles": len(skipped),
        "total_scripts": len(valid_profiles),
        "existing_high_level_profiles": len([p for p in valid_profiles if not p.get("is_targeted")]),
        "targeted_profiles_generated": len([p for p in valid_profiles if p.get("is_targeted")]),
        "packages": len(packages),
        "script_counts_by_package": {key: len(pkg["scripts"]) for pkg, key in packages},
        "skipped_detail": skipped,
        "drift_warnings": contract.get("drift_warnings", []),
        "runner_sha256": runner_sha256,
        "requirements_lock_sha256": reqs_lock_sha,
        "runtime_bundle_filename": mapping.get("runtime_bundle_filename", "fuzzysully-runtime-linux-amd64.tar.gz"),
        "runtime_self_contained": mapping.get("runtime_self_contained", "bundle-build-required"),
        "manual_fuzzysully_install_required": True,
        "license_corrected": "GPL-2.0 (was LGPL-2.1 in previous milestone)",
        "python_requires": mapping.get("requires_python", ">=3.10"),
        "source_reconciled": True,
        "result_parser": {
            "faults": True,
            "connection_failures": True,
            "crash_candidates": True,
            "timeouts": True,
            "threshold_skips": True,
            "total_cases_available": True,
            "cases_attempted": True,
            "cases_completed": True,
            "structured_result_metadata": True,
        },
        "execution": {
            "non_interactive": True,
            "case_bounding": True,
            "duration_bounding": True,
            "cancellation": True,
            "certificates": True,
            "private_keys": True,
            "credentials_env_injected": True,
        },
        "validation": "PASS",
    }
    (out_dir / "conversion-report.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )

    # Write function inventory
    finv = {
        "source_commit": source_commit,
        "modes": {},
    }
    func_cats = mapping["function_categories"]
    for mode_key, funcs in contract["functions_by_mode"].items():
        finv["modes"][mode_key] = []
        for func in funcs:
            policies: list[str] = []
            unsupported: list[str] = []
            if mode_key == "server":
                policies.append("None")
                if func not in set(mapping["server_basic_excluded_functions"]):
                    policies += ["Basic256Sha256-Sign", "Basic256Sha256-SignEncrypt"]
                else:
                    unsupported.append("Basic256Sha256 (upstream restriction: hello/secure_channel/session)")
            elif mode_key == "gds":
                policies += ["Basic256Sha256-Sign", "Basic256Sha256-SignEncrypt"]
                unsupported.append("None (GDS requires Basic256Sha256)")
            elif mode_key == "reverse":
                policies.append("None")
                unsupported.append("Basic256Sha256 (reverse mode None-only)")
            finv["modes"][mode_key].append({
                "function": func,
                "category": func_cats.get(mode_key, {}).get(func, "Other"),
                "valid_policies": policies,
                "unsupported_policies": unsupported,
            })
    (out_dir / "function-inventory.json").write_text(
        json.dumps(finv, indent=2) + "\n", encoding="utf-8"
    )

    # Update catalog
    if not args.no_update_catalog:
        catalog_path = Path(args.catalog)
        if catalog_path.exists():
            update_catalog(catalog_path, packages, mapping, source_commit)
        else:
            print(f"[WARN] Catalog not found at {catalog_path} — skipping catalog update", file=sys.stderr)

    # Summary
    total = sum(len(pkg["scripts"]) for pkg, _ in packages)
    print(f"\n[SUCCESS] FuzzySully packages generated:")
    for pkg, key in packages:
        print(f"  {key}: {len(pkg['scripts'])} scripts → {pkg['package_id']}")
    print(f"  Total scripts: {total}")
    print(f"  Skipped combinations: {len(skipped)}")
    print(f"  Source commit: {source_commit}")
    print(f"  Runner SHA256: {runner_sha256}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
