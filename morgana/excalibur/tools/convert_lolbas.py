#!/usr/bin/env python3
"""Normalize every usable LOLBAS Commands[] entry into a Morgana procedure."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any

import yaml

from convert_lotl import (
    NormalizedProcedure, ProviderStats, classify_risk, compact, make_tag, slug,
)

LOLBAS_REPOSITORY = "https://github.com/LOLBAS-Project/LOLBAS"
SOURCE_TOKEN = re.compile(r"\{([^{}]+)\}")
URL_HOST = re.compile(r"(?P<scheme>https?://)(?P<host>(?!#\{)[a-z0-9.-]+)(?P<port>:\d+)?", re.I)
IPV4 = re.compile(r"(?<![\w.])(?:\d{1,3}\.){3}\d{1,3}(?![\w.])")


def parameter_class(token: str, category: str, occurrence: int) -> str:
    base, _, suffix = token.upper().partition(":")
    category_lower = category.lower()
    if base == "CMD":
        return "command"
    if base == "REMOTEURL":
        return "remote_url"
    if base == "PATH_SMB":
        return "remote_host"
    if base in {"PORT", "REMOTEPORT"}:
        return "remote_port"
    if base in {"USER", "USERNAME"}:
        return "username"
    if base == "DOMAIN":
        return "domain"
    if base in {"SERVICE", "SERVICENAME"}:
        return "service"
    if base.startswith("REG"):
        return "registry_path"
    if base.startswith("PATH"):
        if "download" in category_lower or "copy" in category_lower:
            return "output_file" if occurrence else "input_file"
        if suffix in {".BASE64", ".HEX", ".CAB"} and occurrence:
            return "output_file"
        if suffix in {".EXE", ".DLL", ".PS1", ".SCT", ".XML", ".XSL", ".INF", ".CS"}:
            return "payload_path"
        return "local_path"
    return "argument"


def normalize_command(command: str, category: str) -> tuple[str, list[str], list[Any], list[str]]:
    tags: dict[str, Any] = {}
    required: list[str] = []
    token_counts: dict[str, int] = {}
    prerequisites: list[str] = []

    def replace(match: re.Match[str]) -> str:
        token = match.group(1)
        base = token.split(":", 1)[0].upper()
        occurrence = token_counts.get(base, 0)
        token_counts[base] = occurrence + 1
        kind = parameter_class(token, category, occurrence)
        tag = make_tag("lolbas", kind, token)
        if tag.key in tags and token not in tags[tag.key].description:
            digest = hashlib.sha1(token.encode("utf-8")).hexdigest()[:7]
            tag.key = f"{tag.key[:56]}_{digest}"[:64]
        tags[tag.key] = tag
        if tag.key not in required:
            required.append(tag.key)
        return f"#{{{tag.key}}}"

    rewritten = SOURCE_TOKEN.sub(replace, command.strip())
    remote_host_tag = make_tag("lolbas", "remote_host", "literal network target")

    def replace_url_host(match: re.Match[str]) -> str:
        host = match.group("host")
        if host.lower() == "localhost" or host.startswith("127.") or host == "0.0.0.0":
            return match.group(0)
        tags[remote_host_tag.key] = remote_host_tag
        if remote_host_tag.key not in required:
            required.append(remote_host_tag.key)
        return f"{match.group('scheme')}#{{{remote_host_tag.key}}}{match.group('port') or ''}"

    rewritten = URL_HOST.sub(replace_url_host, rewritten)

    def replace_ip(match: re.Match[str]) -> str:
        value = match.group(0)
        if value.startswith("127.") or value == "0.0.0.0":
            return value
        tags[remote_host_tag.key] = remote_host_tag
        if remote_host_tag.key not in required:
            required.append(remote_host_tag.key)
        return f"#{{{remote_host_tag.key}}}"

    rewritten = IPV4.sub(replace_ip, rewritten)
    if "REMOTEURL" in command.upper() or "PATH_SMB" in command.upper():
        prerequisites.append("Operator-controlled remote infrastructure must be reachable from the authorized target.")
    return rewritten, required, list(tags.values()), prerequisites


def executor_for(command: str) -> str:
    value = command.lstrip().lower()
    if value.startswith(("powershell ", "powershell.exe ", "pwsh ")):
        return "powershell"
    return "cmd"


def convert_lolbas(
    source_dir: Path,
    overrides: dict[str, str],
    category_filter: str | None = None,
    _function_filter: str | None = None,
    _context_filter: str | None = None,
    verbose: bool = False,
) -> tuple[list[NormalizedProcedure], ProviderStats, list[dict[str, Any]]]:
    stats = ProviderStats()
    procedures: list[NormalizedProcedure] = []
    inventory: list[dict[str, Any]] = []
    yml_dir = source_dir / "yml"

    for path in sorted([*yml_dir.rglob("*.yml"), *yml_dir.rglob("*.yaml")]):
        source_path = str(path.relative_to(source_dir)).replace("\\", "/")
        source_directory = path.relative_to(yml_dir).parts[0]
        stats.source_objects += 1
        stats.counts_by_source_directory[source_directory] += 1
        try:
            loaded = yaml.safe_load(path.read_text(encoding="utf-8-sig", errors="replace"))
        except (OSError, yaml.YAMLError) as exc:
            stats.errors += 1
            stats.issues.append({"source_path": source_path, "status": "error", "reason": str(exc)})
            continue
        objects = loaded if isinstance(loaded, list) else [loaded]
        for object_index, source in enumerate(objects):
            if not isinstance(source, dict):
                stats.errors += 1
                stats.issues.append({"source_path": source_path, "status": "error", "reason": "object is not a mapping"})
                continue
            source_name = str(source.get("Name") or path.stem).strip()
            full_paths = [item.get("Path") for item in (source.get("Full_Path") or []) if isinstance(item, dict) and item.get("Path")]
            resources = [item.get("Link") for item in (source.get("Resources") or []) if isinstance(item, dict) and item.get("Link")]
            detections = source.get("Detection") or []
            aliases = source.get("Aliases") or []
            commands = source.get("Commands") or []
            if not isinstance(commands, list):
                stats.errors += 1
                stats.issues.append({"source_path": source_path, "status": "error", "reason": "Commands is not a list"})
                continue
            for command_index, entry in enumerate(commands):
                stats.source_entries += 1
                stats.raw_variants += 1
                if not isinstance(entry, dict):
                    stats.unsupported += 1
                    inventory.append({"provider": "lolbas", "source_path": source_path, "command_index": command_index, "status": "unsupported", "reason": "command entry is not a mapping"})
                    continue
                category = str(entry.get("Category") or "Uncategorized").strip()
                if category_filter and slug(category_filter) != slug(category):
                    stats.skipped += 1
                    inventory.append({"provider": "lolbas", "source_path": source_path, "command_index": command_index, "status": "skipped", "reason": "category filter"})
                    continue
                command = str(entry.get("Command") or "").strip()
                tcode = str(entry.get("MitreID") or "T0000").strip().upper()
                if not command:
                    stats.unsupported += 1
                    inventory.append({"provider": "lolbas", "source_path": source_path, "command_index": command_index, "status": "unsupported", "reason": "blank command"})
                    continue
                rewritten, required_tags, tags, prerequisites = normalize_command(command, category)
                privilege = str(entry.get("Privileges") or "Unspecified").strip()
                if privilege.lower() not in {"user", "unspecified"}:
                    prerequisites.append(f"Required source privilege: {privilege}.")
                operating_system = str(entry.get("OperatingSystem") or "Windows").strip()
                source_id = f"lolbas:{source_path}:{object_index}:{command_index}"
                short_usecase = compact(entry.get("Usecase") or entry.get("Description") or category, 90)
                identity_suffix = hashlib.sha1(source_id.encode("utf-8")).hexdigest()[:7]
                name = f"LOLBAS - {tcode} - {source_name} - {category} - {short_usecase} [{identity_suffix}]"
                readiness = "ready_with_parameters" if required_tags else "ready"
                risk = classify_risk("lolbas", category, rewritten, "all", overrides)
                description = compact(
                    f"{source.get('Description') or source_name}. {entry.get('Description') or ''} "
                    f"Use case: {entry.get('Usecase') or category}. Privilege: {privilege}.",
                    700,
                )
                procedure = NormalizedProcedure(
                    provider="lolbas",
                    source_id=source_id,
                    source_name=source_name,
                    name=name,
                    platform="windows",
                    executor=executor_for(rewritten),
                    command=rewritten,
                    primary_tcode=tcode,
                    source_tcodes=[tcode] if tcode != "T0000" else [],
                    category=category,
                    context="all",
                    risk=risk,
                    readiness=readiness,
                    description=description,
                    required_tags=required_tags,
                    tags=tags,
                    prerequisites=prerequisites,
                    source_metadata={
                        "source_file": source_path,
                        "source_documentation": f"{LOLBAS_REPOSITORY}/blob/master/{source_path}",
                        "source_directory": source_directory,
                        "source_name": source_name,
                        "command_index": command_index,
                        "category": category,
                        "usecase": entry.get("Usecase"),
                        "privileges": privilege,
                        "operating_system": operating_system,
                        "source_mitre_id": tcode,
                        "full_paths": full_paths,
                        "aliases": aliases,
                        "resources": resources,
                        "detection": detections,
                        "tags": entry.get("Tags") or [],
                    },
                )
                procedures.append(procedure)
                stats.counts_by_category[category] += 1
                stats.counts_by_context["all"] += 1
                stats.counts_by_tcode[tcode] += 1
                stats.counts_by_readiness[readiness] += 1
                stats.counts_by_privilege[privilege] += 1
                inventory.append({
                    "provider": "lolbas", "source_id": source_id, "source_path": source_path,
                    "source_name": source_name, "command_index": command_index, "category": category,
                    "tcode": tcode, "privilege": privilege, "readiness": readiness, "status": "published",
                })
                if verbose:
                    print(f"[LOLBAS] {source_name} command {command_index}: {category} {tcode}")
    stats.metrics = {
        "yaml_files_scanned": stats.source_objects,
        "objects": stats.source_objects,
        "commands_discovered": stats.source_entries,
    }
    return procedures, stats, inventory