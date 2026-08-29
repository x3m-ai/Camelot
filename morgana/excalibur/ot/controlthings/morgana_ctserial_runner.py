#!/usr/bin/env python3
"""
morgana_ctserial_runner.py — Non-interactive ctserial wrapper for Morgana.

Executes ctserial operations via pyserial without the interactive ctui shell.

Usage:
    python morgana_ctserial_runner.py <operation> [args...]
"""
from __future__ import annotations

import json
import re
import sys
import time

MORGANA_RESULT_PREFIX = "MORGANA_RESULT_METADATA="


def _emit(result: dict) -> None:
    print(f"{MORGANA_RESULT_PREFIX}{json.dumps(result, separators=(',', ':'))}", flush=True)


def main() -> int:
    if len(sys.argv) < 2:
        print("[ERROR] Usage: morgana_ctserial_runner.py <operation> [args...]", file=sys.stderr)
        return 2

    op = sys.argv[1]
    args = sys.argv[2:]
    result = {"provider": "controlthings", "component": "ctserial", "operation": op, "status": "started"}
    start = time.time()

    try:
        import serial
    except ImportError as exc:
        result["status"] = "init_failed"
        result["error"] = f"pyserial not importable: {exc}. Install ctserial: pip install ctserial"
        _emit(result)
        return 2

    session = None
    parity_map = {
        "none": serial.PARITY_NONE, "even": serial.PARITY_EVEN,
        "odd": serial.PARITY_ODD, "mark": serial.PARITY_MARK, "space": serial.PARITY_SPACE,
    }

    try:
        if op == "connect":
            device  = args[0] if args else "/dev/null"
            baud    = int(args[1]) if len(args) > 1 else 9600
            parity  = args[2].lower() if len(args) > 2 else "none"
            session = serial.Serial(
                port=device, baudrate=baud,
                parity=parity_map.get(parity, serial.PARITY_NONE),
                stopbits=serial.STOPBITS_ONE, bytesize=serial.EIGHTBITS,
            )
            result["device"] = device
            result["baud"] = baud
            result["connected"] = session.isOpen()

        elif op == "send_hex":
            if not session:
                raise RuntimeError("No session — call connect first")
            raw = (args[0] if args else "").lower().replace("0x","").replace("\\x","").replace(" ","")
            if not re.match(r'^[0-9a-f]+$', raw):
                raise ValueError("Only hex characters allowed")
            tx = bytes.fromhex(raw)
            session.write(tx)
            timeout = float(args[1]) if len(args) > 1 else 5.0
            session.timeout = timeout
            rx = session.read(session.inWaiting() or 256)
            result["tx_hex"] = raw
            result["rx_hex"] = rx.hex()
            result["rx_bytes"] = len(rx)

        elif op == "send_utf8":
            if not session:
                raise RuntimeError("No session — call connect first")
            text = args[0] if args else ""
            tx = text.encode("utf-8")
            session.write(tx)
            timeout = float(args[1]) if len(args) > 1 else 5.0
            session.timeout = timeout
            rx = session.read(session.inWaiting() or 256)
            result["tx_text"] = text
            result["rx_text"] = rx.decode("utf-8", errors="replace")
            result["rx_bytes"] = len(rx)

        elif op == "close":
            if session:
                session.close()
            result["status"] = "closed"

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
