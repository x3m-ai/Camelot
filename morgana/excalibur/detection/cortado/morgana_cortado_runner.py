#!/usr/bin/env python3
"""
morgana_cortado_runner.py — Morgana non-interactive Cortado RTA execution wrapper.

Loads the pinned Cortado wheel from the Agent's asset cache, discovers the
requested CodeRta by name, verifies OS support, and executes the RTA code
function. Returns a MORGANA_RESULT_METADATA= line on stdout for the
Morgana result parser.

Usage:
    python morgana_cortado_runner.py --runtime <extracted-wheel-dir> \
        --module <source-module> --rta <rta-name> [--platform <os>]
"""
from __future__ import annotations

import argparse
import importlib
import importlib.util
import json
import logging
import os
import platform
import sys
import time

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger(__name__)

MORGANA_RESULT_PREFIX = "MORGANA_RESULT_METADATA="


def _detect_platform() -> str:
    s = platform.system().lower()
    if s == "windows": return "windows"
    if s == "darwin": return "macos"
    return "linux"


def _emit_result(result: dict) -> None:
    print(f"{MORGANA_RESULT_PREFIX}{json.dumps(result, separators=(',', ':'))}", flush=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="Morgana Cortado RTA runner")
    parser.add_argument("--runtime", required=True,
                        help="Path to extracted Cortado wheel directory (contains cortado/ package)")
    parser.add_argument("--module", required=True,
                        help="Source module name, e.g. cortado.rtas.accepted_default_telnet_port_connection")
    parser.add_argument("--rta", required=True,
                        help="RTA name (as registered, e.g. accepted_default_telnet_port_connection)")
    parser.add_argument("--platform", default=None,
                        help="Override OS platform check (windows/linux/macos)")
    parser.add_argument("--rta-id", default="",
                        help="RTA UUID for result metadata")
    parser.add_argument("--techniques", default="",
                        help="Comma-separated ATT&CK techniques for result")
    parser.add_argument("--endpoint-rules", default="",
                        help="JSON array of expected endpoint rules")
    parser.add_argument("--siem-rules", default="",
                        help="JSON array of expected SIEM rules")
    args = parser.parse_args()

    current_platform = args.platform or _detect_platform()
    result = {
        "provider": "elastic-cortado",
        "rta_id": args.rta_id,
        "rta_name": args.rta,
        "rta_type": "code",
        "platform": current_platform,
        "status": "started",
        "duration_ms": 0,
        "expected_endpoint_rules": json.loads(args.endpoint_rules) if args.endpoint_rules else [],
        "expected_siem_rules": json.loads(args.siem_rules) if args.siem_rules else [],
        "techniques": [t for t in args.techniques.split(",") if t],
    }

    # Ensure the extracted wheel is on sys.path
    runtime_dir = args.runtime
    if runtime_dir not in sys.path:
        sys.path.insert(0, runtime_dir)

    # Verify Cortado is importable
    try:
        import cortado.rtas as _rtas_pkg
    except ImportError as exc:
        result["status"] = "init_failed"
        result["error"] = f"Cannot import cortado.rtas from {runtime_dir}: {exc}"
        log.error(result["error"])
        _emit_result(result)
        return 2

    # Import the specific RTA module
    try:
        module = importlib.import_module(args.module)
    except Exception as exc:
        result["status"] = "module_load_failed"
        result["error"] = f"Cannot import module {args.module}: {exc}"
        log.error(result["error"])
        _emit_result(result)
        return 2

    # Find the registered CodeRta
    from cortado.rtas import _REGISTRY  # noqa: internal
    rta_obj = None
    for key, obj in _REGISTRY.items():
        if getattr(obj, "name", None) == args.rta:
            rta_obj = obj
            break

    if rta_obj is None:
        # Try attribute lookup on module
        code_func = getattr(module, "main", None)
        if code_func is None:
            result["status"] = "rta_not_found"
            result["error"] = f"RTA '{args.rta}' not found in registry or module"
            log.error(result["error"])
            _emit_result(result)
            return 2
    else:
        # Check platform support
        supported = [str(p).lower() for p in getattr(rta_obj, "platforms", [])]
        if supported and current_platform not in supported:
            result["status"] = "platform_not_supported"
            result["error"] = f"RTA '{args.rta}' does not support {current_platform}. Supported: {supported}"
            log.warning(result["error"])
            _emit_result(result)
            return 3
        code_func = getattr(rta_obj, "code_func", None) or getattr(module, "main", None)

    if code_func is None:
        result["status"] = "no_executable"
        result["error"] = "No code_func or main() found"
        log.error(result["error"])
        _emit_result(result)
        return 2

    # Execute RTA
    log.info("[START] Cortado RTA: %s (platform=%s)", args.rta, current_platform)
    start_ms = time.time() * 1000
    try:
        code_func()
        result["status"] = "succeeded"
        log.info("[SUCCESS] RTA completed: %s", args.rta)
    except SystemExit as exc:
        result["status"] = "succeeded" if (exc.code or 0) == 0 else "failed"
        result["exit_code"] = exc.code
    except Exception as exc:
        result["status"] = "failed"
        result["error"] = str(exc)
        log.error("[ERROR] RTA failed: %s — %s", args.rta, exc)

    result["duration_ms"] = round(time.time() * 1000 - start_ms)
    log.info("[INFO] %s | %s | %dms", args.rta, result["status"], result["duration_ms"])
    _emit_result(result)
    return 0 if result["status"] == "succeeded" else 1


if __name__ == "__main__":
    sys.exit(main())
