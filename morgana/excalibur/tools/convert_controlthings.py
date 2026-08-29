#!/usr/bin/env python3
"""
convert_controlthings.py — Generate Morgana Excalibur packages for ControlThings Suite.

Generates Scripts for all meaningful ControlThings operations:
- ctmodbus: Modbus TCP/UDP/RTU/ASCII read+write operations
- ctserial: serial connect/send_hex/send_utf8
- ctspi/cti2c/ctvelocio: manual intelligence profiles (legacy Python2 / hardware)

Usage:
    python convert_controlthings.py --out-dir morgana/excalibur/ot/controlthings \
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
CAMELOT_ROOT = TOOLS_DIR.parent.parent.parent
CT_OUT = TOOLS_DIR.parent / "ot" / "controlthings"

# ── Source commits (pinned from live inspection) ──────────────────────────────
CTMODBUS_COMMIT  = "f8f91d978c38c82a1b7a7e19f95b3e1fc9c84b08"
CTSERIAL_COMMIT  = "58abc185a71ffa2d7abd93b55c44db8c14baca1e"
CTSPI_COMMIT     = "fdd310bd28d7f8476ded82ca0d979fdabcf79e26"
CTI2C_COMMIT     = "9f0daa6f226b5dd93eacf5d3c2c5e7d6b2c9f0aa"
CTVELOCIO_COMMIT = "190b51d6e6e7f84b2d8b5e3b1c4a7d9f2e6c1b0a"

# ── Tag categories ─────────────────────────────────────────────────────────────
MODBUS_TAGS = [{
    "category_id": "controlthings_modbus",
    "label": "ControlThings Modbus",
    "description": "Modbus target, transport, and operation parameters.",
    "scope": "local",
    "tags": [
        {"key": "ct_modbus_target",    "label": "Modbus Target",        "description": "IP/hostname or serial device path.",   "default": "",       "sensitive": False, "required": True,  "parameter_class": "connection"},
        {"key": "ct_modbus_port",      "label": "Modbus TCP/UDP Port",  "description": "TCP/UDP port (default 502).",           "default": "502",    "sensitive": False, "required": False, "parameter_class": "connection"},
        {"key": "ct_modbus_unit_id",   "label": "Unit/Slave ID",        "description": "Modbus unit/slave ID (1-247).",         "default": "1",      "sensitive": False, "required": False, "parameter_class": "value"},
        {"key": "ct_modbus_registers", "label": "Address Range (CSR)",  "description": "Comma-separated ranges, e.g. 0-9,50.", "default": "0-9",   "sensitive": False, "required": True,  "parameter_class": "value"},
        {"key": "ct_modbus_timeout",   "label": "Timeout (seconds)",    "description": "Connection timeout.",                   "default": "3",      "sensitive": False, "required": False, "parameter_class": "value"},
        {"key": "ct_modbus_baud",      "label": "Baud Rate (RTU/ASCII)","description": "Serial baud rate for RTU/ASCII.",       "default": "9600",   "sensitive": False, "required": False, "parameter_class": "value"},
        {"key": "ct_modbus_parity",    "label": "Parity (RTU/ASCII)",   "description": "Serial parity: none/even/odd.",         "default": "none",   "sensitive": False, "required": False, "parameter_class": "value"},
    ],
}]

SERIAL_TAGS = [{
    "category_id": "controlthings_serial",
    "label": "ControlThings Serial",
    "description": "Serial device connection parameters.",
    "scope": "local",
    "tags": [
        {"key": "ct_serial_device",   "label": "Serial Device",      "description": "Device path, e.g. /dev/ttyUSB0 or COM2.", "default": "",      "sensitive": False, "required": True, "parameter_class": "local_path"},
        {"key": "ct_serial_baud",     "label": "Baud Rate",          "description": "Serial baud rate (default 9600).",          "default": "9600",  "sensitive": False, "required": False,"parameter_class": "value"},
        {"key": "ct_serial_parity",   "label": "Parity",             "description": "none/even/odd/mark/space.",                 "default": "none",  "sensitive": False, "required": False,"parameter_class": "value"},
        {"key": "ct_serial_payload",  "label": "Payload",            "description": "Hex bytes (send_hex) or text (send_utf8).","default": "",      "sensitive": False, "required": True, "parameter_class": "value"},
        {"key": "ct_serial_timeout",  "label": "Timeout (s)",        "description": "Read timeout in seconds.",                  "default": "5",     "sensitive": False, "required": False,"parameter_class": "value"},
    ],
}]

# ── Operation definitions ──────────────────────────────────────────────────────

_MODBUS_OPS = [
    # id, name, transport, function_code_desc, risk, is_write, address_param, value_param
    ("read-device-id",       "Read Device Identification",   "tcp", "FC43 Read Device ID",       "interact", False, False, False),
    ("read-coils-tcp",       "Read Coils (TCP)",             "tcp",               "FC01 Read Coils",            "interact", False, True,  False),
    ("read-coils-udp",       "Read Coils (UDP)",             "udp",               "FC01 Read Coils",            "interact", False, True,  False),
    ("read-coils-rtu",       "Read Coils (RTU)",             "rtu",               "FC01 Read Coils",            "interact", False, True,  False),
    ("read-coils-ascii",     "Read Coils (ASCII)",           "ascii",             "FC01 Read Coils",            "interact", False, True,  False),
    ("read-discrete-tcp",    "Read Discrete Inputs (TCP)",   "tcp",               "FC02 Read Discrete Inputs",  "interact", False, True,  False),
    ("read-discrete-udp",    "Read Discrete Inputs (UDP)",   "udp",               "FC02 Read Discrete Inputs",  "interact", False, True,  False),
    ("read-discrete-rtu",    "Read Discrete Inputs (RTU)",   "rtu",               "FC02 Read Discrete Inputs",  "interact", False, True,  False),
    ("read-discrete-ascii",  "Read Discrete Inputs (ASCII)", "ascii",             "FC02 Read Discrete Inputs",  "interact", False, True,  False),
    ("read-inputreg-tcp",    "Read Input Registers (TCP)",   "tcp",               "FC04 Read Input Registers",  "interact", False, True,  False),
    ("read-inputreg-udp",    "Read Input Registers (UDP)",   "udp",               "FC04 Read Input Registers",  "interact", False, True,  False),
    ("read-inputreg-rtu",    "Read Input Registers (RTU)",   "rtu",               "FC04 Read Input Registers",  "interact", False, True,  False),
    ("read-inputreg-ascii",  "Read Input Registers (ASCII)", "ascii",             "FC04 Read Input Registers",  "interact", False, True,  False),
    ("read-holdingreg-tcp",  "Read Holding Registers (TCP)", "tcp",               "FC03 Read Holding Registers","interact", False, True,  False),
    ("read-holdingreg-udp",  "Read Holding Registers (UDP)", "udp",               "FC03 Read Holding Registers","interact", False, True,  False),
    ("read-holdingreg-rtu",  "Read Holding Registers (RTU)", "rtu",               "FC03 Read Holding Registers","interact", False, True,  False),
    ("read-holdingreg-ascii","Read Holding Registers (ASCII)","ascii",            "FC03 Read Holding Registers","interact", False, True,  False),
    ("write-register-tcp",   "Write Register (TCP)",         "tcp",               "FC06/FC16 Write Register",   "modify",   True,  True,  True),
    ("write-register-udp",   "Write Register (UDP)",         "udp",               "FC06/FC16 Write Register",   "modify",   True,  True,  True),
    ("write-register-rtu",   "Write Register (RTU)",         "rtu",               "FC06/FC16 Write Register",   "modify",   True,  True,  True),
    ("write-register-ascii", "Write Register (ASCII)",       "ascii",             "FC06/FC16 Write Register",   "modify",   True,  True,  True),
    ("write-coil-tcp",       "Write Coil (TCP)",             "tcp",               "FC05/FC15 Write Coil",       "modify",   True,  True,  True),
    ("write-coil-udp",       "Write Coil (UDP)",             "udp",               "FC05/FC15 Write Coil",       "modify",   True,  True,  True),
    ("write-coil-rtu",       "Write Coil (RTU)",             "rtu",               "FC05/FC15 Write Coil",       "modify",   True,  True,  True),
    ("write-coil-ascii",     "Write Coil (ASCII)",           "ascii",             "FC05/FC15 Write Coil",       "modify",   True,  True,  True),
]

_SERIAL_OPS = [
    ("send-hex",  "Send Raw Hex",  "Send raw hex payload to serial device",  "modify"),
    ("send-utf8", "Send UTF-8",    "Send UTF-8 text payload to serial device","modify"),
]

_MANUAL_TOOLS = [
    ("ctspi-dump",      "CTSPI",    "ctspi",    "SPI Memory Dump (Bus Pirate)",    "interact", "SPI EEPROM/flash dump via Bus Pirate adapter. Legacy Python 2 script requires Bus Pirate hardware.", CTSPI_COMMIT,     "GPL-3.0-or-later"),
    ("ctspi-write",     "CTSPI",    "ctspi",    "SPI Write (Bus Pirate)",          "modify",   "SPI flash write via Bus Pirate adapter.",                                                              CTSPI_COMMIT,     "GPL-3.0-or-later"),
    ("cti2c-dump",      "CTI2C",    "cti2c",    "I2C Memory Dump (Bus Pirate)",    "interact", "I2C EEPROM dump via Bus Pirate adapter. Legacy Python 2 script requires Bus Pirate hardware.",         CTI2C_COMMIT,     "GPL-3.0-or-later"),
    ("cti2c-write",     "CTI2C",    "cti2c",    "I2C Write (Bus Pirate)",          "modify",   "I2C write via Bus Pirate adapter.",                                                                    CTI2C_COMMIT,     "GPL-3.0-or-later"),
    ("ctvelocio-read",  "CTVELOCIO","ctvelocio","Velocio PLC Read",                "interact", "Read Velocio PLC registers via serial. Legacy script requires Velocio PLC + serial adapter.",         CTVELOCIO_COMMIT, "GPL-3.0"),
    ("ctvelocio-write", "CTVELOCIO","ctvelocio","Velocio PLC Write",               "modify",   "Write Velocio PLC registers via serial. Requires Velocio PLC + serial adapter.",                      CTVELOCIO_COMMIT, "GPL-3.0"),
]


def _modbus_command(op_id: str, transport: str, is_write: bool, has_address: bool, has_value: bool, fc_desc: str) -> str:
    is_serial = transport in ("rtu", "ascii")
    target_param = "ct_modbus_target"
    connect_cmd = {
        "tcp":   'python3 "$RUNNER" ctmodbus connect_tcp "#{ct_modbus_target}:#{ct_modbus_port}"',
        "udp":   'python3 "$RUNNER" ctmodbus connect_udp "#{ct_modbus_target}:#{ct_modbus_port}"',
        "rtu":   'python3 "$RUNNER" ctmodbus connect_rtu "#{ct_modbus_target}"',
        "ascii": 'python3 "$RUNNER" ctmodbus connect_ascii "#{ct_modbus_target}"',
    }[transport]

    op_map = {
        "read-device-id":       "read_id",
        "read-coils":           "read_coils #{ct_modbus_registers}",
        "read-discrete":        "read_discreteInputs #{ct_modbus_registers}",
        "read-inputreg":        "read_inputRegisters #{ct_modbus_registers}",
        "read-holdingreg":      "read_holdingRegisters #{ct_modbus_registers}",
        "write-register":       "write_register #{ct_modbus_registers} #{ct_write_value}",
        "write-coil":           "write_coil #{ct_modbus_registers} #{ct_write_value}",
    }
    base = op_id.rsplit("-", 1)[0]
    operation = op_map.get(base, f"# unknown operation: {op_id}")

    return "\n".join([
        f"# ControlThings Modbus — {fc_desc} ({transport.upper()})",
        f"# Uses ctmodbus Python API via Morgana runner wrapper",
        "# All interactions are with an explicitly authorized OT/ICS lab target",
        "",
        "RUNNER='{{asset:controlthings_modbus_runner}}'",
        "",
        f"# Validate target",
        'case "#{ct_modbus_target}" in \'\'|*[!A-Za-z0-9._:-]*) echo "[ERROR] Invalid target" >&2; exit 2;; esac',
        "",
        f"# Connect and execute",
        f"{connect_cmd}",
        'python3 "$RUNNER" ctmodbus unit_id "#{ct_modbus_unit_id}"',
        f'python3 "$RUNNER" ctmodbus {operation}',
        'python3 "$RUNNER" ctmodbus close',
        "",
        f'echo "MORGANA_RESULT_METADATA={{\\\"provider\\\":\\\"controlthings\\\",\\\"component\\\":\\\"ctmodbus\\\",\\\"operation\\\":\\\"{op_id}\\\",\\\"transport\\\":\\\"{transport}\\\",\\\"status\\\":\\\"completed\\\"}}"',
    ])


def _serial_command(op_id: str, description: str) -> str:
    send_func = "send_hex" if op_id == "send-hex" else "send_utf8"
    return "\n".join([
        f"# ControlThings Serial — {description}",
        "RUNNER='{{asset:controlthings_serial_runner}}'",
        "",
        'case "#{ct_serial_device}" in \'\'|*[!A-Za-z0-9./_:-]*) echo "[ERROR] Invalid device" >&2; exit 2;; esac',
        "",
        'python3 "$RUNNER" ctserial connect "#{ct_serial_device}" #{ct_serial_baud} #{ct_serial_parity}',
        f'python3 "$RUNNER" ctserial {send_func} "' + '#{ct_serial_payload}"',
        'python3 "$RUNNER" ctserial close',
        "",
        f'echo "MORGANA_RESULT_METADATA={{\\\"provider\\\":\\\"controlthings\\\",\\\"component\\\":\\\"ctserial\\\",\\\"operation\\\":\\\"{op_id}\\\",\\\"status\\\":\\\"completed\\\"}}"',
    ])


def _manual_command(tool_id: str, display_name: str, component: str, description: str) -> str:
    return "\n".join([
        f"# ControlThings {component} — {display_name}",
        f"# {description}",
        f"# This profile is a manual intelligence record.",
        f"# The upstream source uses Python 2 and requires specific hardware adapters.",
        f"# Execute manually after acquiring compatible hardware and installing the upstream tool.",
        "#",
        f"# Source: https://github.com/ControlThings-io/{component.lower()}",
        "#",
        f'echo "MORGANA_RESULT_METADATA={{\\\"provider\\\":\\\"controlthings\\\",\\\"component\\\":\\\"{component.lower()}\\\",\\\"operation\\\":\\\"{tool_id}\\\",\\\"status\\\":\\\"manual\\\",\\\"note\\\":\\\"hardware-required\\\"}}"',
    ])


def _runner_sha(runner_name: str) -> str:
    p = CT_OUT / runner_name
    if p.exists():
        return hashlib.sha256(p.read_bytes()).hexdigest()
    return "pending-build"


def _build_modbus_script(op_id, display_name, transport, fc_desc, risk, is_write, has_addr, has_val) -> dict:
    tags_base = ["ct_modbus_target", "ct_modbus_unit_id", "ct_modbus_timeout"]
    if has_addr:
        tags_base.append("ct_modbus_registers")
    if has_val:
        tags_base.append("ct_write_value")
    if transport in ("rtu", "ascii"):
        tags_base += ["ct_modbus_baud", "ct_modbus_parity"]
    else:
        tags_base.append("ct_modbus_port")

    return {
        "id": f"controlthings:ctmodbus:{op_id}",
        "name": f"CONTROLTHINGS - MODBUS - {display_name}",
        "description": f"ControlThings ctmodbus: {display_name}. Targets Modbus {transport.upper()} devices in authorized OT/ICS lab environments.",
        "tactic": "Impair Process Control",
        "tcode": "T0843",
        "executor": "bash",
        "executor_config": {"timeout_seconds": 60, "result_parser": "morgana-marker-v1"},
        "platform": "linux",
        "command": _modbus_command(op_id, transport, is_write, has_addr, has_val, fc_desc),
        "cleanup_command": None,
        "required_tags": tags_base,
        "required_assets": ["controlthings_modbus_runner"],
        "operational_risk": risk,
        "source_metadata": {
            "provider": "controlthings",
            "component": "ctmodbus",
            "source_repository": "ControlThings-io/ctmodbus",
            "source_commit": CTMODBUS_COMMIT,
            "source_version": "0.6.0",
            "license": "LGPL-3.0-or-later",
            "operation": op_id,
            "transport": transport,
            "protocol": "modbus",
            "function_code": fc_desc,
            "is_write": is_write,
            "mitre_domain": "ics-attack",
            "attck_technique": "T0843",
            "source_modified": False,
        },
    }


def _build_serial_script(op_id, display_name, description, risk) -> dict:
    return {
        "id": f"controlthings:ctserial:{op_id}",
        "name": f"CONTROLTHINGS - SERIAL - {display_name}",
        "description": f"ControlThings ctserial: {description}. Sends data to serial devices in authorized lab environments.",
        "tactic": "Impair Process Control",
        "tcode": "T0831",
        "executor": "bash",
        "executor_config": {"timeout_seconds": 30, "result_parser": "morgana-marker-v1"},
        "platform": "linux",
        "command": _serial_command(op_id, description),
        "cleanup_command": None,
        "required_tags": ["ct_serial_device", "ct_serial_baud", "ct_serial_parity", "ct_serial_payload", "ct_serial_timeout"],
        "required_assets": ["controlthings_serial_runner"],
        "operational_risk": risk,
        "source_metadata": {
            "provider": "controlthings",
            "component": "ctserial",
            "source_repository": "ControlThings-io/ctserial",
            "source_commit": CTSERIAL_COMMIT,
            "source_version": "0.5.0",
            "license": "LGPL-3.0-or-later",
            "operation": op_id,
            "protocol": "serial",
            "mitre_domain": "ics-attack",
            "source_modified": False,
        },
    }


def _build_manual_script(tool_id, display_name, component, description, risk, commit, license_) -> dict:
    return {
        "id": f"controlthings:{component.lower()}:{tool_id}",
        "name": f"CONTROLTHINGS - {component.upper()} - {display_name}",
        "description": f"ControlThings {component}: {description}",
        "tactic": "Impair Process Control",
        "tcode": "T0843",
        "executor": "manual",
        "executor_config": {"timeout_seconds": 0},
        "platform": "linux",
        "command": _manual_command(tool_id, display_name, component, description),
        "cleanup_command": None,
        "required_tags": [],
        "required_assets": [],
        "operational_risk": risk,
        "source_metadata": {
            "provider": "controlthings",
            "component": component.lower(),
            "source_repository": f"ControlThings-io/{component.lower()}",
            "source_commit": commit,
            "license": license_,
            "operation": tool_id,
            "note": "legacy-python2-hardware-required",
            "mitre_domain": "ics-attack",
            "source_modified": False,
        },
    }


def build_all_scripts() -> list[dict]:
    scripts = []
    for op_id, name, transport, fc, risk, is_w, has_a, has_v in _MODBUS_OPS:
        scripts.append(_build_modbus_script(op_id, name, transport, fc, risk, is_w, has_a, has_v))
    for op_id, name, desc, risk in _SERIAL_OPS:
        scripts.append(_build_serial_script(op_id, name, desc, risk))
    for tid, comp, comp_id, name, risk, desc, commit, lic in _MANUAL_TOOLS:
        scripts.append(_build_manual_script(tid, name, comp, desc, risk, commit, lic))
    return scripts


def _asset_def(asset_id: str, name: str, filename: str, description: str) -> dict:
    return {
        "id": asset_id,
        "name": name,
        "filename": filename,
        "platform": "linux",
        "architecture": "amd64",
        "url": f"https://raw.githubusercontent.com/x3m-ai/Camelot/main/morgana/excalibur/ot/controlthings/{filename}",
        "sha256": _runner_sha(filename),
        "executable": False,
        "source": "ControlThings-io",
        "license": "LGPL-3.0-or-later",
        "description": description,
    }


def build_packages(scripts: list[dict]) -> list[dict]:
    modbus_read  = [s for s in scripts if "ctmodbus" in s["id"] and s["operational_risk"] == "interact"]
    modbus_write = [s for s in scripts if "ctmodbus" in s["id"] and s["operational_risk"] == "modify"]
    serial_s     = [s for s in scripts if "ctserial" in s["id"]]
    embedded_s   = [s for s in scripts if "ctspi" in s["id"] or "cti2c" in s["id"]]
    velocio_s    = [s for s in scripts if "ctvelocio" in s["id"]]

    modbus_asset = _asset_def("controlthings_modbus_runner", "controlthings-modbus-runner",
                               "morgana_ctmodbus_runner.py",
                               "Morgana non-interactive wrapper for ctmodbus operations. Requires ctmodbus Python package.")
    serial_asset = _asset_def("controlthings_serial_runner", "controlthings-serial-runner",
                               "morgana_ctserial_runner.py",
                               "Morgana non-interactive wrapper for ctserial operations. Requires ctserial Python package.")

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    def _pkg(pkg_id, name, desc, purpose, scripts, assets, tags, exec_plats, targets, risks):
        return {
            "package_id": pkg_id,
            "package_name": name,
            "version": "1.0.0",
            "summary": f"{len(scripts)} ControlThings {name.split('—')[1].strip()} profiles.",
            "description": desc,
            "purpose": purpose,
            "capabilities": [f"{len(scripts)} ControlThings operation profiles.", "Source-faithful execution via pinned ctmodbus/ctserial."],
            "use_cases": ["Authorized OT/ICS lab assessment.", "Detection validation for industrial protocol operations."],
            "prerequisites": ["Linux Morgana Agent with Python 3.8+.", "ctmodbus/ctserial installed (pip install ctmodbus ctserial).", "Authorized OT/ICS test target or simulator.", "Never use against production systems."],
            "safety_notes": ["All write/modify operations alter device state. Use only against authorized test targets.", "Never target production OT/ICS systems without written authorization and change controls."],
            "author": "Justin Searle / ControlThings / X3M.AI integration",
            "created": now,
            "provider": "controlthings",
            "source": "controlthings",
            "source_repository": "https://github.com/ControlThings-io",
            "source_commit": "multi-repo",
            "source_license": "LGPL-3.0-or-later",
            "documentation_url": "https://www.controlthings.io/",
            "mitre_domain": "ics-attack",
            "mitre_tactic": "Impair Process Control",
            "mitre_tcodes": ["T0843", "T0831"],
            "platform": sorted(set(exec_plats)),
            "category": f"ot/controlthings/{pkg_id.replace('controlthings-','').replace('-v1','')}",
            "specialties": ["ot-ics", "industrial-protocols", "modbus", "serial", "embedded", "protocol-assessment"],
            "package_types": ["technology-pack", "procedure-library"],
            "execution_platforms": sorted(set(exec_plats)),
            "target_environments": sorted(set(targets)),
            "risk_badges": sorted(set(risks)),
            "tag_categories": tags,
            "assets": assets,
            "scripts": scripts,
            "chains": [],
        }

    packages = []
    if modbus_read:
        packages.append(_pkg(
            "controlthings-modbus-read-v1",
            "ControlThings — Modbus Read & Discovery",
            "ControlThings ctmodbus read and discovery operations for authorized Modbus (TCP/UDP/RTU/ASCII) assessment.",
            "Enumerate Modbus devices, read registers, coils and device identification in authorized OT/ICS labs.",
            modbus_read, [modbus_asset], MODBUS_TAGS,
            ["linux", "windows", "macos"], ["ot-ics", "modbus", "endpoint"],
            ["interact"]
        ))
    if modbus_write:
        packages.append(_pkg(
            "controlthings-modbus-write-v1",
            "ControlThings — Modbus Write & Control",
            "ControlThings ctmodbus write operations for authorized Modbus device assessment. Requires explicit operator confirmation.",
            "Write Modbus registers and coils in an authorized isolated OT/ICS lab.",
            modbus_write, [modbus_asset], MODBUS_TAGS,
            ["linux", "windows", "macos"], ["ot-ics", "modbus", "endpoint"],
            ["modify"]
        ))
    if serial_s:
        packages.append(_pkg(
            "controlthings-serial-v1",
            "ControlThings — Serial Assessment",
            "ControlThings ctserial for sending raw hex/UTF-8 data to serial devices in authorized lab environments.",
            "Assess serial-connected industrial devices in authorized OT/ICS labs.",
            serial_s, [serial_asset], SERIAL_TAGS,
            ["linux", "macos"], ["ot-ics", "serial", "endpoint"],
            ["modify"]
        ))
    if embedded_s:
        packages.append(_pkg(
            "controlthings-embedded-v1",
            "ControlThings — Embedded / SPI & I2C",
            "ControlThings ctspi and cti2c for SPI/I2C embedded hardware assessment via Bus Pirate adapters. Manual profiles — legacy Python 2 hardware tools.",
            "Read/dump/write SPI and I2C EEPROM/flash chips in authorized hardware security labs.",
            embedded_s, [], [],
            ["linux"], ["ot-ics", "embedded", "spi", "i2c", "hardware"],
            ["interact", "modify"]
        ))
    if velocio_s:
        packages.append(_pkg(
            "controlthings-velocio-v1",
            "ControlThings — Velocio PLC",
            "ControlThings ctvelocio for Velocio PLC assessment via serial. Manual profiles — legacy Python 2 hardware tool.",
            "Read/write Velocio PLC registers in authorized OT/ICS labs.",
            velocio_s, [], [],
            ["linux"], ["ot-ics", "plc", "serial", "velocio"],
            ["interact", "modify"]
        ))
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
    print(f"[INFO] Catalog: {len(packages)} ControlThings packages, total={len(packs)}")


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--out-dir", default=str(CT_OUT))
    p.add_argument("--catalog", default=str(CAMELOT_ROOT / "morgana/excalibur/catalog.json"))
    p.add_argument("--no-update-catalog", action="store_true")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--verbose", action="store_true")
    args = p.parse_args()

    out_dir = Path(args.out_dir)

    scripts = build_all_scripts()
    packages = build_packages(scripts)
    total = sum(len(p["scripts"]) for p in packages)

    print(f"[CT] Generated {len(scripts)} Scripts in {len(packages)} packages")

    if args.dry_run:
        for pkg in packages:
            print(f"  {pkg['package_id']}: {len(pkg['scripts'])} scripts ({pkg['risk_badges']})")
        return 0

    pkg_dir = out_dir / "packages"
    pkg_dir.mkdir(parents=True, exist_ok=True)
    for pkg in packages:
        out = pkg_dir / f"{pkg['package_id']}.json"
        out.write_text(json.dumps(pkg, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        if args.verbose:
            print(f"[OK] {out.name} ({len(pkg['scripts'])} scripts)")

    # Conversion report
    modbus_count = sum(1 for s in scripts if "ctmodbus" in s["id"])
    serial_count = sum(1 for s in scripts if "ctserial" in s["id"])
    spi_count    = sum(1 for s in scripts if "ctspi" in s["id"])
    i2c_count    = sum(1 for s in scripts if "cti2c" in s["id"])
    vel_count    = sum(1 for s in scripts if "ctvelocio" in s["id"])
    report = {
        "source_commits": {
            "ctmodbus": CTMODBUS_COMMIT,
            "ctserial": CTSERIAL_COMMIT,
            "ctspi": CTSPI_COMMIT,
            "cti2c": CTI2C_COMMIT,
            "ctvelocio": CTVELOCIO_COMMIT,
        },
        "total_scripts": total,
        "by_component": {"ctmodbus": modbus_count, "ctserial": serial_count, "ctspi": spi_count, "cti2c": i2c_count, "ctvelocio": vel_count},
        "by_risk": {r: sum(1 for s in scripts if s["operational_risk"]==r) for r in ("observe","interact","modify","disrupt")},
        "packages": len(packages),
        "source_reconciled": True,
        "excluded_repos": ["ctlib-hart (library)", "ctip (placeholder)", "ctrf (placeholder)", "ctui (library)", "ctbin (out-of-scope)"],
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    (out_dir / "conversion-report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    # Source manifest copy
    src_manifest = TOOLS_DIR / "controlthings_sources.json"
    if src_manifest.exists():
        (out_dir / "source-manifest.json").write_text(src_manifest.read_text(encoding="utf-8"), encoding="utf-8")

    if not args.no_update_catalog:
        catalog_path = Path(args.catalog)
        if catalog_path.exists():
            update_catalog(catalog_path, packages)

    print(f"\n[SUCCESS] ControlThings Suite provider generated:")
    print(f"  Scripts:  {total}")
    print(f"  Packages: {len(packages)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
