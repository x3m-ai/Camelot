#!/usr/bin/env python3
"""generate_industrial_lab.py — Generate the provider-agnostic Industrial Lab
catalog for Camelot: providers, service manifests, and Lab templates.

Camelot = content / definitions / distribution plane.
The Morgana Server consumes this catalog (cached) to populate the
Industrial Lab page. Morgana Agents act as Lab Hosts and run the mock
devices/simulators as real processes.

Usage:
    python generate_industrial_lab.py [--out-dir morgana/industrial-lab] [--dry-run]
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent
CAMELOT_ROOT = TOOLS_DIR.parent.parent.parent
OUT_DIR = CAMELOT_ROOT / "morgana" / "industrial-lab"

UPSTREAM_REPO = "https://github.com/IndustriAgents/IndustriConnect"
UPSTREAM_COMMIT = "aa634a12ece8186b3e6c775cea1917ea89418f5e"

# Protocol slug -> service manifest facts.
# entry: how to run the mock inside its project dir via uv.
# mock fidelity: honest description (these are mocks/simulators, not emulators).
SERVICES = {
    "modbus": {
        "name": "Modbus Mock Device",
        "project": "MODBUS-Project",
        "subdir": "modbus-mock-server",
        "entry": ["uv", "run", "modbus-mock-server"],
        "description": "Mock Modbus TCP device with a realistic register map (coils, discrete inputs, input registers, holding registers) that periodically mutates to mimic live plant data.",
        "fidelity": "simulated industrial process / mock device (not a hardware emulator).",
        "default_port": 1502,
        "protocol": "modbus",
        "health": "tcp-connect",
        "state_inspection": True,
        "presets": [
            {"id": "default-device", "name": "Default Device", "description": "Upstream default register map."},
        ],
    },
    "mqtt": {
        "name": "MQTT / Sparkplug B Mock Broker",
        "project": "MQTT-Project",
        "subdir": "mqtt-mock-server",
        "entry": ["uv", "run", "mqtt-mock-server"],
        "description": "Mock MQTT broker with Sparkplug B edge nodes/devices that publish birth/death certificates and live metric data.",
        "fidelity": "simulated broker + Sparkplug edge/device behaviour.",
        "default_port": 1883,
        "protocol": "mqtt",
        "health": "tcp-connect",
        "state_inspection": False,
        "presets": [
            {"id": "basic-broker", "name": "Basic Broker", "description": "Plain MQTT broker behaviour."},
            {"id": "sparkplug-demo", "name": "Sparkplug Demo", "description": "Sparkplug B edge nodes publishing NDATA/DDATA."},
        ],
    },
    "opcua": {
        "name": "OPC UA Industrial Plant Server",
        "project": "OPCUA-Project",
        "subdir": "opcua-local-server",
        "entry": ["uv", "run", "python", "opcua_local_server.py"],
        "description": "Rich mock OPC UA server simulating an industrial plant with sensor variables, actuator controls, system status and management methods (StartProduction, StopProduction, EmergencyStop).",
        "fidelity": "simulated industrial process / mock plant server.",
        "default_port": 4840,
        "protocol": "opcua",
        "health": "tcp-connect",
        "state_inspection": True,
        "presets": [
            {"id": "default-plant", "name": "Default Plant", "description": "Upstream default plant with sensors and actuators."},
        ],
    },
    "bacnet": {
        "name": "BACnet Mock Device",
        "project": "BACnet-Project",
        "subdir": "bacnet-mock-device",
        "entry": ["uv", "run", "bacnet-mock-device"],
        "description": "Mock BACnet device exposing a JSON-over-TCP bridge for discovery and property access tests (BACnet/IP stack integration planned upstream).",
        "fidelity": "mock device / test endpoint.",
        "default_port": 7900,
        "protocol": "bacnet",
        "health": "tcp-connect",
        "state_inspection": True,
        "presets": [
            {"id": "default-device", "name": "Default Device", "description": "Upstream default device map."},
        ],
    },
    "dnp3": {
        "name": "DNP3 Mock Outstation",
        "project": "DNP3-Project",
        "subdir": "dnp3-mock-outstation",
        "entry": ["uv", "run", "dnp3-mock-outstation"],
        "description": "Mock DNP3 outstation exposing a JSON-over-TCP bridge simulating binary/analog input points and outputs.",
        "fidelity": "mock outstation / test endpoint.",
        "default_port": 7300,
        "protocol": "dnp3",
        "health": "tcp-connect",
        "state_inspection": True,
        "presets": [
            {"id": "default-outstation", "name": "Default Outstation", "description": "Upstream default point map."},
        ],
    },
    "ethercat": {
        "name": "EtherCAT Mock Slave",
        "project": "EtherCAT-Project",
        "subdir": "ethercat-mock-slave",
        "entry": ["uv", "run", "ethercat-mock-slave"],
        "description": "Minimalist EtherCAT slave simulator exposing a JSON-over-TCP bridge that mimics network scans and PDO buffers (SOEM-based mock planned upstream).",
        "fidelity": "mock slave / test endpoint (JSON bridge; not a raw EtherCAT frame emulator).",
        "default_port": 6700,
        "protocol": "ethercat",
        "health": "tcp-connect",
        "state_inspection": False,
        "presets": [
            {"id": "default-slave", "name": "Default Slave", "description": "Upstream default PDO buffer."},
        ],
    },
    "ethernetip": {
        "name": "EtherNet/IP Mock PLC",
        "project": "EtherNetIP-Project",
        "subdir": "ethernetip-mock-server",
        "entry": ["uv", "run", "ethernetip-mock-server"],
        "description": "Mock CIP server with representative tags/UDTs simulating an EtherNet/IP (Rockwell/AB-style) controller.",
        "fidelity": "mock CIP/PLC server with representative tags.",
        "default_port": 5025,
        "protocol": "ethernetip",
        "health": "tcp-connect",
        "state_inspection": True,
        "presets": [
            {"id": "default-plc", "name": "Default PLC", "description": "Upstream default tag set."},
        ],
    },
    "profibus": {
        "name": "PROFIBUS Mock Slave",
        "project": "PROFIBUS-Project",
        "subdir": "profibus-mock-slave",
        "entry": ["uv", "run", "profibus-mock-slave"],
        "description": "Mock PROFIBUS slave exposing a JSON-over-TCP bridge that mimics input/output image access (raw PROFIBUS DP/PA planned upstream).",
        "fidelity": "mock slave / test endpoint (JSON bridge; not raw PROFIBUS).",
        "default_port": 7100,
        "protocol": "profibus",
        "health": "tcp-connect",
        "state_inspection": False,
        "presets": [
            {"id": "default-slave", "name": "Default Slave", "description": "Upstream default I/O image."},
        ],
    },
    "profinet": {
        "name": "PROFINET Mock IO Device",
        "project": "PROFINET-Project",
        "subdir": "profinet-mock-server",
        "entry": ["uv", "run", "profinet-mock-server"],
        "description": "Toy PROFINET IO device exposing a JSON-over-TCP bridge that mimics device discovery and I/O payloads (raw DCP planned upstream).",
        "fidelity": "mock IO device / test endpoint (JSON bridge; not raw PROFINET).",
        "default_port": 5600,
        "protocol": "profinet",
        "health": "tcp-connect",
        "state_inspection": False,
        "presets": [
            {"id": "default-device", "name": "Default Device", "description": "Upstream default IO device."},
        ],
    },
    "s7comm": {
        "name": "Siemens S7 Mock PLC",
        "project": "S7comm-Project",
        "subdir": "s7comm-mock-server",
        "entry": ["uv", "run", "s7comm-mock-server"],
        "description": "Lightweight Siemens S7 mock built with python-snap7. Seeds deterministic data blocks (DB1 motor telemetry, DB2 alarms), inputs, outputs and marker bytes, periodically mutated to mimic live plant data.",
        "fidelity": "mock PLC (DB/I/O/SZL-style behaviour; not a full S7-1500 emulator).",
        "default_port": 1102,
        "protocol": "s7comm",
        "health": "tcp-connect",
        "state_inspection": True,
        "presets": [
            {"id": "default-plc", "name": "Default PLC", "description": "DB1 motor telemetry + DB2 alarms + toggling sensors."},
        ],
    },
}

# Generic requirements all python-process services share (honest: manual install).
BASE_REQUIREMENTS = [
    {"id": "python", "name": "Python 3.10+", "auto_install": False,
     "check_command": "python --version", "description": "Required to run the mock device."},
    {"id": "uv", "name": "uv package manager", "auto_install": False,
     "check_command": "uv --version", "description": "Required to install pinned dependencies and run the mock device."},
]

# Config fields shared by all TCP mock services.
BASE_CONFIG_FIELDS = [
    {"key": "host", "label": "Listen Interface", "type": "string",
     "default": "127.0.0.1", "required": True,
     "description": "Bind address: localhost only, Lab Host network, or custom."},
    {"key": "port", "label": "Port", "type": "int",
     "required": True, "description": "TCP port for the mock device."},
    {"key": "update_interval", "label": "Update Interval (s)", "type": "float",
     "default": "1.0", "required": False,
     "description": "How often the mock mutates simulated process values."},
]


def _service_manifest(slug: str) -> dict:
    facts = SERVICES[slug]
    env_port_var = {
        "modbus": "MODBUS_PORT", "mqtt": "MQTT_BROKER_PORT", "opcua": "OPCUA_PORT",
        "bacnet": "MOCK_BACNET_PORT", "dnp3": "MOCK_DNP3_PORT",
        "ethercat": "MOCK_ETHERCAT_PORT", "ethernetip": "MOCK_ENIP_PORT",
        "profibus": "MOCK_PROFIBUS_PORT", "profinet": "MOCK_PROFINET_PORT",
        "s7comm": "MOCK_S7_PORT",
    }[slug]
    env_host_var = {
        "modbus": "MODBUS_HOST", "mqtt": "MQTT_BROKER_HOST", "opcua": "OPCUA_HOST",
        "bacnet": "MOCK_BACNET_HOST", "dnp3": "MOCK_DNP3_HOST",
        "ethercat": "MOCK_ETHERCAT_HOST", "ethernetip": "MOCK_ENIP_HOST",
        "profibus": "MOCK_PROFIBUS_HOST", "profinet": "MOCK_PROFINET_HOST",
        "s7comm": "MOCK_S7_HOST",
    }[slug]

    return {
        "schema_version": "1.0",
        "service_id": f"industriconnect-{slug}",
        "provider": "industriconnect",
        "name": facts["name"],
        "description": facts["description"],
        "protocol": facts["protocol"],
        "fidelity": facts["fidelity"],
        "source_repository": UPSTREAM_REPO,
        "source_commit": UPSTREAM_COMMIT,
        "source_path": f"{facts['project']}/{facts['subdir']}",
        "project_dir": facts["project"],
        "subdir": facts["subdir"],
        "license": "MIT",
        "license_status": "declared-mit-in-pyproject",
        "runtime_type": "python-process",
        "supported_platforms": ["linux", "windows", "macos"],
        "raw_network_required": slug in {"ethercat", "profinet"},
        "container_required": False,
        "requirements": BASE_REQUIREMENTS,
        "default_ports": [facts["default_port"]],
        "config_schema": {
            "fields": BASE_CONFIG_FIELDS,
            "env_port_var": env_port_var,
            "env_host_var": env_host_var,
        },
        "install": {"strategy": "uv-sync", "commands": ["uv", "sync"]},
        "start": {"commands": list(facts["entry"])},
        "stop": {"strategy": "terminate-process"},
        "restart": {"strategy": "stop-then-start"},
        "reset": {"strategy": "restart-with-seed"},
        "health": {"strategy": facts["health"], "port_ref": "$config.port"},
        "logs": {"source": "process-stdout-stderr"},
        "state_inspection": {"supports_state_inspection": facts["state_inspection"]},
        "multiple_instance_support": True,
        "compatible_scripts": {
            "protocol": facts["protocol"],
            "package": f"industriconnect-{slug}-v1",
        },
        "presets": facts["presets"],
    }


TEMPLATES = [
    {
        "id": "industriconnect-single-modbus",
        "name": "IndustriConnect - Single Modbus Device",
        "description": "A single Modbus mock device on one Lab Host. Good first lab for validating read/write operations and detection telemetry.",
        "providers": ["industriconnect"],
        "services": [
            {"service_id": "industriconnect-modbus", "preset": "default-device", "port": 1502, "friendly_name": "MODBUS-PLC-01"},
        ],
        "host_placement": {"all_services_on_one_host": True},
        "startup_order": ["industriconnect-modbus"],
        "shutdown_order": ["industriconnect-modbus"],
        "reset_policy": "reset-all-services",
    },
    {
        "id": "industriconnect-single-opcua",
        "name": "IndustriConnect - Single OPC UA Plant",
        "description": "A single OPC UA mock plant server with sensors, actuators and methods.",
        "providers": ["industriconnect"],
        "services": [
            {"service_id": "industriconnect-opcua", "preset": "default-plant", "port": 4840, "friendly_name": "PUMP-STATION-OPCUA"},
        ],
        "host_placement": {"all_services_on_one_host": True},
        "startup_order": ["industriconnect-opcua"],
        "shutdown_order": ["industriconnect-opcua"],
        "reset_policy": "reset-all-services",
    },
    {
        "id": "industriconnect-single-dnp3",
        "name": "IndustriConnect - Single DNP3 Outstation",
        "description": "A single DNP3 mock outstation for binary/analog point operations.",
        "providers": ["industriconnect"],
        "services": [
            {"service_id": "industriconnect-dnp3", "preset": "default-outstation", "port": 7300, "friendly_name": "SUBSTATION-DNP3-01"},
        ],
        "host_placement": {"all_services_on_one_host": True},
        "startup_order": ["industriconnect-dnp3"],
        "shutdown_order": ["industriconnect-dnp3"],
        "reset_policy": "reset-all-services",
    },
    {
        "id": "industriconnect-basic-lab",
        "name": "IndustriConnect - Basic Industrial Lab",
        "description": "A small multi-protocol lab: one Modbus PLC and one OPC UA plant on the same host, for cross-protocol detection validation.",
        "providers": ["industriconnect"],
        "services": [
            {"service_id": "industriconnect-modbus", "preset": "default-device", "port": 1502, "friendly_name": "MODBUS-PLC-01"},
            {"service_id": "industriconnect-opcua", "preset": "default-plant", "port": 4840, "friendly_name": "PUMP-STATION-OPCUA"},
        ],
        "host_placement": {"all_services_on_one_host": True},
        "startup_order": ["industriconnect-modbus", "industriconnect-opcua"],
        "shutdown_order": ["industriconnect-opcua", "industriconnect-modbus"],
        "reset_policy": "reset-all-services",
    },
]


def build_catalog() -> dict:
    services = {slug: _service_manifest(slug) for slug in SERVICES}
    return {
        "catalog_version": "1.0.0",
        "updated": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "source": "https://github.com/x3m-ai/Camelot",
        "description": "Industrial Lab catalog — provider-agnostic lab service manifests and Lab templates. Camelot is the content/distribution plane; Morgana Server orchestrates and Morgana Agents act as Lab Hosts.",
        "providers": [
            {
                "id": "industriconnect",
                "name": "IndustriConnect",
                "description": "IndustriAgents IndustriConnect MCP suite: Python MCP servers + mock devices for BACnet, DNP3, EtherCAT, EtherNet/IP, Modbus, MQTT/Sparkplug B, OPC UA, PROFIBUS, PROFINET, and Siemens S7.",
                "source_repository": UPSTREAM_REPO,
                "source_commit": UPSTREAM_COMMIT,
                "license": "MIT",
            }
        ],
        "services": list(services.values()),
        "templates": TEMPLATES,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", default=str(OUT_DIR))
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    out = Path(args.out_dir)
    catalog = build_catalog()

    if args.dry_run:
        print(f"[LAB] {len(catalog['services'])} services, {len(catalog['templates'])} templates")
        for s in catalog["services"]:
            print(f"  {s['service_id']}: {s['protocol']} port={s['default_ports']}")
        return 0

    providers_dir = out / "providers" / "industriconnect"
    services_dir = providers_dir / "services"
    templates_dir = providers_dir / "templates"
    for d in (providers_dir, services_dir, templates_dir):
        d.mkdir(parents=True, exist_ok=True)

    # catalog.json (flat: providers summary + service/template index URLs)
    index = {
        "catalog_version": catalog["catalog_version"],
        "updated": catalog["updated"],
        "source": catalog["source"],
        "description": catalog["description"],
        "providers": catalog["providers"],
        "services": [
            {
                "service_id": s["service_id"],
                "provider": s["provider"],
                "name": s["name"],
                "protocol": s["protocol"],
                "default_ports": s["default_ports"],
                "url": f"https://raw.githubusercontent.com/x3m-ai/Camelot/main/morgana/industrial-lab/providers/industriconnect/services/{s['service_id']}.json",
            }
            for s in catalog["services"]
        ],
        "templates": [
            {
                "id": t["id"],
                "name": t["name"],
                "description": t["description"],
                "url": f"https://raw.githubusercontent.com/x3m-ai/Camelot/main/morgana/industrial-lab/providers/industriconnect/templates/{t['id']}.json",
            }
            for t in catalog["templates"]
        ],
    }
    (out / "catalog.json").write_text(json.dumps(index, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    (providers_dir / "provider.json").write_text(
        json.dumps(catalog["providers"][0], indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    for s in catalog["services"]:
        (services_dir / f"{s['service_id']}.json").write_text(
            json.dumps(s, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    for t in catalog["templates"]:
        (templates_dir / f"{t['id']}.json").write_text(
            json.dumps(t, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    # Full manifest snapshot for local validation
    (out / "full-catalog.json").write_text(json.dumps(catalog, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    # Lab service inventory report (spec: service ID, protocol, mock source
    # path, entrypoint, runtime type, platforms, default ports, requirements,
    # health strategy, reset strategy, state inspection, multiple-instance,
    # license status, published catalog path)
    inventory = [
        {
            "service_id": s["service_id"],
            "protocol": s["protocol"],
            "mock_source_path": s["source_path"],
            "entrypoint": s["start"]["commands"],
            "runtime_type": s["runtime_type"],
            "platforms": s["supported_platforms"],
            "default_ports": s["default_ports"],
            "requirements": s["requirements"],
            "health_strategy": s["health"]["strategy"],
            "reset_strategy": s["reset"]["strategy"],
            "state_inspection": s["state_inspection"]["supports_state_inspection"],
            "multiple_instance_support": s["multiple_instance_support"],
            "license_status": s["license_status"],
            "fidelity": s["fidelity"],
            "published_catalog_path": f"morgana/industrial-lab/providers/industriconnect/services/{s['service_id']}.json",
        }
        for s in catalog["services"]
    ]
    (out / "industriconnect-lab-service-inventory.json").write_text(
        json.dumps(inventory, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print(f"[SUCCESS] Industrial Lab catalog generated:")
    print(f"  Services:  {len(catalog['services'])}")
    print(f"  Templates: {len(catalog['templates'])}")
    print(f"  Providers: {len(catalog['providers'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
