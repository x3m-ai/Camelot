#!/usr/bin/env python3
"""Conservative exact, normalized, and derivative Frida source analysis."""

from __future__ import annotations

import re
from collections import defaultdict
from difflib import SequenceMatcher
from typing import Iterable

from frida_sources import FridaSource, sha256


def normalize_source(source: str) -> str:
    text = source.replace("\r\n", "\n").replace("\r", "\n")
    lines = [line.rstrip() for line in text.split("\n")]
    lines = [line for line in lines if not re.match(r"^\s*//", line)]
    text = "\n".join(lines).strip()
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text


def token_fingerprint(source: str) -> str:
    normalized = normalize_source(source)
    tokens = re.findall(r"[A-Za-z_$][\w$]*|\d+|===|!==|==|!=|=>|[{}()[\].,;:+*/%-]", normalized)
    return " ".join(tokens)


def deduplicate(sources: Iterable[FridaSource]) -> tuple[list[FridaSource], dict]:
    ordered = sorted(sources, key=lambda item: (item.quality_tier, item.source_id.lower()))
    exact: dict[str, FridaSource] = {}
    normalized: dict[str, FridaSource] = {}
    canonical: list[FridaSource] = []
    duplicate_groups: dict[str, dict[str, list[str] | str]] = {}
    exact_count = normalized_count = 0
    for source in ordered:
        normalized_code = normalize_source(source.source_code)
        source.normalized_hash = sha256(normalized_code)
        if source.source_hash in exact:
            source.status = "exact_duplicate"
            source.duplicate_of = exact[source.source_hash].source_id
            exact_count += 1
            group = duplicate_groups.setdefault(source.duplicate_of, {"canonical": source.duplicate_of, "exact_duplicates": [], "normalized_duplicates": [], "derivatives": []})
            group["exact_duplicates"].append(source.source_id)
            continue
        if source.normalized_hash in normalized:
            source.status = "normalized_duplicate"
            source.duplicate_of = normalized[source.normalized_hash].source_id
            normalized_count += 1
            group = duplicate_groups.setdefault(source.duplicate_of, {"canonical": source.duplicate_of, "exact_duplicates": [], "normalized_duplicates": [], "derivatives": []})
            group["normalized_duplicates"].append(source.source_id)
            exact[source.source_hash] = source
            continue
        exact[source.source_hash] = source
        normalized[source.normalized_hash] = source
        source.status = "canonical"
        canonical.append(source)

    derivative_count = 0
    buckets: dict[tuple, list[FridaSource]] = defaultdict(list)
    for source in canonical:
        length_band = len(source.source_code) // 1000
        key = (source.target_platform, source.primary_behavior, tuple(source.frida_apis), length_band)
        buckets[key].append(source)
    for bucket in buckets.values():
        if len(bucket) < 2 or len(bucket) > 120:
            continue
        fingerprints = {source.source_id: token_fingerprint(source.source_code) for source in bucket}
        for index, source in enumerate(bucket):
            for candidate in bucket[:index]:
                left, right = fingerprints[source.source_id], fingerprints[candidate.source_id]
                if min(len(left), len(right)) < 200:
                    continue
                ratio = SequenceMatcher(None, left, right, autojunk=True).quick_ratio()
                if ratio >= 0.94:
                    source.derived_from = candidate.source_id
                    source.status = "modified-derivative"
                    derivative_count += 1
                    group = duplicate_groups.setdefault(candidate.source_id, {"canonical": candidate.source_id, "exact_duplicates": [], "normalized_duplicates": [], "derivatives": []})
                    group["derivatives"].append(source.source_id)
                    break

    report = {
        "raw_sources": len(ordered), "published": len(canonical),
        "exact_duplicates": exact_count, "normalized_duplicates": normalized_count,
        "meaningful_derivatives_retained": derivative_count,
        "groups": [duplicate_groups[key] for key in sorted(duplicate_groups)],
    }
    return canonical, report