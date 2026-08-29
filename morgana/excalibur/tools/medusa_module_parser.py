#!/usr/bin/env python3
"""
medusa_module_parser.py — Tolerant parser for MEDUSA .med and .imed module files.

MEDUSA modules are JSON with fields: Name, Description, Help, Code, Options.
Some contain control characters in Code that require tolerant parsing.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Optional

MEDUSA_COMMIT  = "8c62447d082f8612aeb9e07f8d8c20d8fa5f1fbb"
MEDUSA_RELEASE = "v3.9.6"
MEDUSA_LICENSE = "GPL-3.0"
MEDUSA_REPO    = "Ch0pin/medusa"


def _tolerant_parse(text: str) -> Optional[dict]:
    """Parse JSON tolerating control characters in strings."""
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    # Replace bare control characters inside string literals
    try:
        cleaned = re.sub(r'(?<!\\)[\x00-\x1f\x7f]', lambda m: f'\\u{ord(m.group()):04x}', text)
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass
    # Last resort: extract fields manually
    try:
        name  = re.search(r'"Name"\s*:\s*"([^"]*)"', text)
        desc  = re.search(r'"Description"\s*:\s*"([^"]*)"', text)
        help_ = re.search(r'"Help"\s*:\s*"([^"]*)"', text)
        code_m = re.search(r'"Code"\s*:\s*"((?:[^"\\]|\\.)*)"', text, re.DOTALL)
        if name:
            return {
                "Name": name.group(1),
                "Description": desc.group(1) if desc else "",
                "Help": help_.group(1) if help_ else "",
                "Code": code_m.group(1).encode().decode('unicode_escape', errors='replace') if code_m else "",
                "Options": None,
                "_parse_mode": "regex_fallback",
            }
    except Exception:
        pass
    return None


def _slug(s: str) -> str:
    return re.sub(r'[^a-z0-9_]+', '_', s.lower()).strip('_')


def parse_module(path: Path, platform: str) -> dict:
    """Parse a single .med or .imed file."""
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except Exception as exc:
        return {"_error": str(exc), "_path": str(path), "platform": platform}

    data = _tolerant_parse(text)
    if data is None:
        return {"_error": "json_parse_failed", "_path": str(path), "platform": platform}

    name = (data.get("Name") or "").strip()
    description = (data.get("Description") or "").strip()
    help_text = (data.get("Help") or "").strip()
    code = (data.get("Code") or "").strip()
    options_raw = data.get("Options")

    # Normalize options
    options = []
    if options_raw and isinstance(options_raw, list):
        for opt in options_raw:
            if isinstance(opt, dict):
                options.append({
                    "name": str(opt.get("name") or opt.get("Name") or "").strip(),
                    "help": str(opt.get("help") or opt.get("Help") or "").strip(),
                    "type": str(opt.get("type") or opt.get("Type") or "string").strip().lower(),
                    "value": opt.get("value") or opt.get("Value") or "",
                })

    # Category = parent directory name
    parts = path.relative_to(path.parent.parent.parent).parts  # modules/category/file
    if len(parts) >= 3:
        category = parts[1]
    elif len(parts) == 2:
        category = parts[0]
    else:
        category = "uncategorized"

    has_code = bool(code)
    file_sha = hashlib.sha256(path.read_bytes()).hexdigest()
    code_sha = hashlib.sha256(code.encode("utf-8", errors="replace")).hexdigest() if code else ""

    # Source path relative to medusa root
    source_path = str(path.relative_to(path.parents[3]))  # medusa/modules/...

    # Stable ID from source path
    module_id = _slug(source_path.replace("\\", "/").replace("/", "_").replace(".med", "").replace(".imed", ""))

    # Script ID
    script_id = f"medusa:{platform}:{module_id}"

    # Display name
    display_name = name or path.stem.replace("_", " ").title()

    return {
        "script_id": script_id,
        "source_path": str(path),
        "source_file": path.name,
        "source_sha256": file_sha,
        "source_commit": MEDUSA_COMMIT,
        "platform": platform,
        "category": category,
        "name": name,
        "display_name": display_name,
        "description": description,
        "help_text": help_text,
        "code": code,
        "code_sha256": code_sha,
        "options": options,
        "has_code": has_code,
        "has_options": bool(options),
        "parse_mode": data.get("_parse_mode", "standard"),
        "is_template": not has_code,
    }


def enumerate_modules(medusa_dir: Path) -> tuple[list[dict], list[dict]]:
    """Enumerate all .med and .imed module files."""
    modules_dir = medusa_dir / "modules"
    if not modules_dir.exists():
        raise FileNotFoundError(f"modules/ not found in {medusa_dir}")

    valid, errors = [], []

    # Android .med
    for f in sorted(modules_dir.rglob("*.med")):
        result = parse_module(f, "android")
        if "_error" in result:
            errors.append(result)
        else:
            valid.append(result)

    # iOS .imed
    for f in sorted(modules_dir.rglob("*.imed")):
        result = parse_module(f, "ios")
        if "_error" in result:
            errors.append(result)
        else:
            valid.append(result)

    return valid, errors


def enumerate_snippets(medusa_dir: Path) -> list[dict]:
    """Enumerate MEDUSA standalone JS snippets."""
    snippets_dir = medusa_dir / "snippets"
    if not snippets_dir.exists():
        return []
    result = []
    for f in sorted(snippets_dir.rglob("*.js")):
        code = f.read_text(encoding="utf-8", errors="replace")
        if not code.strip():
            continue
        name = f.stem.replace("_", " ").title()
        slug = _slug(f.stem)
        result.append({
            "script_id": f"medusa:android:snippet:{slug}",
            "source_path": str(f),
            "source_file": f.name,
            "source_sha256": hashlib.sha256(f.read_bytes()).hexdigest(),
            "source_commit": MEDUSA_COMMIT,
            "platform": "android",
            "category": "snippets",
            "name": name,
            "display_name": name,
            "description": f"MEDUSA standalone Frida snippet: {name}",
            "help_text": "",
            "code": code,
            "code_sha256": hashlib.sha256(code.encode()).hexdigest(),
            "options": [],
            "has_code": True,
            "has_options": False,
            "parse_mode": "standalone_js",
            "is_template": False,
        })
    return result


def get_source_commit(medusa_dir: Path) -> str:
    import subprocess
    try:
        r = subprocess.run(["git", "-C", str(medusa_dir), "rev-parse", "HEAD"],
                          capture_output=True, text=True, check=True)
        return r.stdout.strip()
    except Exception:
        return MEDUSA_COMMIT
