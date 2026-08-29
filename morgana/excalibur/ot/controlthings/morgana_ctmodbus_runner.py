#!/usr/bin/env python3
"""
morgana_ctmodbus_runner.py — Non-interactive ctmodbus wrapper for Morgana.

Executes a single ctmodbus operation programmatically via the pymodbus library
(used internally by ctmodbus) without requiring the interactive ctui shell.

Usage:
    python morgana_ctmodbus_runner.py <operation> [args...]

Operations: connect_tcp, connect_udp, connect_rtu, connect_ascii, close,
            unit_id, read_id, read_coils, read_discrete, read_inputreg,
            read_holdingreg, write_register, write_coil
"""
from __future__ import annotations

import json
import sys
import time

MORGANA_RESULT_PREFIX = "MORGANA_RESULT_METADATA="


def _emit(result: dict) -> None:
    print(f"{MORGANA_RESULT_PREFIX}{json.dumps(result, separators=(',', ':'))}", flush=True)


def main() -> int:
    if len(sys.argv) < 2:
        print("[ERROR] Usage: morgana_ctmodbus_runner.py <operation> [args...]", file=sys.stderr)
        return 2

    op = sys.argv[1]
    args = sys.argv[2:]
    result = {"provider": "controlthings", "component": "ctmodbus", "operation": op, "status": "started"}
    start = time.time()

    try:
        from pymodbus.client import ModbusTcpClient, ModbusUdpClient, ModbusSerialClient
        from pymodbus.mei_message import ReadDeviceInformationRequest
    except ImportError as exc:
        result["status"] = "init_failed"
        result["error"] = f"pymodbus not importable: {exc}. Install ctmodbus: pip install ctmodbus"
        _emit(result)
        return 2

    # Session stored as a module-level singleton for this process
    session = None
    unit_id = 1

    try:
        if op == "connect_tcp":
            host_port = args[0] if args else "localhost:502"
            if ":" in host_port:
                host, port = host_port.rsplit(":", 1)
                port = int(port)
            else:
                host, port = host_port, 502
            session = ModbusTcpClient(host, port=port, timeout=3)
            session.connect()
            result["connected"] = True
            result["target"] = f"{host}:{port}"
            result["transport"] = "tcp"
        elif op == "connect_udp":
            host_port = args[0] if args else "localhost:502"
            host, port = (host_port.rsplit(":", 1) if ":" in host_port else (host_port, "502"))
            session = ModbusUdpClient(host, port=int(port))
            session.connect()
            result["transport"] = "udp"
        elif op == "connect_rtu":
            device = args[0] if args else "/dev/ttyUSB0"
            baud = int(args[1]) if len(args) > 1 else 9600
            session = ModbusSerialClient(method="rtu", port=device, baudrate=baud, timeout=1)
            session.connect()
            result["transport"] = "rtu"
        elif op == "connect_ascii":
            device = args[0] if args else "/dev/ttyUSB0"
            session = ModbusSerialClient(method="ascii", port=device, timeout=1)
            session.connect()
            result["transport"] = "ascii"
        elif op == "unit_id":
            unit_id = int(args[0]) if args else 1
            result["unit_id"] = unit_id
        elif op == "close":
            if session:
                session.close()
                result["status"] = "closed"
        elif op == "read_id":
            if not session:
                raise RuntimeError("No active session")
            r = session.execute(ReadDeviceInformationRequest(unit=unit_id))
            result["device_info"] = {k: str(v) for k, v in enumerate(r.information)} if not r.isError() else {}
        elif op in ("read_coils", "read_discrete", "read_inputreg", "read_holdingreg"):
            if not session:
                raise RuntimeError("No active session")
            csr = args[0] if args else "0-9"
            start_addr = int(csr.split("-")[0].split(",")[0])
            count = 10
            if "-" in csr.split(",")[0]:
                s, e = csr.split(",")[0].split("-")
                count = int(e) - int(s) + 1
            fn_map = {
                "read_coils":      lambda s, c: session.read_coils(s, c, unit=unit_id),
                "read_discrete":   lambda s, c: session.read_discrete_inputs(s, c, unit=unit_id),
                "read_inputreg":   lambda s, c: session.read_input_registers(s, c, unit=unit_id),
                "read_holdingreg": lambda s, c: session.read_holding_registers(s, c, unit=unit_id),
            }
            r = fn_map[op](start_addr, count)
            if op in ("read_coils", "read_discrete"):
                result["values"] = list(r.bits[:count]) if hasattr(r, "bits") else []
            else:
                result["values"] = list(r.registers[:count]) if hasattr(r, "registers") else []
            result["address"] = start_addr
            result["count"] = count
        elif op == "write_register":
            if not session:
                raise RuntimeError("No active session")
            addr = int(args[0]) if args else 0
            val = int(args[1]) if len(args) > 1 else 0
            session.write_register(addr, val, unit=unit_id)
            result["address"] = addr
            result["value"] = val
        elif op == "write_coil":
            if not session:
                raise RuntimeError("No active session")
            addr = int(args[0]) if args else 0
            val = bool(int(args[1])) if len(args) > 1 else False
            session.write_coil(addr, val, unit=unit_id)
            result["address"] = addr
            result["value"] = val
        else:
            result["status"] = "unknown_operation"
            result["error"] = f"Unknown operation: {op}"
            _emit(result)
            return 1

        result["status"] = "completed"
        result["duration_ms"] = round((time.time() - start) * 1000)
        _emit(result)
        return 0

    except Exception as exc:
        result["status"] = "failed"
        result["error"] = str(exc)
        result["duration_ms"] = round((time.time() - start) * 1000)
        _emit(result)
        return 1


if __name__ == "__main__":
    sys.exit(main())
