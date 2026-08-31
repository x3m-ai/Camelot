#!/usr/bin/env python3
"""Generic drozer runner for Morgana Mobile Lab.

Launches the pinned isolated drozer runtime non-interactively:

    drozer console connect <serial> --no-color --no-password -c "run <fqmn> <args>"

with an ADB forward on the drozer default port (tcp:31415 -> tcp:31415) when
ADB is available. Captures stdout/stderr with bounded output, enforces a
timeout, and normalizes the result into a JSON marker line:

    MORGANA_RESULT_METADATA={"operation":"drozer_module", ...}

No interactive console screen-scraping: the `-c` one-command path is used.

Usage (stdlib-only; executed by the Morgana `python` executor):

    from morgana_drozer_runner import run_drozer_module
    result = run_drozer_module(
        drozer_bin=..., runtime_dir=..., serial=..., fqmn=...,
        args=[...], timeout=120.0,
    )
"""
from __future__ import annotations

import json
import os
import shlex
import subprocess
import sys
import time

MAX_STDOUT_BYTES = 200 * 1024   # 200 KB bounded capture
MAX_STDERR_BYTES = 200 * 1024
DROZER_PORT = 31415


def _find_drozer(runtime_dir: str) -> str:
    """Locate the drozer console entry point inside the isolated runtime."""
    candidates = []
    if runtime_dir:
        # Windows venv Scripts, POSIX venv bin
        candidates += [
            os.path.join(runtime_dir, "Scripts", "drozer.exe"),
            os.path.join(runtime_dir, "Scripts", "drozer"),
            os.path.join(runtime_dir, "bin", "drozer"),
            os.path.join(runtime_dir, "drozer"),
        ]
    # fall back to PATH
    for cand in candidates:
        if cand and os.path.isfile(cand):
            return cand
    # PATH lookup (no shell)
    for directory in os.environ.get("PATH", "").split(os.pathsep):
        cand = os.path.join(directory, "drozer.exe" if os.name == "nt" else "drozer")
        if os.path.isfile(cand):
            return cand
    return "drozer"


def _run(cmd: list, timeout: float) -> dict:
    """Run a subprocess with bounded capture and a hard timeout."""
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return {
            "exit_code": proc.returncode,
            "stdout": (proc.stdout or "")[:MAX_STDOUT_BYTES],
            "stderr": (proc.stderr or "")[:MAX_STDERR_BYTES],
        }
    except subprocess.TimeoutExpired:
        return {"exit_code": -1, "stdout": "", "stderr": "drozer execution timed out"}
    except FileNotFoundError as exc:
        return {"exit_code": -2, "stdout": "", "stderr": f"drozer binary not found: {exc}"}
    except Exception as exc:  # noqa: BLE001
        return {"exit_code": -3, "stdout": "", "stderr": f"drozer execution failed: {exc}"}


def _safe_arg(value: str) -> str:
    """Serialize one module argument token (single token, no shell)."""
    return str(value or "").strip()


def run_drozer_module(
    fqmn: str,
    args: list,
    serial: str = "",
    runtime_dir: str = "",
    timeout: float = 180.0,
    forward_port: int = DROZER_PORT,
    connect_extra: list | None = None,
) -> dict:
    """Run one drozer module non-interactively and return a normalized result."""
    drozer = _find_drozer(runtime_dir)
    connect_extra = connect_extra or []

    # 1. Establish the ADB forward (tracked, best-effort; clean afterwards).
    forward_made = False
    adb = os.environ.get("MORGANA_ADB", "") or "adb"
    if serial and forward_port:
        fwd = _run([adb, "-s", serial, "forward", f"tcp:{forward_port}", f"tcp:{forward_port}"], 15.0)
        forward_made = fwd["exit_code"] == 0

    # 2. Build the console one-command invocation.
    connect_cmd = [drozer, "console", "connect"]
    if serial:
        connect_cmd.append(serial)
    connect_cmd += ["--no-color", "--no-password"]
    connect_cmd += connect_extra
    # drozer's embedded-server default port is 31415; ADB forward exposes it locally.
    run_args = [a for a in (_safe_arg(a) for a in args) if a]
    onecmd = "run " + fqmn
    if run_args:
        # do_run() re-shlexes the -c command, so quote tokens containing spaces.
        onecmd += " " + " ".join(shlex.quote(a) for a in run_args)
    connect_cmd += ["-c", onecmd]

    start = time.monotonic()
    res = _run(connect_cmd, timeout)
    duration_ms = int((time.monotonic() - start) * 1000)

    # 3. Clean up the tracked ADB forward.
    if forward_made:
        try:
            _run([adb, "-s", serial, "forward", "--remove", f"tcp:{forward_port}"], 10.0)
        except Exception:
            pass

    success = res["exit_code"] == 0 and "unknown module" not in res["stderr"] and "module not found" not in res["stderr"].lower()

    return {
        "operation": "drozer_module",
        "fqmn": fqmn,
        "args": run_args,
        "serial": serial or None,
        "success": success,
        "exit_code": res["exit_code"],
        "stdout": res["stdout"],
        "stderr": res["stderr"],
        "duration_ms": duration_ms,
        "forward_port": forward_port if forward_made else None,
    }


def main() -> int:
    """CLI entry: json-encoded args on stdin are not required; env-driven."""
    # Minimal CLI used only for direct debugging; the Morgana Scripts call the
    # module function via the generated `python -c` command.
    fqmn = os.environ.get("MORGANA_DROZER_FQMN", "")
    serial = os.environ.get("MORGANA_DROZER_SERIAL", "")
    runtime_dir = os.environ.get("MORGANA_DROZER_RUNTIME_DIR", "")
    timeout = float(os.environ.get("MORGANA_DROZER_TIMEOUT", "180"))
    args_json = os.environ.get("MORGANA_DROZER_ARGS", "[]")
    try:
        args = json.loads(args_json)
    except Exception:
        args = []
    result = run_drozer_module(fqmn=fqmn, args=args, serial=serial,
                               runtime_dir=runtime_dir, timeout=timeout)
    print("MORGANA_RESULT_METADATA=" + json.dumps(result))
    return 0 if result["success"] else 1


if __name__ == "__main__":
    sys.exit(main())
