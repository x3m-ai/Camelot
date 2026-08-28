#!/usr/bin/env python3
"""Normalize every explicit GTFOBins function/snippet/context variant."""

from __future__ import annotations

import hashlib
import re
from copy import deepcopy
from pathlib import Path
from typing import Any

import yaml

from convert_lotl import (
    NormalizedProcedure, ProviderStats, classify_risk, compact, make_tag,
)

GTFOBINS_REPOSITORY = "https://github.com/GTFOBins/GTFOBins.github.io"
REPLACEMENTS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"/path/to/input-file"), "input_file"),
    (re.compile(r"/path/to/output-file"), "output_file"),
    (re.compile(r"/path/to/temp-file"), "local_path"),
    (re.compile(r"/path/to/lib\.so"), "payload_path"),
    (re.compile(r"\b(?:attacker|victim)\.com\b", re.I), "remote_host"),
    (re.compile(r"\b12345\b"), "remote_port"),
    (re.compile(r"\bCOMMAND\b"), "command"),
    (re.compile(r"\bURL\b"), "remote_url"),
    (re.compile(r"\bFILE\b"), "local_path"),
    (re.compile(r"\bDATA\b"), "data"),
)
URL_HOST = re.compile(r"(?P<scheme>https?://)(?P<host>(?!#\{)[a-z0-9.-]+)(?P<port>:\d+)?", re.I)
IPV4 = re.compile(r"(?<![\w.])(?:\d{1,3}\.){3}\d{1,3}(?![\w.])")


def normalize_command(command: str) -> tuple[str, list[str], list[Any]]:
    rewritten = command.strip()
    tags: dict[str, Any] = {}
    for pattern, parameter_class in REPLACEMENTS:
        if not pattern.search(rewritten):
            continue
        tag = make_tag("gtfobins", parameter_class, pattern.pattern)
        tags[tag.key] = tag
        rewritten = pattern.sub(f"#{{{tag.key}}}", rewritten)
    remote_host_tag = make_tag("gtfobins", "remote_host", "literal network target")

    def replace_url_host(match: re.Match[str]) -> str:
        host = match.group("host")
        if host.lower() == "localhost" or host.startswith("127.") or host == "0.0.0.0":
            return match.group(0)
        tags[remote_host_tag.key] = remote_host_tag
        return f"{match.group('scheme')}#{{{remote_host_tag.key}}}{match.group('port') or ''}"

    rewritten = URL_HOST.sub(replace_url_host, rewritten)

    def replace_ip(match: re.Match[str]) -> str:
        value = match.group(0)
        if value.startswith("127.") or value == "0.0.0.0":
            return value
        tags[remote_host_tag.key] = remote_host_tag
        return f"#{{{remote_host_tag.key}}}"

    rewritten = IPV4.sub(replace_ip, rewritten)
    return rewritten, sorted(tags), [tags[key] for key in sorted(tags)]


def readiness_for(function: str, context: str, entry: dict[str, Any], command: str) -> tuple[str, list[str]]:
    prerequisites = [f"The `{entry.get('_binary')}` binary must be installed and available to the executing Agent."]
    if context == "sudo":
        prerequisites.append("The operator must preconfigure the documented sudo permission; Morgana does not modify sudoers.")
    elif context == "suid":
        prerequisites.append("The binary must already have the documented SUID ownership and mode; Morgana does not configure SUID bits.")
    elif context == "capabilities":
        prerequisites.append("The required Linux capabilities must already be assigned; Morgana does not configure capabilities.")
    if function in {"reverse-shell", "bind-shell", "upload", "download"} and any(entry.get(key) for key in ("listener", "connector", "sender", "receiver")):
        prerequisites.append("The operator must start and control the documented counterpart infrastructure separately.")
        return "manual_counterpart_required", prerequisites
    comment = str(entry.get("comment") or "").lower()
    if function == "shell" or "interactive" in comment or "terminal" in comment or "tty" in str(entry).lower():
        return "interactive", prerequisites
    if context in {"sudo", "suid", "capabilities"}:
        return "environment_prerequisite", prerequisites
    if "#{" in command:
        return "ready_with_parameters", prerequisites
    return "ready", prerequisites


def load_sources(source_dir: Path, stats: ProviderStats) -> tuple[dict[str, dict[str, Any]], dict[str, Any], dict[str, Any]]:
    functions = yaml.safe_load((source_dir / "_data" / "functions.yml").read_text(encoding="utf-8")) or {}
    contexts = yaml.safe_load((source_dir / "_data" / "contexts.yml").read_text(encoding="utf-8")) or {}
    bins: dict[str, dict[str, Any]] = {}
    for path in sorted((source_dir / "_gtfobins").iterdir()):
        if not path.is_file():
            continue
        stats.source_objects += 1
        try:
            loaded = yaml.safe_load(path.read_text(encoding="utf-8-sig", errors="replace")) or {}
        except (OSError, yaml.YAMLError) as exc:
            stats.errors += 1
            stats.issues.append({"source_path": f"_gtfobins/{path.name}", "status": "error", "reason": str(exc)})
            continue
        if not isinstance(loaded, dict):
            stats.errors += 1
            stats.issues.append({"source_path": f"_gtfobins/{path.name}", "status": "error", "reason": "root is not a mapping"})
            continue
        bins[path.name] = loaded
    return bins, functions, contexts


def expanded_entries(
    binary: str,
    bins: dict[str, dict[str, Any]],
    ancestry: tuple[str, ...] = (),
) -> list[tuple[str, int, dict[str, Any]]]:
    if binary in ancestry:
        return [("__unsupported_inherit__", 0, {
            "_binary": binary,
            "from": binary,
            "reason": f"inheritance cycle: {' -> '.join((*ancestry, binary))}",
            "contexts": {"unknown": None},
        })]
    source_functions = bins[binary].get("functions") or {}
    expanded: list[tuple[str, int, dict[str, Any]]] = []
    for function, entries in source_functions.items():
        if function == "inherit":
            continue
        for index, entry in enumerate(entries or []):
            if isinstance(entry, dict):
                expanded.append((function, index, {**deepcopy(entry), "_binary": binary}))

    for inherit_index, inherit in enumerate(source_functions.get("inherit") or []):
        if not isinstance(inherit, dict):
            continue
        inherited_from = str(inherit.get("from") or "")
        if inherited_from not in bins:
            expanded.append(("__unsupported_inherit__", inherit_index, {**inherit, "_binary": binary}))
            continue
        inherited_contexts = set((inherit.get("contexts") or {}).keys())
        prefix = str(inherit.get("code") or "").strip()
        for function, source_index, inherited_entry in expanded_entries(
            inherited_from, bins, (*ancestry, binary)
        ):
            if function == "__unsupported_inherit__":
                expanded.append((function, source_index, inherited_entry))
                continue
            contexts = inherited_entry.get("contexts") or {}
            matching_contexts = inherited_contexts.intersection(contexts)
            if not matching_contexts:
                continue
            inherited_code = str(inherited_entry.get("code") or "").strip()
            combined = deepcopy(inherited_entry)
            combined["code"] = f"{prefix}\n{inherited_code}".strip()
            combined["contexts"] = {context: contexts[context] for context in sorted(matching_contexts)}
            combined["comment"] = compact(f"{inherit.get('comment') or ''} Inherits {function} behavior from {inherited_from}. {inherited_entry.get('comment') or ''}", 800)
            combined["inherited_from"] = inherited_from
            combined["inheritance_path"] = [binary, *(inherited_entry.get("inheritance_path") or [inherited_from])]
            combined["inherit_index"] = inherit_index
            combined["_binary"] = binary
            expanded.append((function, source_index, combined))
    return expanded


def convert_gtfobins(
    source_dir: Path,
    overrides: dict[str, str],
    category_filter: str | None = None,
    function_filter: str | None = None,
    context_filter: str | None = None,
    verbose: bool = False,
) -> tuple[list[NormalizedProcedure], ProviderStats, list[dict[str, Any]]]:
    stats = ProviderStats()
    procedures: list[NormalizedProcedure] = []
    inventory: list[dict[str, Any]] = []
    bins, function_definitions, context_definitions = load_sources(source_dir, stats)
    direct_snippets = sum(
        1 for source in bins.values()
        for function, entries in (source.get("functions") or {}).items()
        if function != "inherit"
        for entry in (entries or []) if isinstance(entry, dict)
    )
    inheritance_entries = sum(
        len((source.get("functions") or {}).get("inherit") or []) for source in bins.values()
    )

    requested_function = function_filter or category_filter
    for binary in sorted(bins):
        source_path = f"_gtfobins/{binary}"
        for function, snippet_index, entry in expanded_entries(binary, bins):
            stats.source_entries += 1
            if function == "__unsupported_inherit__":
                contexts = entry.get("contexts") or {"unknown": None}
                stats.raw_variants += len(contexts)
                stats.unsupported += len(contexts)
                inventory.append({"provider": "gtfobins", "source_path": source_path, "status": "unsupported", "reason": f"inherit source not found: {entry.get('from')}"})
                continue
            if requested_function and requested_function != function:
                contexts = entry.get("contexts") or {}
                stats.raw_variants += len(contexts)
                stats.skipped += len(contexts)
                continue
            function_definition = function_definitions.get(function)
            if not isinstance(function_definition, dict):
                contexts = entry.get("contexts") or {"unknown": None}
                stats.raw_variants += len(contexts)
                stats.unsupported += len(contexts)
                inventory.append({"provider": "gtfobins", "source_path": source_path, "function": function, "status": "unsupported", "reason": "unknown function"})
                continue
            contexts = entry.get("contexts") or {}
            if not isinstance(contexts, dict) or not contexts:
                stats.raw_variants += 1
                stats.unsupported += 1
                inventory.append({"provider": "gtfobins", "source_path": source_path, "function": function, "status": "unsupported", "reason": "missing explicit contexts"})
                continue
            for context, context_value in contexts.items():
                stats.context_expansions += 1
                stats.raw_variants += 1
                if context_filter and context_filter != context:
                    stats.skipped += 1
                    continue
                if context not in context_definitions:
                    stats.unsupported += 1
                    inventory.append({"provider": "gtfobins", "source_path": source_path, "function": function, "context": context, "status": "unsupported", "reason": "unknown context"})
                    continue
                context_metadata = context_value if isinstance(context_value, dict) else {}
                command = str(context_metadata.get("code") or entry.get("code") or "").strip()
                if not command:
                    stats.unsupported += 1
                    inventory.append({"provider": "gtfobins", "source_path": source_path, "function": function, "context": context, "status": "unsupported", "reason": "blank effective code"})
                    continue
                rewritten, required_tags, tags = normalize_command(command)
                readiness, prerequisites = readiness_for(function, context, entry, rewritten)
                source_tcodes = [str(value).upper() for value in function_definition.get("mitre") or []]
                primary_tcode = source_tcodes[0] if source_tcodes else "T0000"
                inheritance_path = entry.get("inheritance_path") or []
                inheritance_identity = ">".join(inheritance_path)
                source_id = f"gtfobins:{binary}:{function}:{snippet_index}:{context}:{entry.get('inherit_index', '')}:{inheritance_identity}"
                suffix = hashlib.sha1(source_id.encode("utf-8")).hexdigest()[:7]
                function_label = str(function_definition.get("label") or function.replace("-", " ").title())
                name = f"GTFOBINS - {primary_tcode} - {binary} - {function_label} - {context.title()} [{suffix}]"
                risk = classify_risk("gtfobins", function, rewritten, context, overrides)
                description = compact(
                    f"{function_definition.get('description') or function_label} Binary: {binary}. "
                    f"Context: {context_definitions[context].get('label', context)}. {entry.get('comment') or ''}",
                    700,
                )
                extra_metadata = {
                    key: value for key, value in entry.items()
                    if key not in {"code", "contexts", "comment", "_binary"}
                }
                procedure = NormalizedProcedure(
                    provider="gtfobins",
                    source_id=source_id,
                    source_name=binary,
                    name=name,
                    platform="linux",
                    executor="bash",
                    command=rewritten,
                    primary_tcode=primary_tcode,
                    source_tcodes=source_tcodes,
                    category=function,
                    context=context,
                    risk=risk,
                    readiness=readiness,
                    description=description,
                    required_tags=required_tags,
                    tags=tags,
                    prerequisites=prerequisites,
                    source_metadata={
                        "source_file": source_path,
                        "source_documentation": f"{GTFOBINS_REPOSITORY}/blob/master/{source_path}",
                        "source_bin": binary,
                        "function": function,
                        "function_label": function_label,
                        "snippet_index": snippet_index,
                        "context": context,
                        "context_description": context_definitions[context].get("description"),
                        "inherited_from": entry.get("inherited_from"),
                        "inheritance_path": inheritance_path,
                        "interactive": readiness == "interactive",
                        "manual_prerequisite": readiness == "manual_counterpart_required",
                        "function_metadata": function_definition.get("extra") or {},
                        "context_metadata": context_metadata,
                        "procedure_metadata": extra_metadata,
                        "operator_notes": {
                            key: entry.get(key) for key in ("listener", "connector", "sender", "receiver") if entry.get(key)
                        },
                    },
                )
                procedures.append(procedure)
                stats.counts_by_category[function] += 1
                stats.counts_by_context[context] += 1
                stats.counts_by_tcode[primary_tcode] += 1
                stats.counts_by_readiness[readiness] += 1
                inventory.append({
                    "provider": "gtfobins", "source_id": source_id, "source_path": source_path,
                    "source_bin": binary, "function": function, "snippet_index": snippet_index,
                    "context": context, "source_tcodes": source_tcodes, "readiness": readiness,
                    "inherited_from": entry.get("inherited_from"), "inheritance_path": inheritance_path,
                    "status": "published",
                })
                if verbose:
                    print(f"[GTFOBINS] {binary} {function} {snippet_index} {context}")
    stats.metrics = {
        "bin_files_scanned": len(bins),
        "function_definitions": len(function_definitions),
        "context_definitions": len(context_definitions),
        "direct_snippet_entries": direct_snippets,
        "inheritance_entries": inheritance_entries,
        "effective_snippet_entries": stats.source_entries,
    }
    return procedures, stats, inventory