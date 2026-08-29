#!/usr/bin/env python3
"""
cortado_ast.py — AST-based discovery of all Cortado RTAs.

Parses every cortado/rtas/*.py (excluding __init__.py) to extract
register_code_rta and register_hash_rta decorator calls without
importing the modules (cross-platform safe).
"""
from __future__ import annotations

import ast
import re
from pathlib import Path
from typing import Optional

CORTADO_RELEASE = "dev-release-0.1.0+f1dd8bc1"
CORTADO_VERSION = "0.1.0+f1dd8bc1"
CORTADO_COMMIT  = "f1dd8bc1883a399c4990f2f4a63d7a3d26cdd89e"
CORTADO_WHEEL   = "cortado-0.1.0+f1dd8bc1-py3-none-any.whl"
CORTADO_WHEEL_SHA256 = "38fe8fce2f0af631be7df111ac19b872561e85bb57e634f6236a9fa2e3198836"
CORTADO_WHEEL_SIZE   = 5089715
CORTADO_WHEEL_URL    = (
    "https://github.com/elastic/cortado/releases/download/"
    "dev-release-0.1.0%2Bf1dd8bc1/cortado-0.1.0%2Bf1dd8bc1-py3-none-any.whl"
)
CORTADO_LICENSE = "Elastic License 2.0"
CORTADO_REPO    = "elastic/cortado"
CORTADO_PYTHON  = ">=3.12"


def _extract_str(node) -> Optional[str]:
    """Extract string value from AST node."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def _extract_list_of_str(node) -> list[str]:
    """Extract list of string constants."""
    if not isinstance(node, ast.List):
        return []
    result = []
    for elt in node.elts:
        s = _extract_str(elt)
        if s:
            result.append(s)
        elif isinstance(elt, ast.Attribute):
            # OSType.WINDOWS etc.
            result.append(elt.attr.lower())
    return result


def _extract_rule_metadata(node) -> list[dict]:
    """Extract list of RuleMetadata(id=..., name=...) calls."""
    if not isinstance(node, ast.List):
        return []
    rules = []
    for elt in node.elts:
        if not isinstance(elt, ast.Call):
            continue
        rule = {}
        for kw in elt.keywords:
            v = _extract_str(kw.value)
            if v and kw.arg in ("id", "name"):
                rule[kw.arg] = v
        if rule:
            rules.append(rule)
    return rules


def _extract_platforms(node) -> list[str]:
    """Extract platforms list, normalising OSType.X to 'x'."""
    if not isinstance(node, ast.List):
        return []
    result = []
    for elt in node.elts:
        if isinstance(elt, ast.Attribute):
            result.append(elt.attr.lower())
        elif isinstance(elt, ast.Constant):
            result.append(str(elt.value).lower())
    return result


def _extract_ancillary_files(node) -> list[str]:
    """Extract ancillary_files list; elements may be Name refs."""
    if not isinstance(node, ast.List):
        return []
    files = []
    for elt in node.elts:
        if isinstance(elt, ast.Constant):
            files.append(str(elt.value))
        elif isinstance(elt, ast.Name):
            files.append(elt.id)  # variable name like SHIM_FILE
    return files


def _parse_decorator_call(call: ast.Call) -> dict:
    """Extract all keyword arguments from a register_*_rta() call."""
    result = {
        "id": None, "name": None,
        "platforms": [], "endpoint_rules": [], "siem_rules": [],
        "techniques": [], "ancillary_files": [], "sample_hash": None,
    }
    for kw in call.keywords:
        arg = kw.arg
        val = kw.value
        if arg == "id":
            result["id"] = _extract_str(val)
        elif arg == "name":
            result["name"] = _extract_str(val)
        elif arg == "platforms":
            result["platforms"] = _extract_platforms(val)
        elif arg == "endpoint_rules":
            result["endpoint_rules"] = _extract_rule_metadata(val)
        elif arg == "siem_rules":
            result["siem_rules"] = _extract_rule_metadata(val)
        elif arg == "techniques":
            result["techniques"] = _extract_list_of_str(val)
        elif arg == "ancillary_files":
            result["ancillary_files"] = _extract_ancillary_files(val)
        elif arg == "sample_hash":
            result["sample_hash"] = _extract_str(val)
    return result


def _extract_header_comments(source: str) -> dict:
    """Extract # Name: / # Description: header comments."""
    header = {}
    for line in source.splitlines()[:20]:
        line = line.strip()
        if line.startswith("# Name:"):
            header["name_comment"] = line[7:].strip()
        elif line.startswith("# Description:"):
            header["description"] = line[15:].strip()
        elif line.startswith("# RTA:"):
            header["rta_file"] = line[6:].strip()
    return header


def _extract_func_docstring(source: str, func_name: str = "main") -> Optional[str]:
    """Extract docstring from the def main() function."""
    try:
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == func_name:
                return ast.get_docstring(node)
    except SyntaxError:
        pass
    return None


def parse_rta_file(path: Path) -> list[dict]:
    """Parse one RTA file and return list of RTA metadata dicts (usually 1).

    Handles two patterns:
    1. Decorator: @register_code_rta(...) on def main()
    2. Direct call: register_hash_rta(...) as top-level statement
    """
    try:
        source = path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return []

    header = _extract_header_comments(source)
    func_doc = _extract_func_docstring(source)

    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        return [{"_parse_error": str(exc), "_path": str(path)}]

    rtas = []

    def _process_call(call: ast.Call, rta_type: str) -> None:
        meta = _parse_decorator_call(call)
        meta["rta_type"] = rta_type
        meta["source_path"] = str(path.name)
        meta["source_module"] = f"cortado.rtas.{path.stem}"
        desc = header.get("description") or func_doc or ""
        if not desc and meta.get("name"):
            desc = meta["name"].replace("_", " ").title()
        meta["description"] = desc
        meta["name_comment"] = header.get("name_comment", "")
        rtas.append(meta)

    # Pattern 1: @register_code_rta(...) decorator on function
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef):
            continue
        for decorator in node.decorator_list:
            if not isinstance(decorator, ast.Call):
                continue
            func = decorator.func
            dname = func.id if isinstance(func, ast.Name) else (func.attr if isinstance(func, ast.Attribute) else None)
            if dname == "register_code_rta":
                _process_call(decorator, "code")
            elif dname == "register_hash_rta":
                _process_call(decorator, "hash")

    # Pattern 2: register_hash_rta(...) as top-level Expr(Call) statement
    for node in tree.body:
        if not isinstance(node, ast.Expr):
            continue
        call = node.value
        if not isinstance(call, ast.Call):
            continue
        func = call.func
        dname = func.id if isinstance(func, ast.Name) else (func.attr if isinstance(func, ast.Attribute) else None)
        if dname == "register_hash_rta":
            _process_call(call, "hash")
        elif dname == "register_code_rta":
            # Also handle direct call pattern for CodeRTA (unlikely but safe)
            _process_call(call, "code")

    return rtas


def enumerate_rtas(source_dir: Path) -> tuple[list[dict], list[dict]]:
    """
    Enumerate all RTAs from source directory.
    Returns (valid_rtas, errors).
    """
    rta_dir = source_dir / "cortado" / "rtas"
    if not rta_dir.exists():
        raise FileNotFoundError(f"RTA directory not found: {rta_dir}")

    files = sorted(f for f in rta_dir.glob("*.py") if f.name != "__init__.py")
    valid = []
    errors = []

    for f in files:
        results = parse_rta_file(f)
        for r in results:
            if "_parse_error" in r:
                errors.append(r)
            elif r.get("id") and r.get("name"):
                valid.append(r)
            else:
                errors.append({**r, "_error": "missing id or name"})

    return valid, errors
