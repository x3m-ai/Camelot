#!/usr/bin/env python3
"""Acquire and enumerate curated GitHub Frida source collections."""

from __future__ import annotations

import fnmatch
import os
import re
import subprocess
from pathlib import Path
from typing import Any

from frida_sources import FridaSource, compact, sha256

IGNORED_PARTS = {".git", "node_modules", "dist", "build", "vendor", "coverage", "__pycache__"}


def update_checkout(source: dict[str, Any], cache_root: Path, refresh: bool = False) -> Path:
    cache_dir = cache_root / source["cache_dir"]
    repository = source["repository"].rstrip("/") + ".git"
    environment = dict(os.environ)
    environment["GIT_LFS_SKIP_SMUDGE"] = "1"
    if not (cache_dir / ".git").is_dir():
        subprocess.run(
            ["git", "clone", "--filter=blob:none", repository, str(cache_dir)],
            check=True, env=environment, capture_output=True, text=True, timeout=300,
        )
    elif refresh:
        subprocess.run(["git", "-C", str(cache_dir), "fetch", "--prune"], check=True, env=environment, capture_output=True, text=True, timeout=120)
        subprocess.run(["git", "-C", str(cache_dir), "pull", "--ff-only"], check=True, env=environment, capture_output=True, text=True, timeout=120)
    return cache_dir


def git_value(directory: Path, *arguments: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(directory), *arguments], check=True,
        capture_output=True, text=True, timeout=30,
    )
    return result.stdout.strip()


def matches(path: str, patterns: list[str]) -> bool:
    normalized = path.replace("\\", "/")
    for pattern in patterns:
        variants = {pattern}
        if pattern.startswith("**/"):
            variants.add(pattern[3:])
        if "/**/" in pattern:
            variants.add(pattern.replace("/**/", "/"))
        if any(fnmatch.fnmatch(normalized, variant) for variant in variants):
            return True
    return False


def discover_files(source: dict[str, Any], checkout: Path) -> tuple[list[Path], list[dict[str, str]]]:
    included: list[Path] = []
    excluded: list[dict[str, str]] = []
    includes = source.get("include") or ["**/*.js", "**/*.ts"]
    excludes = source.get("exclude") or []
    for path in sorted(checkout.rglob("*")):
        if not path.is_file() or any(part in IGNORED_PARTS for part in path.parts):
            continue
        relative = str(path.relative_to(checkout)).replace("\\", "/")
        if path.suffix.lower() not in {".js", ".ts"}:
            continue
        if not matches(relative, includes):
            excluded.append({"source_path": relative, "reason": "outside include patterns"})
        elif matches(relative, excludes):
            excluded.append({"source_path": relative, "reason": "excluded by registry"})
        else:
            included.append(path)
    return included, excluded


def readme_snippets(checkout: Path) -> list[tuple[str, int, str]]:
    snippets: list[tuple[str, int, str]] = []
    for readme in sorted(checkout.glob("README*")):
        if not readme.is_file():
            continue
        text = readme.read_text(encoding="utf-8", errors="replace")
        heading = "README"
        snippet_index = 0
        lines = text.splitlines()
        index = 0
        while index < len(lines):
            line = lines[index]
            if line.startswith("#"):
                heading = line.lstrip("# ").strip() or heading
            if re.match(r"^```(?:javascript|js|typescript|ts)\s*$", line, re.I):
                language = line.removeprefix("```").strip().lower()
                end = index + 1
                while end < len(lines) and not lines[end].startswith("```"):
                    end += 1
                code = "\n".join(lines[index + 1:end]).strip()
                if len(code) >= 80 and re.search(r"Java\.|ObjC\.|Interceptor\.|Module\.|Process\.|rpc\.exports", code):
                    snippets.append((f"{heading}:{language}", snippet_index, code))
                    snippet_index += 1
                index = end
            index += 1
    return snippets


def discover_repository(source: dict[str, Any], cache_root: Path, refresh: bool = False) -> tuple[list[FridaSource], dict[str, Any]]:
    checkout = update_checkout(source, cache_root, refresh)
    commit = git_value(checkout, "rev-parse", "HEAD")
    commit_date = git_value(checkout, "show", "-s", "--format=%cs", "HEAD")
    files, excluded = discover_files(source, checkout)
    records: list[FridaSource] = []
    owner_repo = source["repository"].removeprefix("https://github.com/")
    for path in files:
        relative = str(path.relative_to(checkout)).replace("\\", "/")
        code = path.read_text(encoding="utf-8-sig", errors="replace")
        records.append(FridaSource(
            source_provider=source["id"],
            source_id=f"frida:github:{owner_repo}:{relative}",
            title=path.stem.replace("_", " ").replace("-", " ").strip(),
            description=f"Curated Frida source from {owner_repo}: {relative}",
            source_code=code,
            source_url=f"{source['repository']}/blob/{commit}/{relative}",
            source_hash=sha256(code),
            license=source.get("license", "unknown"),
            license_source=source.get("license_source", "registry"),
            distribution_status=source.get("distribution_status", "unknown-license"),
            quality_tier=source.get("quality_tier", "C"),
            source_metadata={
                "repository": source["repository"],
                "source_commit": commit,
                "source_commit_date": commit_date,
                "source_path": relative,
                "platform_hint": source.get("platform_hint", []),
                "framework_hint": source.get("framework_hint", []),
                "source_extension": path.suffix.lower(),
            },
        ))

    file_hashes = {record.source_hash for record in records}
    for heading, index, code in readme_snippets(checkout):
        code_hash = sha256(code)
        if code_hash in file_hashes:
            excluded.append({"source_path": f"README:{heading}:{index}", "reason": "duplicates source file"})
            continue
        records.append(FridaSource(
            source_provider=source["id"],
            source_id=f"frida:github:{owner_repo}:readme:{heading}:{index}",
            title=heading.split(":", 1)[0],
            description=f"Standalone Frida snippet extracted from {owner_repo} README section {heading}.",
            source_code=code,
            source_url=f"{source['repository']}/blob/{commit}/README.md",
            source_hash=code_hash,
            license=source.get("license", "unknown"),
            license_source=source.get("license_source", "registry"),
            distribution_status=source.get("distribution_status", "unknown-license"),
            quality_tier=source.get("quality_tier", "C"),
            source_metadata={
                "repository": source["repository"], "source_commit": commit,
                "source_commit_date": commit_date, "source_path": "README.md",
                "readme_heading": heading, "readme_snippet_index": index,
                "platform_hint": source.get("platform_hint", []),
                "framework_hint": source.get("framework_hint", []),
                "source_extension": ".js",
            },
        ))
    report = {
        "source_id": source["id"], "repository": source["repository"],
        "source_commit": commit, "source_commit_date": commit_date,
        "license": source.get("license", "unknown"),
        "distribution_status": source.get("distribution_status", "unknown-license"),
        "candidate_files": len(files), "discovered_sources": len(records),
        "excluded_files": excluded,
    }
    return records, report