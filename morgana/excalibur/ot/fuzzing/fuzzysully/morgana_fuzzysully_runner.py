#!/usr/bin/env python3
"""
morgana_fuzzysully_runner.py — Morgana non-interactive FuzzySully execution wrapper.

Runs a single FuzzySully fuzz profile bounded by case count and/or duration,
collects progress metrics, and emits a MORGANA_RESULT_METADATA= JSON line on exit.

Usage (called by Morgana Script bash command):
    python morgana_fuzzysully_runner.py [OPTIONS] <host> <port>

All options are documented in --help.
"""
from __future__ import annotations

import argparse
import json
import os
import signal
import sys
import time
from pathlib import Path

# ── version check ──────────────────────────────────────────────────────────────
if sys.version_info < (3, 10):
    print("[ERROR] FuzzySully requires Python >= 3.10", file=sys.stderr)
    sys.exit(2)

try:
    from fuzzysully import FuzzySully, OPCUAMode, OPCUASupportedPolicies
    from fuzzysully.fuzzer import OPCUAFuzzer
except ImportError as exc:
    print(f"[ERROR] fuzzysully not importable: {exc}", file=sys.stderr)
    sys.exit(2)


# ── helpers ────────────────────────────────────────────────────────────────────

_POLICY_MAP = {
    "none": OPCUASupportedPolicies.NONE,
    "None": OPCUASupportedPolicies.NONE,
    "basic256sha256": OPCUASupportedPolicies.BASIC_SHA,
    "Basic256Sha256": OPCUASupportedPolicies.BASIC_SHA,
}

_MODE_MAP = {
    "server": OPCUAMode.SERVER,
    "gds": OPCUAMode.GDS,
    "reverse": OPCUAMode.REVERSE_MODE,
}

_RESULT: dict = {}
_START_TIME: float = 0.0
_SESSION = None
_CANCELLED = False


def _emit_result(result: dict) -> None:
    """Write MORGANA_RESULT_METADATA= marker to stdout for Morgana parser."""
    print(f"MORGANA_RESULT_METADATA={json.dumps(result, separators=(',', ':'))}", flush=True)


def _signal_handler(sig, frame) -> None:
    global _CANCELLED
    _CANCELLED = True
    print("[INFO] Cancellation requested — stopping fuzz session", flush=True)
    if _SESSION is not None:
        try:
            # Fuzzowski Session does not expose a clean stop() — flag is checked in run loop
            pass
        except Exception:
            pass


def _validate_inputs(args: argparse.Namespace) -> None:
    if not args.host:
        print("[ERROR] --host is required", file=sys.stderr)
        sys.exit(2)
    if not (1 <= args.port <= 65535):
        print(f"[ERROR] --port must be 1-65535 (got {args.port})", file=sys.stderr)
        sys.exit(2)
    if args.mode not in _MODE_MAP:
        print(f"[ERROR] --mode must be one of: {list(_MODE_MAP.keys())}", file=sys.stderr)
        sys.exit(2)
    policy_key = args.policy.lower() if args.policy else "none"
    if policy_key not in {k.lower() for k in _POLICY_MAP}:
        print(f"[ERROR] --policy must be None or Basic256Sha256", file=sys.stderr)
        sys.exit(2)
    if args.max_cases is not None and args.max_cases < 1:
        print("[ERROR] --max-cases must be >= 1", file=sys.stderr)
        sys.exit(2)
    if args.case_start is not None and args.case_start < 1:
        print("[ERROR] --case-start must be >= 1", file=sys.stderr)
        sys.exit(2)
    if args.max_duration is not None and args.max_duration < 1:
        print("[ERROR] --max-duration must be >= 1 second", file=sys.stderr)
        sys.exit(2)
    # Policy/mode compatibility
    mode = args.mode
    policy_norm = args.policy.lower() if args.policy else "none"
    if mode == "reverse" and policy_norm != "none":
        print("[ERROR] Reverse mode only supports None security policy", file=sys.stderr)
        sys.exit(2)
    if mode == "gds" and policy_norm == "none":
        print("[ERROR] GDS mode requires Basic256Sha256 security policy", file=sys.stderr)
        sys.exit(2)
    if mode == "server" and policy_norm != "none":
        if args.function and args.function.lower() in ("hello", "secure_channel", "session"):
            print(f"[ERROR] Function '{args.function}' is not supported with Basic256Sha256 policy", file=sys.stderr)
            sys.exit(2)
    # Cert requirements
    if policy_norm != "none":
        if not args.client_cert:
            print("[ERROR] --client-cert is required for Basic256Sha256 policy", file=sys.stderr)
            sys.exit(2)
        if not args.private_key:
            print("[ERROR] --private-key is required for Basic256Sha256 policy", file=sys.stderr)
            sys.exit(2)
        if not Path(args.client_cert).exists():
            print(f"[ERROR] client-cert not found: {args.client_cert}", file=sys.stderr)
            sys.exit(2)
        if not Path(args.private_key).exists():
            print(f"[ERROR] private-key not found: {args.private_key}", file=sys.stderr)
            sys.exit(2)


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="morgana_fuzzysully_runner",
        description="Non-interactive FuzzySully wrapper for Morgana.",
    )
    # Target
    p.add_argument("--host", required=True, help="OPC UA target hostname or IP")
    p.add_argument("--port", type=int, default=4840, help="OPC UA target TCP port (1-65535)")
    p.add_argument("--path", default="", help="OPC UA endpoint path (e.g. /OPCUA/SimulationServer)")
    # Mode / function
    p.add_argument("--mode", default="server", choices=["server", "gds", "reverse"],
                   help="FuzzySully mode: server | gds | reverse")
    p.add_argument("--function", default=None,
                   help="Specific upstream function to fuzz (default: all for mode)")
    # Security
    p.add_argument("--policy", default="None",
                   help="Security policy: None | Basic256Sha256")
    p.add_argument("--encrypt", action="store_true",
                   help="Use SignAndEncrypt (requires Basic256Sha256)")
    p.add_argument("--client-cert", default=None,
                   help="Path to client certificate PEM (required for Basic256Sha256)")
    p.add_argument("--private-key", default=None,
                   help="Path to private key PEM (required for Basic256Sha256)")
    p.add_argument("--private-key-password", default=None,
                   help="Private key password (avoid on command line; use env FUZZ_KEY_PWD)")
    p.add_argument("--app-uri", default="urn:morgana:fuzzysully:client",
                   help="OPC UA application URI")
    p.add_argument("--username", default=None, help="OPC UA username (GDS auth)")
    p.add_argument("--password", default=None, help="OPC UA password (use env FUZZ_PASSWORD)")
    # Connection tuning
    p.add_argument("--bind-port", type=int, default=4840, help="Local bind port for reverse mode")
    p.add_argument("--send-timeout", type=float, default=5.0, help="Send timeout (seconds)")
    p.add_argument("--recv-timeout", type=float, default=5.0, help="Receive timeout (seconds)")
    p.add_argument("--sleep-time", type=float, default=0.0, help="Sleep between requests (seconds)")
    p.add_argument("--new-conns", action="store_true", help="Open new connection per request")
    p.add_argument("--transmit-full-path", action="store_true", help="Transmit full path in Fuzzowski")
    p.add_argument("--no-recv", action="store_true", help="Disable receive after request")
    p.add_argument("--no-recv-fuzz", action="store_true", help="Disable receive during fuzz")
    p.add_argument("--check-recv", action="store_true", help="Check received data validity")
    p.add_argument("--threshold-request", type=int, default=9999, help="Crash threshold per request")
    p.add_argument("--threshold-element", type=int, default=9999, help="Crash threshold per element")
    # Bounding
    p.add_argument("--case-start", type=int, default=1,
                   help="First fuzz case index to execute (1-based)")
    p.add_argument("--max-cases", type=int, default=None,
                   help="Maximum number of fuzz cases to execute")
    p.add_argument("--max-duration", type=int, default=None,
                   help="Maximum execution duration in seconds")
    # Output
    p.add_argument("--log-dir", default="/tmp",
                   help="Directory for session logs (default: /tmp)")
    p.add_argument("--test-id", default=None,
                   help="Morgana test ID for log filename correlation")
    p.add_argument("--list-functions", action="store_true",
                   help="Print available functions for the given mode and exit")
    return p


def main() -> int:
    global _SESSION, _START_TIME, _CANCELLED

    parser = _build_parser()
    args = parser.parse_args()

    # Allow sensitive values from environment
    if not args.private_key_password:
        args.private_key_password = os.environ.get("FUZZ_KEY_PWD")
    if not args.password:
        args.password = os.environ.get("FUZZ_PASSWORD")

    mode_enum = _MODE_MAP.get(args.mode, OPCUAMode.SERVER)

    if args.list_functions:
        funcs = FuzzySully.list_available_functions(mode_enum)
        print(f"Available functions for mode '{args.mode}':")
        for f in sorted(funcs):
            print(f"  {f}")
        return 0

    _validate_inputs(args)

    policy_norm = args.policy.lower()
    policy_enum = _POLICY_MAP.get(args.policy, OPCUASupportedPolicies.NONE)
    if policy_norm not in ("none",):
        policy_enum = OPCUASupportedPolicies.BASIC_SHA

    fuzz_requests = [args.function] if args.function else None

    # Discover available functions and total mutation estimate
    all_funcs = FuzzySully.list_available_functions(mode_enum)
    requested_funcs = [args.function] if args.function else list(all_funcs)

    print(f"[INFO] Mode: {args.mode} | Policy: {args.policy} | Function(s): {requested_funcs}", flush=True)

    # Register signal handlers for clean cancellation
    signal.signal(signal.SIGTERM, _signal_handler)
    signal.signal(signal.SIGINT, _signal_handler)

    # Build result skeleton
    result = {
        "provider": "anssi-fuzzysully",
        "mode": args.mode,
        "function": args.function or "all",
        "security_policy": args.policy,
        "encrypt": args.encrypt,
        "requested_case_start": args.case_start,
        "requested_max_cases": args.max_cases,
        "requested_max_duration": args.max_duration,
        "total_cases_available": None,
        "cases_attempted": 0,
        "cases_completed": 0,
        "faults": 0,
        "connection_failures": 0,
        "timeouts": 0,
        "crash_candidates": 0,
        "threshold_skips": 0,
        "duration_seconds": 0.0,
        "session_log": None,
        "status": "started",
    }

    _START_TIME = time.time()

    try:
        fuzzy = FuzzySully(
            mode=mode_enum,
            host=args.host,
            port=args.port,
            d_path=args.path,
            bind=args.bind_port,
            send_timeout=args.send_timeout,
            recv_timeout=args.recv_timeout,
            sleep_time=args.sleep_time,
            new_conns=args.new_conns,
            transmit_full_path=args.transmit_full_path,
            no_recv=args.no_recv,
            no_recv_fuzz=args.no_recv_fuzz,
            check_recv=args.check_recv,
            crash_threshold_request=args.threshold_request,
            crash_threshold_element=args.threshold_element,
            policy=policy_enum,
            client_cert_path=Path(args.client_cert) if args.client_cert else None,
            private_key_path=Path(args.private_key) if args.private_key else None,
            private_key_pwd=args.private_key_password,
            app_uri=args.app_uri,
            fuzz_requests=fuzz_requests,
            encrypt=args.encrypt,
            username=args.username,
            password=args.password,
        )
    except Exception as exc:
        result["status"] = "init_failed"
        result["error"] = str(exc)
        result["duration_seconds"] = round(time.time() - _START_TIME, 2)
        print(f"[ERROR] FuzzySully init failed: {exc}", file=sys.stderr)
        _emit_result(result)
        return 1

    _SESSION = fuzzy.session

    # Record session log path
    log_path = Path(args.log_dir) / fuzzy.session_filename
    result["session_log"] = str(log_path)

    # Discover total available cases
    try:
        total = fuzzy.session.num_mutations
        result["total_cases_available"] = total
        print(f"[INFO] Total available fuzz cases: {total}", flush=True)
    except Exception:
        total = None

    # Seek to start case if not 1
    if args.case_start and args.case_start > 1:
        try:
            print(f"[INFO] Seeking to case {args.case_start}...", flush=True)
            fuzzy.session.goto(args.case_start)
        except Exception as e:
            print(f"[WARN] Could not seek to case {args.case_start}: {e}", flush=True)

    # Execute bounded loop
    cases_run = 0
    faults = 0
    conn_failures = 0
    timeout_count = 0
    threshold_skips = 0

    print(f"[START] Beginning fuzz campaign (max_cases={args.max_cases}, max_duration={args.max_duration}s)", flush=True)

    try:
        while not _CANCELLED:
            # Duration bound
            if args.max_duration is not None:
                elapsed = time.time() - _START_TIME
                if elapsed >= args.max_duration:
                    print(f"[INFO] Max duration {args.max_duration}s reached after {cases_run} cases", flush=True)
                    result["status"] = "duration_limit"
                    break

            # Case count bound
            if args.max_cases is not None and cases_run >= args.max_cases:
                print(f"[INFO] Max cases {args.max_cases} reached", flush=True)
                result["status"] = "case_limit"
                break

            # Run one case
            try:
                ran = fuzzy.session.run()
                if ran is False:
                    # Session exhausted
                    result["status"] = "completed"
                    break
                cases_run += 1
                result["cases_attempted"] = cases_run

                # Poll session stats
                try:
                    if hasattr(fuzzy.session, "crashes"):
                        c = getattr(fuzzy.session, "crashes", 0)
                        if isinstance(c, (int, float)):
                            result["faults"] = c
                        elif hasattr(c, "__len__"):
                            result["faults"] = len(c)
                    if hasattr(fuzzy.session, "total_num_mutations"):
                        result["total_cases_available"] = fuzzy.session.total_num_mutations
                except Exception:
                    pass

                # Progress print every 100 cases
                if cases_run % 100 == 0:
                    elapsed = round(time.time() - _START_TIME, 1)
                    print(f"[*] Progress: case {cases_run} | elapsed {elapsed}s | faults {result['faults']}", flush=True)

            except KeyboardInterrupt:
                _CANCELLED = True
                break
            except ConnectionRefusedError:
                conn_failures += 1
                result["connection_failures"] = conn_failures
                print(f"[WARN] Connection refused at case {cases_run + 1}", flush=True)
                time.sleep(1.0)
                if conn_failures >= 5:
                    print("[ERROR] Too many connection failures — aborting", file=sys.stderr)
                    result["status"] = "connection_failed"
                    break
            except TimeoutError:
                timeout_count += 1
                result["timeouts"] = timeout_count
                cases_run += 1
            except Exception as exc:
                err_str = str(exc)
                if "threshold" in err_str.lower():
                    threshold_skips += 1
                    result["threshold_skips"] = threshold_skips
                else:
                    faults += 1
                    result["faults"] = faults
                    if "crash" in err_str.lower() or "exception" in err_str.lower():
                        result["crash_candidates"] = result.get("crash_candidates", 0) + 1
                cases_run += 1
        else:
            if not _CANCELLED:
                result["status"] = "completed"

        if _CANCELLED:
            result["status"] = "cancelled"

    except Exception as exc:
        result["status"] = "runtime_error"
        result["error"] = str(exc)
        print(f"[ERROR] Runtime error: {exc}", file=sys.stderr)

    result["cases_completed"] = cases_run
    result["cases_attempted"] = cases_run
    result["faults"] = faults if faults > result.get("faults", 0) else result.get("faults", 0)
    result["connection_failures"] = conn_failures
    result["timeouts"] = timeout_count
    result["threshold_skips"] = threshold_skips
    result["duration_seconds"] = round(time.time() - _START_TIME, 2)

    # Final summary print
    print(f"[SUCCESS] Campaign complete: {cases_run} cases | {result['faults']} faults | "
          f"{conn_failures} conn_failures | {timeout_count} timeouts | "
          f"{result.get('crash_candidates', 0)} crash_candidates | "
          f"{result['duration_seconds']}s", flush=True)

    _emit_result(result)
    return 0


if __name__ == "__main__":
    sys.exit(main())
