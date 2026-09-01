#!/usr/bin/env python3
"""mastg_parser.py - Source-faithful parser for OWASP/mastg and OWASP/MASTG-Hacking-Playground.

Provides:
  - minimal YAML front-matter parsing (no external dependency)
  - MASTG test discovery (tests/ = deprecated v1, tests-beta/ = current v2)
  - MASTG demo discovery + artifact classification
  - knowledge / techniques / tools / apps / best-practices reference discovery
  - MASTG-Hacking-Playground app/backend discovery

Pinned upstreams (2026-09-01):
  - OWASP/mastg commit ef19f2b1967bc5d6fc63970ee7b03496b79e7843 (CC BY-SA 4.0)
  - OWASP/MASTG-Hacking-Playground commit db219a1011e6735cf0c6c08ba929a27ef40e1873 (GPL-3.0)
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any, Optional

MASTG_REPO = "https://github.com/OWASP/mastg"
PLAYGROUND_REPO = "https://github.com/OWASP/MASTG-Hacking-Playground"

# --- Minimal YAML subset parser -------------------------------------------------

_LIST_RE = re.compile(r"^\s*-\s+(.*)$")
_INLINE_LIST_RE = re.compile(r"^\[(.*)\]$")


def _strip_comments(line: str) -> str:
    # simple: strip trailing ' #' comment not inside quotes
    in_s = False
    in_d = False
    out = []
    i = 0
    while i < len(line):
        ch = line[i]
        if ch == "'" and not in_d:
            in_s = not in_s
        elif ch == '"' and not in_s:
            in_d = not in_d
        elif ch == "#" and not in_s and not in_d:
            break
        out.append(ch)
        i += 1
    return "".join(out).rstrip()


def parse_front_matter(text: str) -> dict[str, Any]:
    """Parse a minimal YAML front matter block. Returns {} if absent.

    Supports:
      key: value
      key: [a, b, c]
      key:
        - item1
        - item2
    Nested maps are NOT supported (MASTG front matter does not need them).
    """
    m = re.match(r"^---\s*\n(.*?)\n---", text, re.DOTALL)
    if not m:
        return {}
    result: dict[str, Any] = {}
    lines = m.group(1).splitlines()
    i = 0
    n = len(lines)
    while i < n:
        line = lines[i]
        if not line.strip():
            i += 1
            continue
        if _LIST_RE.match(line):
            i += 1
            continue  # orphan list item; ignore
        kv = re.match(r"^([A-Za-z0-9_.-]+)\s*:\s*(.*)$", line)
        if not kv:
            i += 1
            continue
        key = kv.group(1).strip()
        val = kv.group(2).strip()
        # inline list?
        il = _INLINE_LIST_RE.match(val)
        if il:
            items = []
            for piece in il.group(1).split(","):
                piece = piece.strip().strip("'\"")
                if piece:
                    items.append(piece)
            result[key] = items
            i += 1
            continue
        # block list?
        if val == "":
            items = []
            j = i + 1
            while j < n and _LIST_RE.match(lines[j]):
                item = _LIST_RE.match(lines[j]).group(1).strip().strip("'\"")
                if item:
                    items.append(item)
                j += 1
            if items:
                result[key] = items
            else:
                result[key] = ""
            i = j
            continue
        # scalar
        result[key] = _strip_comments(val).strip().strip("'\"")
        i += 1
    return result


def body_after_fm(text: str) -> str:
    """Return the markdown body with the YAML front matter block removed."""
    m = re.match(r"^---\s*\n.*?\n---\s*\n?", text, re.DOTALL)
    return text[m.end():].strip() if m else text.strip()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def compact(text: str, limit: int) -> str:
    text = (text or "").strip().replace("\n", " ").replace("\r", " ")
    return text if len(text) <= limit else text[: limit - 3] + "..."


# --- MASTG source discovery -----------------------------------------------------

def mastg_tests(root: Path) -> list[dict[str, Any]]:
    """Discover all MASTG tests.

    `tests/`      -> deprecated v1 tests (status: deprecated, covered_by)
    `tests-beta/` -> current v2 tests (id + weakness + type + knowledge)
    """
    records: list[dict[str, Any]] = []
    for subset in ("tests", "tests-beta"):
        for platform in ("android", "ios"):
            p = root / subset / platform
            if not p.exists():
                continue
            for f in sorted(p.glob("**/*.md")):
                raw = f.read_text(encoding="utf-8", errors="replace")
                fm = parse_front_matter(raw)
                canonical = f.stem  # MASTG-TEST-XXXX
                masvs_dir = f.parent.name if f.parent.name.startswith("MASVS-") else ""
                raw_platform = str(fm.get("platform", platform)).strip()
                # MASTG has two tests with platform: network (MASVS-NETWORK);
                # normalize to the directory platform (android/ios) which is the
                # authoritative source-of-truth for the test's platform.
                if raw_platform not in {"android", "ios"}:
                    raw_platform = platform

                def _as_list(v: Any) -> list:
                    if v is None:
                        return []
                    if isinstance(v, list):
                        return v
                    return [v]

                records.append({
                    "subset": subset,
                    "canonical_id": canonical,
                    "title": fm.get("title", ""),
                    "platform": raw_platform,
                    "masvs_v2_id": _as_list(fm.get("masvs_v2_id")),
                    "masvs_v1_id": _as_list(fm.get("masvs_v1_id")),
                    "masvs_dir": masvs_dir,
                    "profiles": _as_list(fm.get("profiles")),
                    "status": fm.get("status", ""),
                    "covered_by": _as_list(fm.get("covered_by")),
                    "deprecation_note": fm.get("deprecation_note", ""),
                    "weakness": fm.get("weakness") or "",
                    "type": _as_list(fm.get("type")),
                    "apis": _as_list(fm.get("apis")),
                    "knowledge": _as_list(fm.get("knowledge")),
                    "best_practices": _as_list(fm.get("best-practices")),
                    "prerequisites": _as_list(fm.get("prerequisites")),
                    "threat": fm.get("threat") or "",
                    "alias": _as_list(fm.get("alias")),
                    "source_path": str(f.relative_to(root)).replace("\\", "/"),
                    "source_sha256": sha256_file(f),
                    "body": body_after_fm(raw),
                })
    return records


def _demo_artifact_types(demo_dir: Path) -> dict[str, Any]:
    files = [x.name for x in demo_dir.rglob("*") if x.is_file()]
    has_run = any(n in {"run.sh", "run_after.sh", "run_before.sh", "evaluate.sh"} or n.startswith("run") and n.endswith(".sh") for n in files)
    has_js = any(n.endswith(".js") for n in files)
    has_r2 = any(n.endswith(".r2") for n in files)
    has_rule = any(n.endswith(".yml") or n.endswith(".yaml") for n in files)
    has_code = any(n in {"MastgTest.kt", "MastgTest.swift", "MastgTestWebView.kt"} for n in files)
    has_app = any(n == "MASTestApp" or n.endswith(".app") for n in files)
    executable = has_run or has_js or has_r2 or has_rule
    if executable:
        kind = "EXECUTABLE_SCRIPT"
    elif has_code or has_app:
        kind = "REFERENCE_CODE"
    else:
        kind = "MANUAL_REFERENCE"
    return {
        "has_run": has_run, "has_js": has_js, "has_r2": has_r2,
        "has_rule": has_rule, "has_code": has_code, "has_app": has_app,
        "artifact_kind": kind, "files": files,
    }


def mastg_demos(root: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for platform in ("android", "ios"):
        p = root / "demos" / platform
        if not p.exists():
            continue
        for d in sorted(p.glob("**/MASTG-DEMO-*")):
            if not d.is_dir():
                continue
            mdfile = next((f for f in sorted(d.glob("*.md"))), None)
            if not mdfile:
                continue
            raw = mdfile.read_text(encoding="utf-8", errors="replace")
            fm = parse_front_matter(raw)
            art = _demo_artifact_types(d)
            masvs_dir = d.parent.name if d.parent.name.startswith("MASVS-") else ""
            records.append({
                "canonical_id": mdfile.stem,
                "title": fm.get("title", ""),
                "platform": fm.get("platform", platform),
                "code": fm.get("code") or [],
                "linked_test": fm.get("test") or "",
                "masvs_dir": masvs_dir,
                "source_path": str(d.relative_to(root)).replace("\\", "/"),
                "source_sha256": sha256_file(mdfile),
                "artifact_kind": art["artifact_kind"],
                "has_run": art["has_run"], "has_js": art["has_js"],
                "has_r2": art["has_r2"], "has_rule": art["has_rule"],
                "has_code": art["has_code"], "has_app": art["has_app"],
                "files": art["files"],
                "body": body_after_fm(raw),
            })
    return records


def mastg_references(root: Path, name: str) -> list[dict[str, Any]]:
    """Discover knowledge/techniques/tools/apps/best-practices reference cards."""
    records: list[dict[str, Any]] = []
    p = root / name
    if not p.exists():
        return records
    for f in sorted(p.glob("**/*.md")):
        raw = f.read_text(encoding="utf-8", errors="replace")
        fm = parse_front_matter(raw)
        canonical = f.stem
        records.append({
            "kind": name,
            "canonical_id": canonical,
            "title": fm.get("title", ""),
            "platform": fm.get("platform", ""),
            "masvs_dir": f.parent.name if f.parent.name.startswith("MASVS-") else "",
            "source_path": str(f.relative_to(root)).replace("\\", "/"),
            "source_sha256": sha256_file(f),
        })
    return records


# --- Hacking Playground discovery ----------------------------------------------

def playground_inventory(root: Path) -> list[dict[str, Any]]:
    """Inventory every Hacking Playground app / backend / support candidate."""
    records: list[dict[str, Any]] = []

    def package_from_manifest(manifest: Path) -> str:
        try:
            txt = manifest.read_text(encoding="utf-8", errors="replace")
        except Exception:
            return ""
        m = re.search(r'package="([^"]+)"', txt)
        return m.group(1) if m else ""

    def appid_from_gradle(g: Path) -> str:
        try:
            txt = g.read_text(encoding="utf-8", errors="replace")
        except Exception:
            return ""
        m = re.search(r'applicationId\s+["\']([^"\']+)["\']', txt)
        return m.group(1) if m else ""

    # Android Kotlin
    kotlin = root / "Android" / "MASTG-Android-Kotlin-App"
    if kotlin.exists():
        gradle_files = list(kotlin.rglob("build.gradle*"))
        app_id = next((appid_from_gradle(g) for g in gradle_files if appid_from_gradle(g)), "") or "owasp.mastgkotlin"
        records.append({
            "type": "HACKING_PLAYGROUND_APP",
            "platform": "android",
            "name": "MASTG Android Kotlin App",
            "package_id": app_id,
            "source_path": "Android/MASTG-Android-Kotlin-App",
            "build_system": "gradle",
            "language": "kotlin",
            "backend_dependency": "rails-api-original",
            "license": "GPL-3.0",
            "artifact_type": "apk",
            "related": "MASTG Kotlin app - OWASP MASTG Hacking Playground",
        })

    # Android Java
    java = root / "Android" / "MSTG-Android-Java-App"
    if java.exists():
        gradle_files = list(java.rglob("build.gradle*"))
        ids = [appid_from_gradle(g) for g in gradle_files if appid_from_gradle(g)]
        app_id = ids[-1] if ids else "sg.vp.owasp_mobile.omtg_android"
        records.append({
            "type": "HACKING_PLAYGROUND_APP",
            "platform": "android",
            "name": "MASTG Android Java App",
            "package_id": app_id,
            "source_path": "Android/MSTG-Android-Java-App",
            "build_system": "gradle",
            "language": "java",
            "backend_dependency": "",
            "license": "GPL-3.0",
            "artifact_type": "apk",
            "related": "MASTG Java app - OWASP MASTG Hacking Playground",
        })

    # iOS JWT (Swift)
    ios = root / "iOS" / "MSTG-JWT"
    if ios.exists():
        has_podfile = (ios / "Podfile").exists()
        records.append({
            "type": "HACKING_PLAYGROUND_APP",
            "platform": "ios",
            "name": "MASTG iOS JWT App (Swift)",
            "package_id": "",  # resolved at build time via PRODUCT_BUNDLE_IDENTIFIER
            "source_path": "iOS/MSTG-JWT",
            "build_system": "xcode + cocoapods",
            "language": "swift",
            "backend_dependency": "rails-api-original",
            "license": "GPL-3.0",
            "artifact_type": "ipa",
            "related": "MASTG iOS Swift/JWT app - OWASP MASTG Hacking Playground",
            "notes": "Simulator build requires macOS/Xcode host; release IPA is a physical-device build.",
        })

    # Serverside Rails API
    rails = root / "Serverside" / "rails-api-original"
    if rails.exists():
        has_gemfile = (rails / "Gemfile").exists()
        records.append({
            "type": "HACKING_PLAYGROUND_BACKEND",
            "platform": "serverside",
            "name": "MASTG Hacking Playground Rails API",
            "package_id": "",
            "source_path": "Serverside/rails-api-original",
            "build_system": "ruby/bundler (Ruby on Rails)",
            "language": "ruby",
            "backend_dependency": "",
            "license": "GPL-3.0",
            "artifact_type": "service",
            "related": "Ruby on Rails API backend for MASTG Android Kotlin and iOS JWT apps",
            "has_gemfile": has_gemfile,
        })

    return records


def playground_meta(root: Path) -> dict[str, Any]:
    readme = root / "README.md"
    license_file = root / "LICENSE.md"
    return {
        "repository": PLAYGROUND_REPO,
        "readme_sha256": sha256_file(readme) if readme.exists() else "",
        "license": "GPL-3.0" if license_file.exists() else "UNKNOWN",
        "summary": compact(readme.read_text(encoding="utf-8", errors="replace"), 500) if readme.exists() else "",
    }
