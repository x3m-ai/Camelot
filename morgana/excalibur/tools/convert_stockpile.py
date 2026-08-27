#!/usr/bin/env python3
"""Convert MITRE CALDERA Stockpile abilities into Morgana Excalibur packs.

The converter only reads and normalizes upstream content. It never executes
ability commands, cleanup commands, parsers, requirements, build blocks, or
payloads.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

try:
    import yaml
except ImportError:
    print("[ERROR] PyYAML is required. Run: python -m pip install pyyaml")
    sys.exit(1)

TOOLS_DIR = Path(__file__).resolve().parent
EXCALIBUR_DIR = TOOLS_DIR.parent
DEFAULT_OUTPUT_DIR = EXCALIBUR_DIR / "stockpile"
CATALOG_FILE = EXCALIBUR_DIR / "catalog.json"
CATALOG_BASE_URL = (
    "https://raw.githubusercontent.com/x3m-ai/Camelot/main/"
    "morgana/excalibur/stockpile"
)
SOURCE_REPOSITORY = "https://github.com/mitre/stockpile"
SOURCE_NAME = "mitre-stockpile"
SCRIPT_PREFIX = "STOCKPILE - "
VALID_TCODE = re.compile(r"^T\d{4}(?:\.\d{3})?$")
PLACEHOLDER = re.compile(r"#\{([^{}]+)\}")
REMOTE_URL = re.compile(r"https?://[^\s'\"`]+", re.IGNORECASE)
DOWNLOAD_PRIMITIVE = re.compile(
    r"(?:downloadstring|downloadfile|invoke-webrequest|start-bitstransfer|\bcurl(?:\.exe)?\b|\bwget(?:\.exe)?\b)",
    re.IGNORECASE,
)
EXECUTION_SINK = re.compile(
    r"(?:\|\s*(?:sh|bash|zsh|python\d*|pwsh|powershell)\b|\biex\b|invoke-expression|scriptleturl)",
    re.IGNORECASE,
)
SENSITIVE_TERMS = (
    "password",
    "passwd",
    "token",
    "secret",
    "credential",
    "private_key",
    "private.key",
    "apikey",
    "api.key",
    "api_key",
    "access.key",
)

TACTICS: dict[str, tuple[str, str, str]] = {
    "collection": ("TA0009", "Collection", "collection"),
    "command-and-control": ("TA0011", "Command and Control", "c2"),
    "credential-access": ("TA0006", "Credential Access", "credaccess"),
    "defense-evasion": ("TA0005", "Defense Evasion", "evasion"),
    "discovery": ("TA0007", "Discovery", "discovery"),
    "execution": ("TA0002", "Execution", "exec"),
    "exfiltration": ("TA0010", "Exfiltration", "exfil"),
    "impact": ("TA0040", "Impact", "impact"),
    "lateral-movement": ("TA0008", "Lateral Movement", "lateral"),
    "persistence": ("TA0003", "Persistence", "persist"),
    "privilege-escalation": ("TA0004", "Privilege Escalation", "privesc"),
}

EXECUTORS = {
    "psh": "powershell",
    "pwsh": "powershell",
    "powershell": "powershell",
    "cmd": "cmd",
    "sh": "bash",
    "bash": "bash",
    "python": "python",
    "python3": "python",
}

PLATFORMS = {
    "windows": "windows",
    "linux": "linux",
    "darwin": "macos",
    "macos": "macos",
}

EXECUTOR_LABELS = {
    "powershell": "PowerShell",
    "cmd": "CMD",
    "bash": "Bash",
    "python": "Python",
}

PLATFORM_LABELS = {
    "windows": "Windows",
    "linux": "Linux",
    "macos": "macOS",
}


@dataclass
class ConversionState:
    files_scanned: int = 0
    abilities_parsed: int = 0
    variants_discovered: int = 0
    generated_scripts: int = 0
    skipped_variants: int = 0
    errors: int = 0
    abilities_with_facts: set[str] = field(default_factory=set)
    facts_converted: int = 0
    abilities_with_cleanup: set[str] = field(default_factory=set)
    abilities_with_parsers: set[str] = field(default_factory=set)
    abilities_with_requirements: set[str] = field(default_factory=set)
    payload_references: int = 0
    executor_counts: Counter[str] = field(default_factory=Counter)
    platform_counts: Counter[str] = field(default_factory=Counter)
    encountered_executors: Counter[str] = field(default_factory=Counter)
    encountered_platforms: Counter[str] = field(default_factory=Counter)
    unsupported_executors: list[dict[str, Any]] = field(default_factory=list)
    unsupported_platforms: list[dict[str, Any]] = field(default_factory=list)
    unsupported_build_variants: list[dict[str, Any]] = field(default_factory=list)
    unsafe_runtime_variants: list[dict[str, Any]] = field(default_factory=list)
    payload_issues: list[dict[str, Any]] = field(default_factory=list)
    parser_metadata: list[dict[str, Any]] = field(default_factory=list)
    requirement_metadata: list[dict[str, Any]] = field(default_factory=list)
    malformed_files: list[dict[str, Any]] = field(default_factory=list)
    skipped_source_entries: list[dict[str, Any]] = field(default_factory=list)
    invalid_variants: list[dict[str, Any]] = field(default_factory=list)
    errors_detail: list[dict[str, Any]] = field(default_factory=list)

    def skip(self) -> None:
        self.skipped_variants += 1


def log(message: str) -> None:
    print(f"[STOCKPILE] {message}")


def warning(message: str) -> None:
    print(f"[STOCKPILE] [WARN] {message}")


def sanitize_key(value: str) -> str:
    return re.sub(r"_+", "_", re.sub(r"[^a-z0-9]+", "_", value.lower())).strip("_")


def tcode_key(tcode: str) -> str:
    return tcode.removeprefix("T").replace(".", "_").lower()


def make_tag_key(tactic_slug: str, tcode: str, fact: str) -> str:
    prefix = f"stockpile_{tactic_slug}_{tcode_key(tcode)}_"
    fact_part = sanitize_key(fact) or "value"
    candidate = f"{prefix}{fact_part}"
    if len(candidate) <= 64:
        return candidate
    digest = hashlib.sha1(fact.encode("utf-8")).hexdigest()[:7]
    return f"{candidate[:56]}_{digest}"[:64]


def friendly_label(fact: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[._-]+", " ", fact)).strip().title()


def is_sensitive(fact: str) -> bool:
    normalized = fact.lower()
    return any(term in normalized for term in SENSITIVE_TERMS)


def trim(value: Any, maximum: int) -> str:
    text = str(value or "").strip()
    if len(text) <= maximum:
        return text
    return f"{text[: maximum - 3].rstrip()}..."


def command_text(value: Any) -> str:
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, list):
        return "\n".join(str(item) for item in value if item is not None).strip()
    return ""


def extract_payloads(executor: dict[str, Any]) -> list[str]:
    raw = executor.get("payloads") or executor.get("payload") or []
    if isinstance(raw, str):
        return [raw]
    if isinstance(raw, list):
        return [str(item) for item in raw if item]
    if isinstance(raw, dict):
        return [str(value) for value in raw.values() if value]
    return [str(raw)] if raw else []


def source_identity(stockpile_dir: Path) -> tuple[str, str]:
    def git_value(arguments: list[str], fallback: str) -> str:
        try:
            result = subprocess.run(
                ["git", "-C", str(stockpile_dir), *arguments],
                check=True,
                capture_output=True,
                text=True,
                timeout=15,
            )
            return result.stdout.strip() or fallback
        except (OSError, subprocess.SubprocessError):
            return fallback

    commit = git_value(["rev-parse", "HEAD"], "unknown")
    commit_date = git_value(["show", "-s", "--format=%cs", "HEAD"], "unknown")
    return commit, commit_date


def resolve_tactic(raw_tactic: str, source_path: Path) -> tuple[str, str, str, str] | None:
    normalized = sanitize_key(raw_tactic).replace("_", "-")
    if normalized not in TACTICS:
        parent = source_path.parent.name.lower()
        normalized = parent if parent in TACTICS else normalized
    info = TACTICS.get(normalized)
    if not info:
        return None
    tactic_id, tactic_name, tactic_slug = info
    return normalized, tactic_id, tactic_name, tactic_slug


def iter_abilities(
    path: Path,
    state: ConversionState,
    source_label: str,
) -> Iterable[dict[str, Any]]:
    try:
        loaded = yaml.safe_load(path.read_text(encoding="utf-8", errors="replace"))
    except (OSError, yaml.YAMLError) as exc:
        state.errors += 1
        state.malformed_files.append({"source_path": source_label, "error": str(exc)})
        warning(f"Malformed YAML skipped: {path.name}: {exc}")
        return []

    if isinstance(loaded, dict):
        entries = [loaded]
    elif isinstance(loaded, list):
        entries = [entry for entry in loaded if isinstance(entry, dict)]
    else:
        state.malformed_files.append(
            {"source_path": source_label, "error": f"unexpected root type: {type(loaded).__name__}"}
        )
        return []
    return entries


def unique_script_name(base: str, identity: str, names: set[str]) -> str:
    if base not in names:
        names.add(base)
        return base
    candidate = f"{base} [{identity[:8]}]"
    counter = 2
    while candidate in names:
        candidate = f"{base} [{identity[:8]}-{counter}]"
        counter += 1
    names.add(candidate)
    return candidate


def rewrite_placeholders(
    text: str,
    tactic_slug: str,
    tcode: str,
    ability_id: str,
    state: ConversionState,
) -> tuple[str, list[dict[str, Any]], list[str]]:
    facts = sorted(set(PLACEHOLDER.findall(text)))
    tags: list[dict[str, Any]] = []
    rename: dict[str, str] = {}
    for fact in facts:
        key = make_tag_key(tactic_slug, tcode, fact)
        rename[fact] = key
        tags.append(
            {
                "key": key,
                "label": friendly_label(fact),
                "description": f"MITRE Stockpile fact: {fact}",
                "default": "",
                "example": "",
                "sensitive": is_sensitive(fact),
                "required": True,
                "_fact": fact,
                "_ability_id": ability_id,
                "_tcode": tcode,
            }
        )
    rewritten = PLACEHOLDER.sub(lambda match: f"#{{{rename[match.group(1)]}}}", text)
    if facts:
        state.abilities_with_facts.add(ability_id)
        state.facts_converted += len(facts)
    return rewritten, tags, facts


def requirement_summary(requirements: Any) -> Any:
    if requirements is None:
        return None
    return requirements


def unsafe_runtime_reasons(
    command: str,
    cleanup: str,
    ability_name: str,
    ability_description: str,
) -> list[str]:
    combined = f"{ability_name}\n{ability_description}\n{command}\n{cleanup}".lower()
    reasons: list[str] = []
    if any(marker in combined for marker in ("s4ndc4t", "sandcat")):
        reasons.append("requires CALDERA Sandcat runtime")
    if "/file/download" in combined or "/file/upload" in combined:
        reasons.append("requires CALDERA file transfer service")
    if "#{server}" in combined and any(
        marker in combined for marker in ("-server", "server=", "server ")
    ):
        reasons.append("requires CALDERA server fact/runtime")
    if "scriptleturl" in combined and REMOTE_URL.search(combined):
        reasons.append("loads an unverified remote scriptlet")
    if DOWNLOAD_PRIMITIVE.search(combined) and EXECUTION_SINK.search(combined):
        reasons.append("downloads and executes unverified remote content")
    if REMOTE_URL.search(combined) and any(
        marker in combined
        for marker in (
            "downloadstring",
            "downloadfile",
            "invoke-webrequest",
            "start-bitstransfer",
            "curl ",
            "curl.exe",
            "wget ",
            "wget.exe",
            "iex ",
            "invoke-expression",
        )
    ):
        reasons.append("downloads remote content without package integrity metadata")
    return reasons


def convert_variant(
    ability: dict[str, Any],
    source_path: Path,
    relative_path: str,
    raw_platform: str,
    raw_executor: str,
    executor_definition: Any,
    tactic_id: str,
    tactic_name: str,
    tactic_slug: str,
    state: ConversionState,
    platform_filter: str | None,
    names: set[str],
) -> tuple[dict[str, Any], list[dict[str, Any]]] | None:
    ability_id = str(ability.get("id") or "").strip()
    state.variants_discovered += 1
    state.encountered_platforms[raw_platform] += 1
    state.encountered_executors[raw_executor] += 1

    platform = PLATFORMS.get(raw_platform.lower())
    if not platform:
        state.unsupported_platforms.append(
            {
                "ability": ability_id,
                "source_path": relative_path,
                "platform": raw_platform,
                "executor": raw_executor,
            }
        )
        state.skip()
        return None
    if platform_filter and platform != platform_filter:
        return None

    executor = EXECUTORS.get(raw_executor.lower())
    if not executor:
        state.unsupported_executors.append(
            {
                "ability": ability_id,
                "tactic": tactic_name,
                "platform": raw_platform,
                "executor": raw_executor,
                "source_path": relative_path,
            }
        )
        warning(
            f"Unsupported executor: ability={ability_id} tactic={tactic_name} "
            f"platform={raw_platform} executor={raw_executor}"
        )
        state.skip()
        return None

    if not isinstance(executor_definition, dict):
        state.invalid_variants.append(
            {"ability": ability_id, "source_path": relative_path, "error": "executor definition is not an object"}
        )
        state.skip()
        return None

    raw_command = command_text(executor_definition.get("command"))
    build_fields = {
        key: executor_definition.get(key)
        for key in ("build_target", "language", "code")
        if executor_definition.get(key) not in (None, "")
    }
    if build_fields and not raw_command:
        state.unsupported_build_variants.append(
            {
                "ability": ability_id,
                "source_path": relative_path,
                "platform": raw_platform,
                "executor": raw_executor,
                "build_target": build_fields.get("build_target"),
                "language": build_fields.get("language"),
            }
        )
        state.skip()
        return None
    if not raw_command:
        state.invalid_variants.append(
            {
                "ability": ability_id,
                "source_path": relative_path,
                "platform": raw_platform,
                "executor": raw_executor,
                "error": "empty command",
            }
        )
        state.skip()
        return None

    payloads = extract_payloads(executor_definition)
    if payloads:
        state.payload_references += len(payloads)
        issues = []
        stockpile_root = source_path.parents[3]
        for payload in payloads:
            candidates = [
                source_path.parent / payload,
                stockpile_root / "payloads" / payload,
                stockpile_root / "data" / "payloads" / payload,
            ]
            resolved = next((candidate for candidate in candidates if candidate.exists()), None)
            issues.append(
                {
                    "name": payload,
                    "resolved": bool(resolved),
                    "resolved_path": resolved.relative_to(stockpile_root).as_posix() if resolved else None,
                }
            )
        state.payload_issues.append(
            {
                "ability": ability_id,
                "source_path": relative_path,
                "platform": raw_platform,
                "executor": raw_executor,
                "payloads": issues,
                "action": "skipped_requires_payload",
            }
        )
        state.skip()
        return None

    raw_cleanup = command_text(
        executor_definition.get("cleanup") or executor_definition.get("cleanup_command")
    )
    unsafe_reasons = unsafe_runtime_reasons(
        raw_command,
        raw_cleanup,
        str(ability.get("name") or ""),
        str(ability.get("description") or ""),
    )
    if unsafe_reasons:
        state.unsafe_runtime_variants.append(
            {
                "ability": ability_id,
                "source_path": relative_path,
                "platform": raw_platform,
                "executor": raw_executor,
                "reasons": unsafe_reasons,
                "action": "skipped_unsafe_runtime_dependency",
            }
        )
        state.skip()
        return None

    cleanup_boundary = "\n__MORGANA_STOCKPILE_CLEANUP_BOUNDARY__\n"
    combined = f"{raw_command}{cleanup_boundary}{raw_cleanup}" if raw_cleanup else raw_command
    rewritten, tags, _facts = rewrite_placeholders(
        combined, tactic_slug, str(ability["_tcode"]), ability_id, state
    )
    if raw_cleanup:
        command, cleanup = (part.strip() for part in rewritten.split(cleanup_boundary, 1))
        state.abilities_with_cleanup.add(ability_id)
    else:
        command = rewritten.strip()
        cleanup = ""

    unresolved = [fact for fact in PLACEHOLDER.findall(f"{command}\n{cleanup}") if fact not in {t["key"] for t in tags}]
    if unresolved:
        state.invalid_variants.append(
            {
                "ability": ability_id,
                "source_path": relative_path,
                "error": "unresolved placeholders",
                "placeholders": unresolved,
            }
        )
        state.skip()
        return None

    parsers = executor_definition.get("parsers")
    if parsers:
        state.abilities_with_parsers.add(ability_id)
        state.parser_metadata.append(
            {
                "ability": ability_id,
                "source_path": relative_path,
                "platform": raw_platform,
                "executor": raw_executor,
                "parsers": parsers,
                "action": "ignored_for_execution",
            }
        )

    requirements = executor_definition.get("requirements") or ability.get("requirements")
    if requirements:
        state.abilities_with_requirements.add(ability_id)
        state.requirement_metadata.append(
            {
                "ability": ability_id,
                "source_path": relative_path,
                "platform": raw_platform,
                "executor": raw_executor,
                "requirements": requirement_summary(requirements),
                "action": "preserved_as_diagnostic_only",
            }
        )

    technique_name = trim(ability.get("_technique_name"), 120)
    ability_name = trim(ability.get("name") or "Unnamed Ability", 80)
    variant_label = f"{PLATFORM_LABELS[platform]}/{EXECUTOR_LABELS[executor]}"
    base_name = f"{SCRIPT_PREFIX}{ability['_tcode']} - {ability_name} [{variant_label}]"
    script_name = unique_script_name(base_name, ability_id, names)

    source_requirements = requirement_summary(requirements)
    script = {
        "id": script_name,
        "name": script_name,
        "description": trim(ability.get("description") or f"MITRE Stockpile ability for {ability['_tcode']}.", 500),
        "tactic": tactic_name,
        "tcode": ability["_tcode"],
        "technique_name": technique_name,
        "executor": executor,
        "platform": platform,
        "required_tags": [tag["key"] for tag in tags],
        "command": command,
        "cleanup_command": cleanup,
        "detection_rule": "See MITRE ATT&CK for detection guidance",
        "sentinel_connector": "",
        "package": "stockpile",
        "source": SOURCE_NAME,
        "stockpile_id": ability_id,
        "source_path": relative_path,
        "source_executor": raw_executor,
        "source_platform": raw_platform,
    }
    if source_requirements:
        script["source_requirements"] = source_requirements

    state.generated_scripts += 1
    state.executor_counts[executor] += 1
    state.platform_counts[platform] += 1
    return script, tags


def validate_pack(pack: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for field_name in ("package_id", "package_name", "version", "scripts", "chains"):
        if not pack.get(field_name):
            errors.append(f"missing top-level field: {field_name}")

    scripts = pack.get("scripts") or []
    names: set[str] = set()
    tag_keys = {
        tag.get("key")
        for category in pack.get("tag_categories") or []
        for tag in category.get("tags") or []
        if tag.get("key")
    }
    for index, script in enumerate(scripts):
        name = script.get("name") or ""
        if not name.startswith(SCRIPT_PREFIX):
            errors.append(f"script {index}: invalid prefix: {name}")
        if name in names:
            errors.append(f"script {index}: duplicate name: {name}")
        names.add(name)
        if not VALID_TCODE.match(script.get("tcode") or ""):
            errors.append(f"script {index}: invalid tcode")
        if script.get("executor") not in set(EXECUTORS.values()):
            errors.append(f"script {index}: unsupported executor")
        if script.get("platform") not in set(PLATFORMS.values()):
            errors.append(f"script {index}: unsupported platform")
        if not str(script.get("command") or "").strip():
            errors.append(f"script {index}: empty command")
        required = set(script.get("required_tags") or [])
        missing_tags = required - tag_keys
        if missing_tags:
            errors.append(f"script {index}: missing tag definitions: {sorted(missing_tags)}")
        final_placeholders = set(
            PLACEHOLDER.findall(
                f"{script.get('command') or ''}\n{script.get('cleanup_command') or ''}"
            )
        )
        if final_placeholders != required:
            errors.append(
                f"script {index}: placeholders {sorted(final_placeholders)} do not match required_tags {sorted(required)}"
            )

    for index, chain in enumerate(pack.get("chains") or []):
        refs = chain.get("script_refs") or []
        if not refs:
            errors.append(f"chain {index}: missing script_refs")
        for ref in refs:
            if ref not in names:
                errors.append(f"chain {index}: unresolved script_ref: {ref}")
    return errors


def build_pack(
    tactic_key: str,
    tactic_id: str,
    tactic_name: str,
    tactic_slug: str,
    scripts: list[dict[str, Any]],
    tag_definitions: dict[str, dict[str, Any]],
    source_commit: str,
    source_date: str,
) -> dict[str, Any]:
    package_id = f"stockpile-{tactic_slug}-v1"
    tcodes = sorted({script["tcode"] for script in scripts})
    platforms = sorted({script["platform"] for script in scripts})

    tags_by_tcode: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for tag in tag_definitions.values():
        tags_by_tcode[tag["_tcode"]].append(tag)

    tag_categories = []
    for tcode, tags in sorted(tags_by_tcode.items()):
        clean_tags = [
            {key: value for key, value in tag.items() if not key.startswith("_")}
            for tag in sorted(tags, key=lambda item: item["key"])
        ]
        tag_categories.append(
            {
                "category_id": f"stockpile_{tactic_slug}_{tcode_key(tcode)}",
                "label": f"{tcode} Stockpile Parameters",
                "description": f"Input parameters for MITRE Stockpile {tcode} abilities.",
                "scope": "local",
                "used_by_tcodes": [tcode],
                "tags": clean_tags,
            }
        )

    chains = [
        {
            "name": script["name"],
            "description": f"Single-step MITRE Stockpile chain for {script['tcode']} - {script['technique_name']}.",
            "package": package_id,
            "tcode": script["tcode"],
            "tactic": tactic_name,
            "script_refs": [script["name"]],
        }
        for script in scripts
    ]
    if len(scripts) > 1:
        chains.append(
            {
                "name": f"STOCKPILE - {tactic_name} - Full Tactic Convenience Chain",
                "description": (
                    f"Convenience collection of all {len(scripts)} converted {tactic_name} scripts. "
                    "This is not an authentic MITRE CALDERA adversary profile or validated operation sequence."
                ),
                "package": package_id,
                "tcode": tcodes[0],
                "tactic": tactic_name,
                "script_refs": [script["name"] for script in scripts],
            }
        )

    return {
        "package_id": package_id,
        "package_name": f"STOCKPILE - {tactic_name} Pack (MITRE)",
        "version": "1.0.0",
        "description": (
            f"MITRE CALDERA Stockpile command-based abilities converted to Morgana-native scripts "
            f"for {tactic_name} ({tactic_id}). CALDERA is not required at runtime."
        ),
        "author": "MITRE (converted by X3M.AI for Morgana)",
        "created": source_date,
        "source": SOURCE_NAME,
        "source_repository": SOURCE_REPOSITORY,
        "source_commit": source_commit,
        "mitre_domain": "enterprise-attack",
        "mitre_tactic": f"{tactic_name} ({tactic_id})",
        "mitre_tactic_name": tactic_name,
        "mitre_tactic_source": tactic_key,
        "mitre_tcodes": tcodes,
        "platform": platforms,
        "prerequisites": [
            "Morgana agent installed on the authorized target",
            "Required Stockpile facts supplied as Morgana tag values",
            "CALDERA and Stockpile are not required at runtime",
        ],
        "license": "Apache-2.0",
        "tag_categories": tag_categories,
        "scripts": scripts,
        "chains": chains,
    }


def catalog_entry(pack: dict[str, Any]) -> dict[str, Any]:
    package_id = pack["package_id"]
    return {
        "package_id": package_id,
        "package_name": pack["package_name"],
        "version": pack["version"],
        "description": pack["description"],
        "mitre_tactic": pack["mitre_tactic"],
        "mitre_tcodes": pack["mitre_tcodes"],
        "script_count": len(pack["scripts"]),
        "chain_count": len(pack["chains"]),
        "platform": pack["platform"],
        "prerequisites": pack["prerequisites"],
        "sentinel_connectors": [],
        "status": "community",
        "source": SOURCE_NAME,
        "source_commit": pack["source_commit"],
        "category": "stockpile",
        "url": f"{CATALOG_BASE_URL}/{package_id}.json",
    }


def update_catalog(packs: list[dict[str, Any]], dry_run: bool) -> tuple[int, int]:
    if not CATALOG_FILE.exists():
        raise FileNotFoundError(f"catalog not found: {CATALOG_FILE}")
    catalog = json.loads(CATALOG_FILE.read_text(encoding="utf-8"))
    existing_ids = {entry.get("package_id") for entry in catalog.get("packs", [])}
    entries = {pack["package_id"]: catalog_entry(pack) for pack in packs}
    new_packs = [
        entries.get(entry.get("package_id"), entry)
        for entry in catalog.get("packs", [])
    ]
    represented = {entry.get("package_id") for entry in new_packs}
    new_packs.extend(entries[package_id] for package_id in sorted(entries) if package_id not in represented)
    catalog["packs"] = new_packs
    source_dates = sorted({str(pack.get("created") or "") for pack in packs if pack.get("created")})
    catalog_dates = [
        str(catalog.get("updated") or ""),
        *source_dates,
        str(datetime.now(timezone.utc).date()),
    ]
    catalog["updated"] = max(date_value for date_value in catalog_dates if date_value)
    if not any(str(package_id).startswith("stockpile-") for package_id in existing_ids):
        version = str(catalog.get("catalog_version") or "1.0.0").split(".")
        try:
            catalog["catalog_version"] = f"{int(version[0])}.{int(version[1]) + 1}.0"
        except (ValueError, IndexError):
            catalog["catalog_version"] = "1.3.0"
    if not dry_run:
        temporary_catalog = CATALOG_FILE.with_suffix(".json.tmp")
        temporary_catalog.write_text(
            json.dumps(catalog, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        os.replace(temporary_catalog, CATALOG_FILE)
    added = sum(1 for package_id in entries if package_id not in existing_ids)
    updated = len(entries) - added
    return added, updated


def build_report(
    state: ConversionState,
    source_commit: str,
    source_date: str,
    packs: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "source": SOURCE_NAME,
        "source_repository": SOURCE_REPOSITORY,
        "source_commit": source_commit,
        "source_commit_date": source_date,
        "generated_at": f"{source_date}T00:00:00+00:00" if source_date != "unknown" else "unknown",
        "summary": {
            "yaml_files_scanned": state.files_scanned,
            "abilities_parsed": state.abilities_parsed,
            "platform_executor_variants": state.variants_discovered,
            "generated_scripts": state.generated_scripts,
            "skipped_variants": state.skipped_variants,
            "errors": state.errors,
            "packs_generated": len(packs),
            "facts_converted": state.facts_converted,
            "abilities_with_facts": len(state.abilities_with_facts),
            "abilities_with_cleanup": len(state.abilities_with_cleanup),
            "abilities_with_parsers": len(state.abilities_with_parsers),
            "abilities_with_requirements": len(state.abilities_with_requirements),
            "payload_references": state.payload_references,
            "source_entries_skipped": len(state.skipped_source_entries),
        },
        "platform_counts": dict(sorted(state.platform_counts.items())),
        "executor_counts": dict(sorted(state.executor_counts.items())),
        "encountered_platforms": dict(sorted(state.encountered_platforms.items())),
        "encountered_executors": dict(sorted(state.encountered_executors.items())),
        "packs": [
            {
                "package_id": pack["package_id"],
                "script_count": len(pack["scripts"]),
                "chain_count": len(pack["chains"]),
                "platforms": pack["platform"],
            }
            for pack in packs
        ],
        "unsupported_executors": state.unsupported_executors,
        "unsupported_platforms": state.unsupported_platforms,
        "unsupported_build_variants": state.unsupported_build_variants,
        "unsafe_runtime_variants": state.unsafe_runtime_variants,
        "payload_issues": state.payload_issues,
        "parser_metadata": state.parser_metadata,
        "requirement_metadata": state.requirement_metadata,
        "malformed_files": state.malformed_files,
        "skipped_source_entries": state.skipped_source_entries,
        "invalid_variants": state.invalid_variants,
        "errors": state.errors_detail,
    }


def print_summary(state: ConversionState, packs: list[dict[str, Any]], source_commit: str) -> None:
    print("\n=== MITRE Stockpile Conversion Summary ===")
    print(f"Source commit:                  {source_commit}")
    print(f"YAML files scanned:             {state.files_scanned}")
    print(f"Abilities parsed:               {state.abilities_parsed}")
    print(f"Platform/executor variants:     {state.variants_discovered}")
    print(f"Generated scripts:              {state.generated_scripts}")
    print(f"Skipped variants:               {state.skipped_variants}")
    print(f"Errors:                         {state.errors}")
    print(f"Packs generated:                {len(packs)}")
    print("\nPlatforms:")
    for name, count in sorted(state.platform_counts.items()):
        print(f"  {name:<28} {count}")
    print("Executors:")
    for name, count in sorted(state.executor_counts.items()):
        print(f"  {name:<28} {count}")
    print("CALDERA features:")
    print(f"  abilities with facts          {len(state.abilities_with_facts)}")
    print(f"  facts converted               {state.facts_converted}")
    print(f"  abilities with cleanup        {len(state.abilities_with_cleanup)}")
    print(f"  abilities with parsers        {len(state.abilities_with_parsers)}")
    print(f"  abilities with requirements   {len(state.abilities_with_requirements)}")
    print(f"  payload references            {state.payload_references}")
    print("Unsupported/skipped:")
    print(f"  build variants                {len(state.unsupported_build_variants)}")
    print(f"  unsafe runtime dependencies   {len(state.unsafe_runtime_variants)}")
    print(f"  unsupported executors         {len(state.unsupported_executors)}")
    print(f"  unsupported platforms         {len(state.unsupported_platforms)}")
    print(f"  payload-dependent variants    {len(state.payload_issues)}")
    print(f"  invalid variants              {len(state.invalid_variants)}")
    print(f"  source entries skipped        {len(state.skipped_source_entries)}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Convert MITRE CALDERA Stockpile abilities to Morgana Excalibur packs"
    )
    parser.add_argument("--stockpile-dir", required=True, help="Path to the MITRE Stockpile checkout")
    parser.add_argument("--out-dir", default=str(DEFAULT_OUTPUT_DIR), help="Pack output directory")
    parser.add_argument("--tactic", help="Filter by Stockpile tactic name, tactic ID, or Morgana slug")
    parser.add_argument("--platform", choices=["windows", "linux", "macos"], help="Filter output platform")
    parser.add_argument("--dry-run", action="store_true", help="Parse and validate without writing files")
    parser.add_argument("--no-update-catalog", action="store_true", help="Do not update catalog.json")
    parser.add_argument("--max-per-pack", type=int, default=0, help="Maximum scripts per pack (0 = unlimited)")
    parser.add_argument(
        "--allow-large-reduction",
        action="store_true",
        help="Allow a full conversion to reduce the existing Stockpile script count by more than 25%",
    )
    parser.add_argument("--verbose", action="store_true", help="Print every parsed source path")
    args = parser.parse_args()

    stockpile_dir = Path(args.stockpile_dir).resolve()
    abilities_dir = stockpile_dir / "data" / "abilities"
    output_dir = Path(args.out_dir).resolve()
    if not abilities_dir.is_dir():
        print(f"[ERROR] Stockpile abilities directory not found: {abilities_dir}")
        return 1

    source_commit, source_date = source_identity(stockpile_dir)
    log(f"Source commit: {source_commit}")
    yaml_files = sorted([*abilities_dir.rglob("*.yml"), *abilities_dir.rglob("*.yaml")])
    state = ConversionState(files_scanned=len(yaml_files))
    log(f"Found {len(yaml_files)} YAML files")

    requested_tactic = str(args.tactic or "").strip().lower()
    grouped_scripts: dict[str, list[dict[str, Any]]] = defaultdict(list)
    grouped_tags: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
    group_meta: dict[str, tuple[str, str, str, str]] = {}
    names_by_tactic: dict[str, set[str]] = defaultdict(set)

    for source_path in yaml_files:
        relative_path = source_path.relative_to(stockpile_dir).as_posix()
        if args.verbose:
            log(f"Parsing {relative_path}")
        for ability in iter_abilities(source_path, state, relative_path):
            ability_id = str(ability.get("id") or "").strip()
            ability_name = str(ability.get("name") or "").strip()
            technique = ability.get("technique") if isinstance(ability.get("technique"), dict) else {}
            tcode = str(technique.get("attack_id") or ability.get("technique_id") or "").strip().upper()
            technique_name = str(technique.get("name") or ability.get("technique_name") or "").strip()
            platforms = ability.get("platforms")
            tactic_info = resolve_tactic(str(ability.get("tactic") or ""), source_path)
            if tactic_info and requested_tactic:
                tactic_key, tactic_id, tactic_name, tactic_slug = tactic_info
                if requested_tactic not in {
                    tactic_key,
                    tactic_id.lower(),
                    tactic_slug,
                    tactic_name.lower(),
                }:
                    continue
            missing = [
                name
                for name, value in (
                    ("id", ability_id),
                    ("name", ability_name),
                    ("technique.attack_id", tcode),
                    ("platforms", platforms),
                )
                if not value
            ]
            if missing or not isinstance(platforms, dict) or not VALID_TCODE.match(tcode):
                state.skipped_source_entries.append(
                    {
                        "source_path": relative_path,
                        "ability": ability_id,
                        "error": f"invalid ability; missing/invalid: {', '.join(missing) or 'tcode/platforms'}",
                    }
                )
                continue
            if not tactic_info:
                state.skipped_source_entries.append(
                    {"source_path": relative_path, "ability": ability_id, "error": "unsupported tactic"}
                )
                continue

            tactic_key, tactic_id, tactic_name, tactic_slug = tactic_info

            state.abilities_parsed += 1
            ability["_tcode"] = tcode
            ability["_technique_name"] = technique_name or ability_name
            group_meta[tactic_key] = (tactic_key, tactic_id, tactic_name, tactic_slug)

            for raw_platform_group, executor_blocks in sorted(platforms.items()):
                if not isinstance(executor_blocks, dict):
                    state.invalid_variants.append(
                        {
                            "source_path": relative_path,
                            "ability": ability_id,
                            "platform": raw_platform_group,
                            "error": "platform executor block is not an object",
                        }
                    )
                    continue
                raw_platforms = [part.strip() for part in str(raw_platform_group).split(",") if part.strip()]
                for raw_executor_group, executor_definition in sorted(executor_blocks.items()):
                    raw_executors = [
                        part.strip() for part in str(raw_executor_group).split(",") if part.strip()
                    ]
                    normalized_variants: set[tuple[str, str]] = set()
                    for raw_platform in raw_platforms:
                        for raw_executor in raw_executors:
                            identity = (
                                PLATFORMS.get(raw_platform.lower(), raw_platform.lower()),
                                EXECUTORS.get(raw_executor.lower(), raw_executor.lower()),
                            )
                            if identity in normalized_variants:
                                continue
                            normalized_variants.add(identity)
                            converted = convert_variant(
                                ability,
                                source_path,
                                relative_path,
                                raw_platform,
                                raw_executor,
                                executor_definition,
                                tactic_id,
                                tactic_name,
                                tactic_slug,
                                state,
                                args.platform,
                                names_by_tactic[tactic_key],
                            )
                            if not converted:
                                continue
                            script, tags = converted
                            grouped_scripts[tactic_key].append(script)
                            for tag in tags:
                                existing = grouped_tags[tactic_key].get(tag["key"])
                                if existing and existing.get("_fact") != tag.get("_fact"):
                                    digest = hashlib.sha1(
                                        f"{ability_id}:{tag['_fact']}".encode("utf-8")
                                    ).hexdigest()[:7]
                                    old_key = tag["key"]
                                    new_key = f"{old_key[:56]}_{digest}"[:64]
                                    script["command"] = script["command"].replace(
                                        f"#{{{old_key}}}", f"#{{{new_key}}}"
                                    )
                                    script["cleanup_command"] = script["cleanup_command"].replace(
                                        f"#{{{old_key}}}", f"#{{{new_key}}}"
                                    )
                                    script["required_tags"] = [
                                        new_key if key == old_key else key for key in script["required_tags"]
                                    ]
                                    tag["key"] = new_key
                                grouped_tags[tactic_key][tag["key"]] = tag

    packs: list[dict[str, Any]] = []
    for tactic_key, metadata in sorted(group_meta.items(), key=lambda item: item[1][1]):
        scripts = sorted(grouped_scripts[tactic_key], key=lambda script: (script["tcode"], script["name"]))
        if args.max_per_pack > 0:
            scripts = scripts[: args.max_per_pack]
        if not scripts:
            continue
        pack = build_pack(
            *metadata,
            scripts,
            grouped_tags[tactic_key],
            source_commit,
            source_date,
        )
        validation_errors = validate_pack(pack)
        if validation_errors:
            state.errors += len(validation_errors)
            state.errors_detail.extend(
                {"package_id": pack["package_id"], "error": error}
                for error in validation_errors
            )
            warning(f"Pack {pack['package_id']} failed validation ({len(validation_errors)} errors)")
            continue
        packs.append(pack)

    report = build_report(state, source_commit, source_date, packs)
    print_summary(state, packs, source_commit)

    if state.errors:
        warning(f"Conversion failed with {state.errors} hard errors; no files written")
        return 1

    is_full_conversion = not requested_tactic and not args.platform and args.max_per_pack == 0
    expected_package_ids = {
        f"stockpile-{tactic_slug}-v1"
        for _tactic_id, _tactic_name, tactic_slug in TACTICS.values()
    }
    generated_package_ids = {pack["package_id"] for pack in packs}
    if is_full_conversion and generated_package_ids != expected_package_ids:
        missing = sorted(expected_package_ids - generated_package_ids)
        extra = sorted(generated_package_ids - expected_package_ids)
        warning(f"Incomplete full conversion; no files written. Missing={missing}, extra={extra}")
        return 1
    if is_full_conversion and CATALOG_FILE.exists() and not args.allow_large_reduction:
        existing_catalog = json.loads(CATALOG_FILE.read_text(encoding="utf-8"))
        previous_total = sum(
            int(entry.get("script_count") or 0)
            for entry in existing_catalog.get("packs", [])
            if str(entry.get("package_id") or "").startswith("stockpile-")
        )
        generated_total = sum(len(pack["scripts"]) for pack in packs)
        if previous_total and generated_total < previous_total * 0.75:
            warning(
                f"Generated scripts dropped from {previous_total} to {generated_total} (>25%); "
                "no files written. Review diagnostics and rerun with --allow-large-reduction if intentional."
            )
            return 1

    if not args.dry_run:
        output_dir.mkdir(parents=True, exist_ok=True)
        for pack in packs:
            output_path = output_dir / f"{pack['package_id']}.json"
            temporary_path = output_path.with_suffix(".json.tmp")
            temporary_path.write_text(
                json.dumps(pack, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
            )
            os.replace(temporary_path, output_path)
            log(f"Wrote {output_path.name}: {len(pack['scripts'])} scripts, {len(pack['chains'])} chains")
        report_path = output_dir / "conversion-report.json"
        temporary_report_path = report_path.with_suffix(".json.tmp")
        temporary_report_path.write_text(
            json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        os.replace(temporary_report_path, report_path)
        log("Wrote conversion-report.json")

    if packs and not args.no_update_catalog:
        added, updated = update_catalog(packs, args.dry_run)
        log(f"catalog.json: {added} added, {updated} updated{' (dry run)' if args.dry_run else ''}")

    return 0 if packs else 1


if __name__ == "__main__":
    raise SystemExit(main())
