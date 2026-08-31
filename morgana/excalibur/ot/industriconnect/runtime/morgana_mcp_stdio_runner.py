"""Generic MCP stdio runner.

Launches a pinned Python MCP server as a subprocess, performs an MCP
initialize + tools/list handshake, invokes a single named tool with structured
arguments, captures the structured result and stderr, enforces a timeout, and
terminates the child cleanly.

This is the shared runtime used by IndustriConnect Excalibur Scripts (Part A)
and, where needed, by the Industrial Lab health probes (Part B). It is
provider-agnostic: it speaks the Model Context Protocol JSON-RPC over stdio and
has no knowledge of any specific industrial protocol.

Usage:
    from core.mcp_stdio_runner import run_mcp_tool

    result = run_mcp_tool(
        command=["uv", "run", "modbus-mcp"],
        cwd="/path/to/MODBUS-Project/modbus-python",
        env={...},
        tool_name="read_register",
        arguments={"address": 0, "slave_id": 1},
        timeout=30.0,
    )

    result == {
        "success": bool,
        "tool": "read_register",
        "result": <tool result payload>,
        "error": <error string or None>,
        "stderr": <captured stderr>,
        "duration_ms": float,
        "exit_code": int | None,
    }
"""
from __future__ import annotations

import json
import logging
import os
import subprocess
import sys
import threading
import time
from queue import Empty, Queue
from typing import Any, Optional

log = logging.getLogger("morgana.mcp_stdio_runner")

# JSON-RPC 2.0 is newline-delimited on stdio for the MCP Python SDK.
_MAX_STDERR_BYTES = 1 << 20  # 1 MB bounded capture


class MCPRunnerError(RuntimeError):
    """Raised when the MCP handshake or tool invocation fails."""


def _read_message(line_queue: Queue, deadline: float) -> dict:
    """Wait for the next parseable JSON-RPC line from the stdout queue."""
    import json as _json
    from json import JSONDecodeError

    buf = b""
    while time.monotonic() < deadline:
        try:
            remaining = max(0.0, deadline - time.monotonic())
            chunk = line_queue.get(timeout=min(remaining, 0.2))
        except Empty:
            continue
        buf += chunk
        text = buf.decode("utf-8", errors="replace")
        idx = 0
        n = len(text)
        decoder = _json.JSONDecoder()
        while idx < n:
            if text[idx] in " \t\r\n":
                idx += 1
                continue
            try:
                obj, end = decoder.raw_decode(text, idx)
                return obj
            except JSONDecodeError:
                break
    raise MCPRunnerError("timed out waiting for MCP message")


def _stdout_reader(stream, queue: Queue) -> None:
    """Background line reader: push raw bytes chunks into the queue."""
    try:
        for line in iter(stream.readline, b""):
            queue.put(line)
    except Exception:  # pragma: no cover - best effort
        pass
    finally:
        queue.put(b"\n")  # EOF sentinel


def _drain_stderr(proc: subprocess.Popen, out: list) -> None:
    try:
        for line in iter(proc.stderr.readline, b""):
            if len(out) < _MAX_STDERR_BYTES:
                out.append(line)
    except Exception:  # pragma: no cover - best effort
        pass


def _build_request(method: str, request_id: int, params: dict) -> bytes:
    payload = {"jsonrpc": "2.0", "id": request_id, "method": method, "params": params}
    return (json.dumps(payload) + "\n").encode("utf-8")


def run_mcp_tool(
    command: list[str],
    cwd: str,
    tool_name: str,
    arguments: Optional[dict[str, Any]] = None,
    env: Optional[dict[str, str]] = None,
    timeout: float = 30.0,
    extra_env: Optional[dict[str, str]] = None,
) -> dict[str, Any]:
    """Run one MCP tool via a stdio MCP server subprocess.

    Args:
        command: argv used to launch the MCP server (e.g. ["uv","run","modbus-mcp"]).
        cwd: working directory for the child (the protocol project dir).
        tool_name: the MCP tool to invoke.
        arguments: structured arguments for the tool.
        env: full environment override (optional); merged over os.environ if extra_env.
        timeout: total wall-clock budget for the whole handshake + call.

    Returns a normalized result envelope (see module docstring).
    """
    arguments = arguments or {}
    full_env = dict(os.environ)
    if env:
        full_env.update(env)
    if extra_env:
        full_env.update(extra_env)

    started = time.monotonic()
    result: dict[str, Any] = {
        "success": False,
        "tool": tool_name,
        "result": None,
        "error": None,
        "stderr": "",
        "duration_ms": 0.0,
        "exit_code": None,
    }

    # Drop PYTHONIOENCODING/pipes that can corrupt JSON on Windows.
    full_env.setdefault("PYTHONUNBUFFERED", "1")
    full_env.setdefault("PYTHONIOENCODING", "utf-8")

    try:
        proc = subprocess.Popen(
            command,
            cwd=cwd,
            env=full_env,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except FileNotFoundError as exc:
        result["error"] = f"MCP server launcher not found: {exc}"
        result["duration_ms"] = (time.monotonic() - started) * 1000.0
        return result
    except Exception as exc:  # pragma: no cover - defensive
        result["error"] = f"Failed to launch MCP server: {exc}"
        result["duration_ms"] = (time.monotonic() - started) * 1000.0
        return result

    stderr_chunks: list = []
    stderr_thread = threading.Thread(target=_drain_stderr, args=(proc, stderr_chunks), daemon=True)
    stderr_thread.start()

    line_queue: Queue = Queue()
    stdout_thread = threading.Thread(target=_stdout_reader, args=(proc.stdout, line_queue), daemon=True)
    stdout_thread.start()

    deadline = time.monotonic() + timeout
    request_id = 1
    try:
        # 1. initialize
        init_req = _build_request(
            "initialize",
            request_id,
            {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "morgana-mcp-stdio-runner", "version": "1.0.0"},
            },
        )
        proc.stdin.write(init_req)
        proc.stdin.flush()
        _read_message(line_queue, deadline)
        request_id += 1

        # 2. notifications/initialized (fire-and-forget)
        try:
            notif = {"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}}
            proc.stdin.write((json.dumps(notif) + "\n").encode("utf-8"))
            proc.stdin.flush()
        except Exception:
            pass

        # 3. tools/list
        list_req = _build_request("tools/list", request_id, {})
        proc.stdin.write(list_req)
        proc.stdin.flush()
        list_resp = _read_message(line_queue, deadline)
        request_id += 1
        tool_names = {
            t.get("name")
            for t in (list_resp.get("result", {}) or {}).get("tools", [])
            if isinstance(t, dict)
        }
        if tool_names and tool_name not in tool_names:
            result["error"] = (
                f"tool '{tool_name}' not found; server exposes "
                f"{sorted(tool_names)[:50]}"
            )
            _terminate(proc)
            return result

        # 4. tools/call
        call_req = _build_request(
            "tools/call",
            request_id,
            {"name": tool_name, "arguments": arguments},
        )
        proc.stdin.write(call_req)
        proc.stdin.flush()
        call_resp = _read_message(line_queue, deadline)

        if "error" in call_resp:
            result["error"] = _stringify(call_resp["error"])
        else:
            raw = call_resp.get("result", {})
            result["result"] = raw
            # FastMCP puts the tool return value in .content[0].text
            result["success"] = True
            result["parsed"] = _extract_text_content(raw)

    except MCPRunnerError as exc:
        result["error"] = str(exc)
    except BrokenPipeError:
        result["error"] = "MCP server closed stdin (likely missing runtime dependency)"
    except Exception as exc:  # pragma: no cover - defensive
        result["error"] = f"{type(exc).__name__}: {exc}"
    finally:
        _terminate(proc)
        stderr_thread.join(timeout=1.0)
        try:
            result["stderr"] = b"".join(stderr_chunks).decode("utf-8", errors="replace")
        except Exception:
            result["stderr"] = ""
        result["duration_ms"] = (time.monotonic() - started) * 1000.0

    return result


def _extract_text_content(raw: dict) -> Optional[Any]:
    """Pull the human/structured tool return value out of an MCP CallToolResult."""
    if not isinstance(raw, dict):
        return raw
    content = raw.get("content")
    if not isinstance(content, list):
        return raw
    for item in content:
        if isinstance(item, dict) and item.get("type") == "text":
            text = item.get("text", "")
            try:
                return json.loads(text)
            except Exception:
                return text
    return raw


def _stringify(value: Any) -> str:
    if isinstance(value, str):
        return value
    try:
        return json.dumps(value)
    except Exception:
        return str(value)


def _terminate(proc: subprocess.Popen) -> None:
    """Terminate the child process tree as cleanly as possible."""
    if proc is None or proc.poll() is not None:
        return
    try:
        proc.terminate()
    except Exception:
        pass
    try:
        proc.wait(timeout=3.0)
    except Exception:
        try:
            proc.kill()
        except Exception:
            pass
        try:
            proc.wait(timeout=2.0)
        except Exception:
            pass
