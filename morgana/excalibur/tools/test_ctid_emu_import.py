#!/usr/bin/env python3
"""Validate or explicitly import CTID packages. Never executes a Chain."""

from __future__ import annotations

import argparse
import json
import os
import re
import ssl
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

CTID_DIR = Path(__file__).resolve().parent.parent / "ctid"
DEFAULT_URL = "https://localhost:8888/api/v2/scripts/import-package"
DEFAULT_KEY_FILE = Path(r"C:\ProgramData\Morgana\data\master.key")
VALID_EXECUTORS = {"powershell", "cmd", "bash", "python"}
VALID_PLATFORMS = {"windows", "linux", "macos", "all"}
VALID_NODE_TYPES = {"script", "if_else"}
VALID_FIELDS = {"stdout", "stderr", "exit_code", "state"}
VALID_OPERATORS = {"contains", "not_contains", "equals", "not_equals", "exists", "not_exists"}
PLACEHOLDER = re.compile(r"#\{([^{}]+)\}")
REMOTE_URL = re.compile(r"https?://", re.I)
IPV4 = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
LITERAL_CREDENTIAL = re.compile(r"(?:/p:|--password\b|-password\b|password\s*=)\s*['\"]?[^#\s'\"]+", re.I)
UNSAFE_RUNTIME = re.compile(r"/file/download|\bsandcat\b|\bcaldera\b|\bimplant\b|\bexec-background\b", re.I)


def package_paths() -> list[Path]:
    return sorted(CTID_DIR.glob("**/ctid-*.json"))


def read_package(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: package root must be an object")
    return value


def validate_flow(flow: Any, script_names: set[str]) -> list[str]:
    errors: list[str] = []
    ids: set[str] = set()
    step_refs: list[str] = []
    count = 0

    def walk(nodes: Any, depth: int) -> None:
        nonlocal count
        if not isinstance(nodes, list):
            errors.append("flow branches must be arrays")
            return
        if depth > 20:
            errors.append("flow exceeds maximum nesting depth")
            return
        for node in nodes:
            if not isinstance(node, dict):
                errors.append("flow node must be an object")
                continue
            count += 1
            node_id = str(node.get("id") or "")
            if not node_id:
                errors.append("flow node is missing id")
            elif node_id in ids:
                errors.append(f"duplicate flow node id: {node_id}")
            ids.add(node_id)
            node_type = node.get("type", "script")
            if node_type not in VALID_NODE_TYPES:
                errors.append(f"unsupported flow node type: {node_type}")
                continue
            if node_type == "script":
                reference = str(node.get("script_ref") or "")
                if reference not in script_names:
                    errors.append(f"unknown script_ref: {reference}")
                if node.get("script_id"):
                    errors.append("published flow contains database script_id")
                continue
            condition = node.get("condition")
            contains = node.get("contains")
            if condition is not None:
                if not isinstance(condition, dict):
                    errors.append("condition must be an object")
                else:
                    if condition.get("field") not in VALID_FIELDS:
                        errors.append("invalid condition field")
                    if condition.get("operator") not in VALID_OPERATORS:
                        errors.append("invalid condition operator")
                    if condition.get("source", "previous_step") == "step":
                        step_refs.append(str(condition.get("step_ref") or ""))
            elif not isinstance(contains, str) or not contains.strip():
                errors.append("if_else is missing condition")
            walk(node.get("if_nodes", []), depth + 1)
            walk(node.get("else_nodes", []), depth + 1)

    if not isinstance(flow, dict):
        return ["flow must be an object"]
    walk(flow.get("nodes"), 1)
    if count > 500:
        errors.append("flow exceeds 500 nodes")
    for reference in step_refs:
        if reference not in ids:
            errors.append(f"unknown condition step_ref: {reference}")
    return errors


def validate_package(package: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    package_id = str(package.get("package_id") or "")
    if not package_id.startswith("ctid-"):
        errors.append("invalid CTID package_id")
    if package.get("provider") != "mitre-ctid":
        errors.append("provider must be mitre-ctid")
    if package.get("plan_type") not in {"full-emulation", "micro-emulation"}:
        errors.append("invalid plan_type")
    scripts = package.get("scripts")
    chains = package.get("chains")
    if not isinstance(scripts, list) or not scripts:
        return errors + ["scripts must be a non-empty array"]
    if not isinstance(chains, list) or not chains:
        return errors + ["chains must be a non-empty array"]
    names = {str(script.get("name") or "") for script in scripts if isinstance(script, dict)}
    if len(names) != len(scripts) or "" in names:
        errors.append("script names must be non-empty and unique")
    for script in scripts:
        if script.get("executor") not in VALID_EXECUTORS:
            errors.append(f"{script.get('name')}: invalid executor")
        if script.get("platform") not in VALID_PLATFORMS:
            errors.append(f"{script.get('name')}: invalid platform")
        if not str(script.get("command") or "").strip():
            errors.append(f"{script.get('name')}: command is blank")
        if not isinstance(script.get("source_metadata"), dict):
            errors.append(f"{script.get('name')}: source_metadata missing")
        command_text = f"{script.get('command') or ''}\n{script.get('cleanup_command') or ''}"
        if "Manual CTID procedure" in command_text:
            errors.append(f"{script.get('name')}: manual placeholder command is forbidden")
        if REMOTE_URL.search(command_text):
            errors.append(f"{script.get('name')}: automatic command contains hard-coded URL")
        hardcoded_ips = [value for value in IPV4.findall(command_text) if not value.startswith("127.")]
        if hardcoded_ips:
            errors.append(f"{script.get('name')}: automatic command contains hard-coded IP")
        if LITERAL_CREDENTIAL.search(command_text):
            errors.append(f"{script.get('name')}: automatic command contains literal credential-like value")
        if UNSAFE_RUNTIME.search(command_text):
            errors.append(f"{script.get('name')}: automatic command contains external runtime primitive")
        required_tags = set(script.get("required_tags", []))
        if set(PLACEHOLDER.findall(command_text)) != required_tags:
            errors.append(f"{script.get('name')}: required_tags do not match placeholders")
        metadata = script.get("source_metadata", {})
        if metadata.get("source_payloads") and metadata.get("conversion_status") != "simulated":
            errors.append(f"{script.get('name')}: source command retains payload dependency")
    for category in package.get("tag_categories", []):
        for tag in category.get("tags", []):
            if (tag.get("sensitive") or tag.get("parameter_class") == "connection") and (
                tag.get("default") or tag.get("example")
            ):
                errors.append(f"tag {tag.get('key')}: sensitive/target defaults are forbidden")
    chain_names: set[str] = set()
    for chain in chains:
        name = str(chain.get("name") or "")
        if not name or name in chain_names:
            errors.append("chain names must be non-empty and unique")
        chain_names.add(name)
        if not str(chain.get("description") or "").strip():
            errors.append(f"{name}: description missing")
        if not str(chain.get("objective") or "").strip():
            errors.append(f"{name}: objective missing")
        errors.extend(f"{name}: {error}" for error in validate_flow(chain.get("flow"), names))
    for field in ("source_procedure_count", "converted_procedure_count", "manual_procedure_count", "skipped_procedure_count"):
        if not isinstance(package.get(field), int) or package[field] < 0:
            errors.append(f"invalid completeness field: {field}")
    if package.get("manual_procedure_count") != 0:
        errors.append("CTID packages cannot contain manual procedures")
    return errors


def select_packages(arguments: argparse.Namespace) -> list[Path]:
    paths = package_paths()
    if arguments.plan:
        value = arguments.plan.lower()
        paths = [path for path in paths if value in path.stem.lower() or value in str(path.parent).lower()]
    if arguments.type:
        segment = "full" if arguments.type == "full" else "micro"
        paths = [path for path in paths if segment in path.parts]
    if not paths:
        raise ValueError("no matching CTID packages")
    if arguments.all or arguments.list or arguments.validate_only or arguments.plan or arguments.type:
        return paths
    return paths[:1]


def get_api_key(url: str) -> str:
    configured = os.environ.get("MORGANA_API_KEY", "").strip()
    if configured:
        return configured
    host = (urllib.parse.urlparse(url).hostname or "").lower()
    if host not in {"localhost", "127.0.0.1", "::1"}:
        raise ValueError("refusing to send the local Morgana master key to a non-loopback URL")
    return DEFAULT_KEY_FILE.read_text(encoding="utf-8").strip()


def import_package(path: Path, url: str, api_key: str) -> bool:
    package = read_package(path)
    errors = validate_package(package)
    if errors:
        print(f"[FAIL] {path.name}: {len(errors)} validation errors")
        return False
    request = urllib.request.Request(
        url,
        data=json.dumps(package).encode("utf-8"),
        method="POST",
        headers={"KEY": api_key, "Content-Type": "application/json"},
    )
    context = ssl.create_default_context()
    if (urllib.parse.urlparse(url).hostname or "").lower() in {"localhost", "127.0.0.1", "::1"}:
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
    try:
        with urllib.request.urlopen(request, context=context, timeout=120) as response:
            result = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, json.JSONDecodeError) as exc:
        print(f"[FAIL] {path.name}: {exc}")
        return False
    print(f"[OK] {path.name}: imported={result.get('imported', 0)} chains={result.get('chains_imported', 0)}")
    return bool(result.get("success"))


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate or import CTID Morgana packages")
    parser.add_argument("--list", action="store_true")
    parser.add_argument("--plan")
    parser.add_argument("--type", choices=["full", "micro"])
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--validate-only", action="store_true")
    parser.add_argument("--url", default=DEFAULT_URL)
    arguments = parser.parse_args()
    try:
        paths = select_packages(arguments)
        if arguments.list or arguments.validate_only:
            invalid = 0
            for path in paths:
                package = read_package(path)
                errors = validate_package(package)
                status = "OK" if not errors else f"FAIL ({len(errors)})"
                print(
                    f"[{status}] {package.get('package_id')} type={package.get('plan_type')} "
                    f"scripts={len(package.get('scripts', []))} chains={len(package.get('chains', []))} "
                    f"automated={package.get('converted_procedure_count', 0)}/"
                    f"{package.get('source_procedure_count', 0)} manual={package.get('manual_procedure_count', 0)} "
                    f"assets={len(package.get('assets', []))}"
                )
                for error in errors[:20]:
                    print(f"  - {error}")
                invalid += bool(errors)
            return 1 if invalid else 0
        api_key = get_api_key(arguments.url)
        return 1 if any(not import_package(path, arguments.url, api_key) for path in paths) else 0
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"[ERROR] {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
