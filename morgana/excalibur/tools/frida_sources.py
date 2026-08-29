#!/usr/bin/env python3
"""Common source model and registry helpers for Frida mobile ingestion."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class FridaSource:
    source_provider: str
    source_id: str
    title: str
    description: str
    source_code: str
    source_url: str
    source_hash: str
    license: str
    license_source: str
    distribution_status: str
    quality_tier: str
    source_metadata: dict[str, Any] = field(default_factory=dict)
    target_platform: str = "other"
    frameworks: list[str] = field(default_factory=list)
    scope: str = "research-snippet"
    behaviors: list[str] = field(default_factory=list)
    primary_behavior: str = "other"
    frida_apis: list[str] = field(default_factory=list)
    compatibility_status: str = "requires-review"
    source_tcodes: list[str] = field(default_factory=list)
    primary_tcode: str = "T0000"
    risk: str = "observe"
    readiness: str = "ready_with_target"
    status: str = "discovered"
    duplicate_of: str | None = None
    derived_from: str | None = None
    transformations: list[str] = field(default_factory=list)
    normalized_hash: str = ""

    def inventory(self, include_source: bool = False) -> dict[str, Any]:
        value = asdict(self)
        if not include_source:
            value.pop("source_code", None)
        value["source_bytes"] = len(self.source_code.encode("utf-8"))
        return value


def sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def compact(value: Any, maximum: int = 700) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    return text if len(text) <= maximum else f"{text[:maximum - 3].rstrip()}..."


def load_registry(path: Path) -> dict[str, Any]:
    registry = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(registry, dict) or not isinstance(registry.get("sources"), list):
        raise ValueError("Frida source registry must contain a sources array")
    ids = [source.get("id") for source in registry["sources"]]
    if not ids or any(not value for value in ids) or len(ids) != len(set(ids)):
        raise ValueError("Frida source registry IDs must be non-empty and unique")
    return registry


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")