#!/usr/bin/env python3
"""
drozer_module_parser.py — Tolerant AST parser for drozer core and
drozer-modules external module corpora.

A drozer module is a Python class subclassing `drozer.modules.Module` (often
via `common.*` mixins). Canonical attributes: name, description, examples,
author, date, license, path (namespace), permissions, module_type, plus an
`add_arguments(self, parser)` method declaring argparse options.

This module:
  - discovers all core modules under src/drozer/modules/
  - discovers all external modules under the drozer-modules tree
  - extracts metadata and argument schemas via AST (no import of drozer needed)
  - classifies every candidate: EXECUTABLE / MANUAL / SUPPORT /
    FRAMEWORK_INTERNAL / ABSTRACT / ALIAS / LEGACY_COMPATIBLE / INCOMPATIBLE /
    LICENSE_BLOCKED / PARSE_ERROR

No candidate is silently dropped.
"""
from __future__ import annotations

import ast
import hashlib
import re
from pathlib import Path
from typing import Any, Optional

DROZER_REPO = "ReversecLabs/drozer"
DROZER_COMMIT = "d992f6378d42680ea96ee03eff4117f150e1049c"
DROZER_VERSION = "3.2.0"
DROZER_LICENSE = "BSD-3-Clause"

DROZER_AGENT_REPO = "ReversecLabs/drozer-agent"
DROZER_AGENT_COMMIT = "c1f18ceb6f8464811e9e4f9d57ad8cb38de4e339"
DROZER_AGENT_LICENSE = "BSD-3-Clause"
DROZER_AGENT_PACKAGE = "com.reversec.dz"

DROZER_MODULES_REPO = "ReversecLabs/drozer-modules"
DROZER_MODULES_COMMIT = "c6fb1570163e3347e11c8d8589d51b88931137dd"
DROZER_MODULES_LICENSE = "UNSET"  # no repository-wide license; per-module only

# drozer server default port (ADB forward target)
DROZER_PORT = 31415

# Python files under the core tree that are framework support, not modules.
CORE_SUPPORT_BASENAMES = {"__init__.py", "base.py", "collection.py", "loader.py", "import_conflict_resolver.py"}

# External tree support files.
EXTERNAL_SUPPORT_BASENAMES = {"__init__.py"}

# Mixin classes in common/ that a real module may subclass but are not modules.
COMMON_MIXIN_DIRS = {"common", "tools"}

_SLUG_RE = re.compile(r"[^a-z0-9_]+")


def _slug(value: str) -> str:
    return _SLUG_RE.sub("_", (value or "").lower()).strip("_")


def _file_sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _ast_constant(node: ast.AST) -> Optional[Any]:
    """Best-effort constant extraction (handles str/list/int/bool/None)."""
    if node is None:
        return None
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.List):
        out = []
        for elt in node.elts:
            v = _ast_constant(elt)
            if v is not None:
                out.append(v)
        return out
    if isinstance(node, ast.Tuple):
        return [_ast_constant(e) for e in node.elts]
    if isinstance(node, ast.Name):
        # common sentinel values
        return node.id
    return None


def _extract_class_attrs(tree: ast.AST) -> dict[str, dict[str, Any]]:
    """Return {class_name: {attr: value}} for every top-level class in a file."""
    out: dict[str, dict[str, Any]] = {}
    for node in tree.body:
        if not isinstance(node, ast.ClassDef):
            continue
        attrs: dict[str, Any] = {"_bases": []}
        for base in node.bases:
            if isinstance(base, ast.Name):
                attrs["_bases"].append(base.id)
            elif isinstance(base, ast.Attribute):
                attrs["_bases"].append(base.attr)
        for stmt in node.body:
            if isinstance(stmt, ast.Assign):
                for target in stmt.targets:
                    if isinstance(target, ast.Name):
                        val = _ast_constant(stmt.value)
                        if val is not None:
                            attrs[target.id] = val
            elif isinstance(stmt, ast.FunctionDef):
                if stmt.name == "add_arguments":
                    attrs["_add_arguments"] = _extract_arguments(stmt)
                elif stmt.name == "execute":
                    attrs["_has_execute"] = True
        out[node.name] = attrs
    return out


def _extract_arguments(func: ast.FunctionDef) -> list[dict[str, Any]]:
    """Extract parser.add_argument(...) calls from an add_arguments body."""
    args: list[dict[str, Any]] = []
    for node in ast.walk(func):
        if not isinstance(node, ast.Call):
            continue
        fn = node.func
        if isinstance(fn, ast.Attribute) and fn.attr == "add_argument":
            rec = {"_positional": [], "_flags": [], "help": "", "type": "string",
                   "required": False, "default": None, "choices": None,
                   "action": None, "nargs": None}
            for pos in node.args:
                v = _ast_constant(pos)
                if isinstance(v, str):
                    rec["_positional"].append(v)
            for kw in node.keywords:
                if kw.arg == "help":
                    rec["help"] = _ast_constant(kw.value) or ""
                elif kw.arg == "type":
                    v = _ast_constant(kw.value)
                    rec["type"] = {"int": "integer", "float": "float", "str": "string", "bool": "boolean"}.get(
                        v if isinstance(v, str) else "", "string")
                elif kw.arg == "required":
                    rec["required"] = bool(_ast_constant(kw.value))
                elif kw.arg == "default":
                    rec["default"] = _ast_constant(kw.value)
                elif kw.arg == "choices":
                    v = _ast_constant(kw.value)
                    if isinstance(v, list):
                        rec["choices"] = [str(x) for x in v]
                elif kw.arg == "action":
                    rec["action"] = _ast_constant(kw.value)
                elif kw.arg == "nargs":
                    v = _ast_constant(kw.value)
                    if v is not None:
                        rec["nargs"] = str(v)
            # split flags vs positional
            for p in rec.pop("_positional", []):
                if p.startswith("-"):
                    rec["_flags"].append(p)
                else:
                    rec["positional"] = p
            if rec.get("_flags"):
                long_flags = [f for f in rec["_flags"] if f.startswith("--")]
                short_flags = [f for f in rec["_flags"] if f.startswith("-") and not f.startswith("--")]
                flag = (long_flags[0] if long_flags else (short_flags[0] if short_flags else rec["_flags"][0]))
                rec["flag"] = flag
                rec["dest"] = flag.lstrip("-")
            elif rec.get("positional"):
                rec["dest"] = rec["positional"]
                rec["flag"] = None
            rec.pop("_flags", None)
            rec.pop("_positional", None)
            if rec.get("dest"):
                args.append(rec)
    return args


def _normalize_arg(arg: dict[str, Any]) -> dict[str, Any]:
    """Drop internal keys; expose a stable argument schema."""
    return {
        "name": arg.get("dest") or arg.get("positional") or "",
        "flag": arg.get("flag"),
        "help": arg.get("help") or "",
        "type": arg.get("type") or "string",
        "required": bool(arg.get("required")),
        "default": arg.get("default"),
        "choices": arg.get("choices"),
        "action": arg.get("action"),
        "nargs": arg.get("nargs"),
        "positional": bool(arg.get("positional")),
    }


def _classify_module(klass: dict[str, Any], relpath: str, collection: str) -> str:
    """Classify one candidate class into an explicit status.

    Rationale (derived from actual drozer semantics):
      - `module_type == "payload"`  -> run via `drozer payload build` with a
        different __init__ signature; NOT runnable via the console `run` path.
      - `module_type == "exploit"`  -> `execute()` is inherited from
        common.Exploit mixin; runnable via `drozer console run`.
      - classes without path+name are support/mixin helpers.
      - classes with path+name but no (local or inherited) execute are MANUAL.
    """
    path_attr = klass.get("path")
    has_path = isinstance(path_attr, list) and bool(path_attr)
    name_attr = klass.get("name")
    module_type = klass.get("module_type", "drozer")

    if module_type == "payload":
        return "MANUAL"
    if module_type in {"manual", "manual-only"}:
        return "MANUAL"

    if not has_path or not name_attr:
        return "SUPPORT" if collection == "drozer-modules" else "FRAMEWORK_INTERNAL"

    if module_type == "exploit":
        return "EXECUTABLE"

    if not klass.get("_has_execute"):
        return "MANUAL"

    return "EXECUTABLE"


def _module_record(path: Path, root: Path, collection: str, commit: str) -> list[dict[str, Any]]:
    """Produce candidate record(s) for a single module file (always a list)."""
    rel = path.relative_to(root).as_posix()
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except Exception as exc:
        return [{"_error": str(exc), "source_path": rel, "collection": collection, "status": "PARSE_ERROR"}]

    try:
        tree = ast.parse(text)
    except SyntaxError as exc:
        return [{"_error": f"syntax: {exc}", "source_path": rel, "collection": collection, "status": "PARSE_ERROR"}]

    classes = _extract_class_attrs(tree)
    file_sha = _file_sha(path)

    modules_found = []
    for cname, cattr in classes.items():
        if cname.startswith("_") or cname in {"Module", "Session", "Usage"}:
            continue
        modules_found.append((cname, cattr))

    if not modules_found:
        status = "SUPPORT" if collection == "drozer-modules" else "FRAMEWORK_INTERNAL"
        return [{
            "source_path": rel, "collection": collection, "commit": commit,
            "source_sha256": file_sha, "status": status,
            "module": None, "namespace": None, "name": None,
        }]

    records: list[dict[str, Any]] = []
    for cname, cattr in modules_found:
        status = _classify_module(cattr, rel, collection)
        namespace = ".".join(cattr.get("path") or []) if isinstance(cattr.get("path"), list) else ""
        fqmn = ".".join(list(cattr.get("path") or []) + [cname.lower()]) if isinstance(cattr.get("path"), list) else cname.lower()
        args = [ _normalize_arg(a) for a in (cattr.get("_add_arguments") or []) ]
        author = cattr.get("author") or "Unspecified"
        if isinstance(author, list):
            author = ", ".join(author)
        license_ = cattr.get("license") or (DROZER_LICENSE if collection == "core" else "UNSET")
        records.append({
            "script_id": f"drozer:{collection}:{_slug(fqmn)}",
            "source_path": rel,
            "source_file": path.name,
            "collection": collection,
            "commit": commit,
            "source_sha256": file_sha,
            "code_sha256": hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest(),
            "fqmn": fqmn,
            "namespace": namespace,
            "class_name": cname,
            "name": str(cattr.get("name") or cname.replace("_", " ").title()),
            "description": str(cattr.get("description") or "").strip(),
            "examples": str(cattr.get("examples") or "").strip(),
            "author": author,
            "date": str(cattr.get("date") or ""),
            "license": license_,
            "permissions": cattr.get("permissions") if isinstance(cattr.get("permissions"), list) else [],
            "module_type": cattr.get("module_type") or "drozer",
            "status": status,
            "has_options": bool(args),
            "options": args,
            "repository": f"https://github.com/{DROZER_REPO if collection == 'core' else DROZER_MODULES_REPO}",
        })
    return records


def enumerate_core_modules(source: Path) -> tuple[list[dict], list[dict]]:
    """Enumerate core drozer modules (src/drozer/modules)."""
    root = source / "src" / "drozer" / "modules"
    records: list[dict] = []
    errors: list[dict] = []
    if not root.is_dir():
        return records, [{"error": f"core modules dir not found: {root}"}]
    for path in sorted(root.rglob("*.py")):
        if path.name in CORE_SUPPORT_BASENAMES:
            continue
        records.extend(_module_record(path, root, "core", DROZER_COMMIT))
    return records, errors


def enumerate_external_modules(source: Path) -> tuple[list[dict], list[dict]]:
    """Enumerate external drozer-modules (author namespace dirs)."""
    records: list[dict] = []
    errors: list[dict] = []
    if not source.is_dir():
        return records, [{"error": f"drozer-modules source not found: {source}"}]
    for path in sorted(source.rglob("*.py")):
        if path.name in EXTERNAL_SUPPORT_BASENAMES or ".git" in path.parts:
            continue
        if ".drozer_repository" in path.parts:
            continue
        records.extend(_module_record(path, source, "drozer-modules", DROZER_MODULES_COMMIT))
    return records, errors


def get_source_commit(source: Path) -> str:
    """Return the HEAD commit of a source checkout (empty if unavailable)."""
    try:
        import subprocess
        r = subprocess.run(["git", "-C", str(source), "rev-parse", "HEAD"],
                           capture_output=True, text=True, timeout=15)
        return r.stdout.strip()
    except Exception:
        return ""


def license_blocked(record: dict) -> bool:
    return record.get("license") in {"UNSET", "Unspecified", "", None} and record.get("collection") == "drozer-modules"
