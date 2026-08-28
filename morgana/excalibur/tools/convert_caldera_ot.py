#!/usr/bin/env python3
"""Convert official MITRE CALDERA for OT plugins into Morgana packs.

This tool only reads YAML and local payload bytes. It never executes abilities,
payloads, build instructions, cleanup commands, or upstream source code.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import quote

try:
    import yaml
except ImportError:
    print("[ERROR] PyYAML is required. Run: python -m pip install pyyaml")
    raise SystemExit(1)


TOOLS_DIR = Path(__file__).resolve().parent
EXCALIBUR_DIR = TOOLS_DIR.parent
DEFAULT_OUTPUT_DIR = EXCALIBUR_DIR / "ot"
CATALOG_FILE = EXCALIBUR_DIR / "catalog.json"
OVERRIDES_FILE = TOOLS_DIR / "caldera_ot_risk_overrides.json"
SOURCE_NAME = "mitre-caldera-ot"
SOURCE_REPOSITORY = "https://github.com/mitre/caldera-ot"
CATALOG_BASE_URL = (
    "https://raw.githubusercontent.com/x3m-ai/Camelot/main/morgana/excalibur/ot"
)
SCRIPT_PREFIX = "OT - "
VALID_TCODE = re.compile(r"^T\d{4}(?:\.\d{3})?$")
FACT_PLACEHOLDER = re.compile(r"#\{([^{}]+)\}")
ASSET_PLACEHOLDER = re.compile(r"\{\{asset:([a-z0-9_]+)\}\}")
SAFE_FILENAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
MAX_ASSET_SIZE = 100 * 1024 * 1024
HIGH_CONSEQUENCE_TACTICS = {"impair-process-control", "inhibit-response-function", "impact"}
RISK_LEVELS = ("observe", "interact", "modify", "disrupt")

PLUGINS: dict[str, dict[str, str]] = {
    "bacnet": {
        "label": "BACnet",
        "repository": "https://github.com/mitre/bacnet",
        "license": "Apache-2.0",
    },
    "dnp3": {
        "label": "DNP3",
        "repository": "https://github.com/mitre/dnp3",
        "license": "Apache-2.0",
    },
    "modbus": {
        "label": "Modbus",
        "repository": "https://github.com/mitre/modbus",
        "license": "Apache-2.0",
    },
    "profinet": {
        "label": "Profinet DCP",
        "repository": "https://github.com/mitre/profinet",
        "license": "Apache-2.0",
    },
    "iec61850": {
        "label": "IEC 61850 MMS",
        "repository": "https://github.com/mitre/iec61850",
        "license": "Apache-2.0",
    },
    "gems": {
        "label": "GEMS",
        "repository": "https://github.com/mitre/gems",
        "license": "Apache-2.0",
    },
}

TACTICS: dict[str, tuple[str, str]] = {
    "collection": ("TA0100", "Collection"),
    "command-and-control": ("TA0101", "Command and Control"),
    "discovery": ("TA0102", "Discovery"),
    "impair-process-control": ("TA0103", "Impair Process Control"),
    "inhibit-response-function": ("TA0107", "Inhibit Response Function"),
    "lateral-movement": ("TA0109", "Lateral Movement"),
    "impact": ("TA0105", "Impact"),
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

PLATFORM_LABELS = {"windows": "Windows", "linux": "Linux", "macos": "macOS"}
EXECUTOR_LABELS = {
    "powershell": "PowerShell",
    "cmd": "CMD",
    "bash": "Bash",
    "python": "Python",
}

CONNECTION_TERMS = {
    "ip", "port", "host", "server", "address", "addr", "mac", "serial", "device",
    "interface", "link", "psm", "user", "password", "username", "credential",
}
WRITE_TERMS = {
    "write", "value", "coil", "register", "setpoint", "output", "parameter", "priority",
    "name", "configuration", "config", "state",
}
CONTROL_TERMS = {
    "control", "operate", "command", "action", "mode", "function", "activation", "restart",
    "enable", "disable", "toggle",
}
READ_TERMS = {"read", "get", "query", "list", "level", "start", "end", "group", "range"}
SENSITIVE_TERMS = {"password", "passwd", "token", "secret", "credential", "private_key", "api_key"}
OBSERVE_TERMS = {"read", "get", "list", "discover", "scan", "query", "report", "poll", "status", "identify"}
MODIFY_TERMS = {"write", "set", "operate", "toggle", "change", "enable", "create", "force"}
DISRUPT_TERMS = {"restart", "disable", "delete", "stop", "crash", "terminate", "shutdown", "reset", "inhibit"}


@dataclass
class ConversionState:
    yaml_files_scanned: int = 0
    abilities_parsed: int = 0
    variants_discovered: int = 0
    generated_scripts: int = 0
    skipped_variants: int = 0
    hard_errors: list[dict[str, Any]] = field(default_factory=list)
    skips: list[dict[str, Any]] = field(default_factory=list)
    payload_references: int = 0
    asset_references: int = 0
    facts_converted: int = 0
    protocol_counts: Counter[str] = field(default_factory=Counter)
    tactic_counts: Counter[str] = field(default_factory=Counter)
    risk_counts: Counter[str] = field(default_factory=Counter)
    platform_counts: Counter[str] = field(default_factory=Counter)
    executor_counts: Counter[str] = field(default_factory=Counter)
    asset_status_counts: Counter[str] = field(default_factory=Counter)
    source_inventory: dict[str, dict[str, Any]] = field(default_factory=dict)
    asset_inventory: dict[str, dict[str, Any]] = field(default_factory=dict)

    def skip(self, detail: dict[str, Any]) -> None:
        self.skipped_variants += 1
        self.skips.append(detail)


def log(message: str) -> None:
    print(f"[CALDERA-OT] {message}")


def sanitize(value: str) -> str:
    return re.sub(r"_+", "_", re.sub(r"[^a-z0-9]+", "_", value.lower())).strip("_")


def trim(value: Any, maximum: int) -> str:
    text = str(value or "").strip()
    return text if len(text) <= maximum else f"{text[:maximum - 3].rstrip()}..."


def command_text(value: Any) -> str:
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, list):
        return "\n".join(str(item) for item in value if item is not None).strip()
    return ""


def git_value(repository: Path, arguments: list[str], fallback: str = "unknown") -> str:
    try:
        completed = subprocess.run(
            ["git", "-C", str(repository), *arguments],
            check=True,
            capture_output=True,
            text=True,
            timeout=20,
        )
        return completed.stdout.strip() or fallback
    except (OSError, subprocess.SubprocessError):
        return fallback


def source_identity(root: Path) -> tuple[dict[str, str], dict[str, str]]:
    commits = {"caldera-ot": git_value(root, ["rev-parse", "HEAD"])}
    dates = {"caldera-ot": git_value(root, ["show", "-s", "--format=%cs", "HEAD"])}
    for protocol in PLUGINS:
        plugin_root = root / protocol
        commits[protocol] = git_value(plugin_root, ["rev-parse", "HEAD"])
        dates[protocol] = git_value(plugin_root, ["show", "-s", "--format=%cs", "HEAD"])
    return commits, dates


def load_overrides(path: Path) -> dict[str, Any]:
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"invalid risk override file {path}: {exc}") from exc
    if not isinstance(loaded, dict):
        raise ValueError("risk override root must be an object")
    abilities = loaded.get("abilities", {})
    rules = loaded.get("rules", [])
    if not isinstance(abilities, dict) or not isinstance(rules, list):
        raise ValueError("risk overrides require object 'abilities' and list 'rules'")
    for key, value in abilities.items():
        if value not in RISK_LEVELS:
            raise ValueError(f"invalid risk override for {key}: {value}")
    return loaded


def iter_abilities(path: Path, state: ConversionState, source_path: str) -> Iterable[dict[str, Any]]:
    try:
        loaded = yaml.safe_load(path.read_text(encoding="utf-8", errors="strict"))
    except (OSError, UnicodeError, yaml.YAMLError) as exc:
        state.hard_errors.append({"source_path": source_path, "error": str(exc)})
        return []
    if isinstance(loaded, dict):
        return [loaded]
    if isinstance(loaded, list):
        invalid = [index for index, item in enumerate(loaded) if not isinstance(item, dict)]
        if invalid:
            state.hard_errors.append(
                {"source_path": source_path, "error": f"non-object YAML entries: {invalid}"}
            )
        return [item for item in loaded if isinstance(item, dict)]
    state.hard_errors.append(
        {"source_path": source_path, "error": f"unexpected YAML root: {type(loaded).__name__}"}
    )
    return []


def iter_variants(ability: dict[str, Any]) -> Iterable[tuple[str, str, dict[str, Any]]]:
    executors = ability.get("executors")
    if isinstance(executors, list):
        for definition in executors:
            if isinstance(definition, dict):
                yield str(definition.get("platform") or ""), str(definition.get("name") or ""), definition
        return

    platforms = ability.get("platforms")
    if not isinstance(platforms, dict):
        return
    emitted: set[tuple[str, str]] = set()
    for raw_platforms, executor_blocks in sorted(platforms.items()):
        if not isinstance(executor_blocks, dict):
            continue
        for raw_executors, definition in sorted(executor_blocks.items()):
            if not isinstance(definition, dict):
                continue
            for raw_platform in str(raw_platforms).split(","):
                for raw_executor in str(raw_executors).split(","):
                    identity = (raw_platform.strip().lower(), raw_executor.strip().lower())
                    if all(identity) and identity not in emitted:
                        emitted.add(identity)
                        yield identity[0], identity[1], definition


def technique_fields(ability: dict[str, Any]) -> tuple[str, str]:
    technique = ability.get("technique") if isinstance(ability.get("technique"), dict) else {}
    tcode = str(technique.get("attack_id") or ability.get("technique_id") or "").strip().upper()
    name = str(technique.get("name") or ability.get("technique_name") or "").strip()
    return tcode, name


def resolve_tactic(ability: dict[str, Any], path: Path) -> tuple[str, str, str] | None:
    raw = sanitize(str(ability.get("tactic") or "")).replace("_", "-")
    if raw not in TACTICS:
        parent = path.parent.name.lower()
        raw = parent if parent in TACTICS else raw
    tactic = TACTICS.get(raw)
    return (raw, *tactic) if tactic else None


def classify_risk(
    ability_id: str,
    ability_name: str,
    tactic_slug: str,
    tcode: str,
    command: str,
    overrides: dict[str, Any],
) -> tuple[str, str]:
    ability_override = overrides.get("abilities", {}).get(ability_id)
    if ability_override:
        return ability_override, "ability_override"
    normalized_name = ability_name.lower()
    for rule in overrides.get("rules", []):
        if not isinstance(rule, dict):
            continue
        if rule.get("tcode") and str(rule["tcode"]).upper() != tcode:
            continue
        contains = str(rule.get("name_contains") or "").lower()
        if contains and contains not in normalized_name:
            continue
        risk = rule.get("risk")
        if risk in RISK_LEVELS:
            return risk, "rule_override"

    text = f"{ability_name}\n{command}".lower()
    words = set(re.findall(r"[a-z]+", text))
    if words & DISRUPT_TERMS:
        return "disrupt", "operation"
    if words & MODIFY_TERMS:
        return "modify", "operation"
    if words & OBSERVE_TERMS:
        return "observe", "operation"
    tactic_defaults = {
        "collection": "observe",
        "discovery": "observe",
        "command-and-control": "interact",
        "lateral-movement": "interact",
        "impair-process-control": "modify",
        "inhibit-response-function": "disrupt",
        "impact": "disrupt",
    }
    return tactic_defaults[tactic_slug], "tactic"


def parameter_class(fact: str, risk: str) -> str:
    words = set(sanitize(fact).split("_"))
    if words & CONNECTION_TERMS:
        return "connection"
    if risk in {"modify", "disrupt"} and words & WRITE_TERMS:
        return "process_write"
    if risk in {"modify", "disrupt"} and words & CONTROL_TERMS:
        return "control"
    if words & READ_TERMS or risk == "observe":
        return "read"
    return "control" if risk in {"modify", "disrupt"} else "read"


def tag_key(protocol: str, tactic: str, tcode: str, fact: str) -> str:
    fact_part = sanitize(fact)
    for prefix in (f"{protocol}_", "dcp_"):
        if fact_part.startswith(prefix):
            fact_part = fact_part[len(prefix):]
            break
    base = f"ot_{protocol}_{sanitize(tactic)}_{sanitize(tcode.removeprefix('T'))}_{fact_part or 'value'}"
    if len(base) <= 96:
        return base
    digest = hashlib.sha256(fact.encode("utf-8")).hexdigest()[:8]
    return f"{base[:87]}_{digest}"


def rewrite_facts(
    text: str,
    protocol: str,
    tactic: str,
    tcode: str,
    risk: str,
    additional_info: Any,
) -> tuple[str, list[dict[str, Any]]]:
    facts = sorted(set(FACT_PLACEHOLDER.findall(text)))
    info_facts = {}
    if isinstance(additional_info, dict) and isinstance(additional_info.get("facts"), dict):
        info_facts = additional_info["facts"]
    rename = {fact: tag_key(protocol, tactic, tcode, fact) for fact in facts}
    tags = []
    for fact in facts:
        metadata = info_facts.get(fact) if isinstance(info_facts.get(fact), dict) else {}
        words = re.sub(r"[._-]+", " ", fact).strip()
        tags.append(
            {
                "key": rename[fact],
                "label": words.title(),
                "description": str(metadata.get("description") or f"Upstream CALDERA OT fact: {fact}"),
                "default": "",
                "example": "",
                "sensitive": any(term in sanitize(fact) for term in SENSITIVE_TERMS),
                "required": True,
                "parameter_class": parameter_class(fact, risk),
                "source_fact": fact,
            }
        )
    return FACT_PLACEHOLDER.sub(lambda match: f"#{{{rename[match.group(1)]}}}", text), tags


def payload_names(definition: dict[str, Any]) -> list[str]:
    payloads = definition.get("payloads") or definition.get("payload") or []
    if isinstance(payloads, str):
        return [payloads]
    if isinstance(payloads, list):
        return [str(value) for value in payloads if value]
    if isinstance(payloads, dict):
        return [str(value) for value in payloads.values() if value]
    return []


def asset_architecture(filename: str) -> str:
    lower = filename.lower()
    if "arm64" in lower or "aarch64" in lower:
        return "arm64"
    if "arm" in lower:
        return "arm"
    if "386" in lower or "x86" in lower:
        return "x86"
    return "amd64"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def safe_asset_name(payload: str) -> str | None:
    if Path(payload).name != payload or not SAFE_FILENAME.fullmatch(payload):
        return None
    return payload


def asset_id(protocol: str, filename: str, platform: str, architecture: str) -> str:
    return sanitize(f"{protocol}_{filename}_{platform}_{architecture}")


def resolve_asset(
    root: Path,
    protocol: str,
    payload: str,
    platform: str,
    source_commit: str,
) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    safe_name = safe_asset_name(payload)
    base = {
        "payload": payload,
        "platform": platform,
        "source_repository": PLUGINS[protocol]["repository"],
        "source_commit": source_commit,
    }
    if not safe_name:
        return None, {**base, "status": "unsupported", "reason": "unsafe payload filename"}
    source = root / protocol / "payloads" / safe_name
    if not source.is_file():
        status = "external_release" if protocol == "iec61850" else "missing"
        reason = (
            "IEC61850 payload is supplied by the separate mitre/iec61850-payloads release repository"
            if protocol == "iec61850"
            else "referenced payload is absent from the pinned plugin checkout"
        )
        return None, {**base, "status": status, "reason": reason}
    size = source.stat().st_size
    if size <= 0 or size > MAX_ASSET_SIZE:
        return None, {**base, "status": "unsupported", "reason": f"invalid asset size: {size}"}
    architecture = asset_architecture(safe_name)
    identifier = asset_id(protocol, safe_name, platform, architecture)
    relative = f"{protocol}/assets/{quote(safe_name)}"
    metadata = {
        "id": identifier,
        "name": safe_name,
        "filename": safe_name,
        "platform": platform,
        "architecture": architecture,
        "url": f"{CATALOG_BASE_URL}/{relative}",
        "sha256": sha256_file(source),
        "size": size,
        "source": f"mitre/{protocol}",
        "source_repository": PLUGINS[protocol]["repository"],
        "source_commit": source_commit,
        "source_path": f"{protocol}/payloads/{safe_name}",
        "license": PLUGINS[protocol]["license"],
        "executable": True,
        "review_status": "reviewed-local-pinned",
        "_local_source": str(source),
    }
    return metadata, {**base, **{k: v for k, v in metadata.items() if not k.startswith("_")}, "status": "resolved"}


def rewrite_asset_path(command: str, payload: str, identifier: str) -> tuple[str, bool]:
    escaped = re.escape(payload)
    pattern = re.compile(rf"(?<![A-Za-z0-9_.-])(?:\.\\|\./)?{escaped}(?![A-Za-z0-9_.-])")
    rewritten, count = pattern.subn(f"{{{{asset:{identifier}}}}}", command)
    return rewritten, count > 0


def no_cleanup(executor: str, tcode: str) -> str:
    if executor == "powershell":
        return f"Write-Output '[INFO] {tcode} cleanup: upstream ability provides no cleanup command'"
    if executor == "cmd":
        return f"echo [INFO] {tcode} cleanup: upstream ability provides no cleanup command"
    return f"printf '%s\\n' '[INFO] {tcode} cleanup: upstream ability provides no cleanup command'"


def validate_asset(asset: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for field_name in (
        "id", "filename", "platform", "architecture", "url", "sha256", "size",
        "source_repository", "source_commit", "license", "executable",
    ):
        if asset.get(field_name) in (None, ""):
            errors.append(f"asset {asset.get('id')}: missing {field_name}")
    if not str(asset.get("url") or "").startswith("https://"):
        errors.append(f"asset {asset.get('id')}: URL is not HTTPS")
    if not re.fullmatch(r"[0-9a-f]{64}", str(asset.get("sha256") or "")):
        errors.append(f"asset {asset.get('id')}: invalid SHA256")
    if not SAFE_FILENAME.fullmatch(str(asset.get("filename") or "")):
        errors.append(f"asset {asset.get('id')}: unsafe filename")
    if asset.get("platform") not in set(PLATFORMS.values()):
        errors.append(f"asset {asset.get('id')}: invalid platform")
    if asset.get("executable") is not True:
        errors.append(f"asset {asset.get('id')}: executable must be true")
    if asset.get("review_status") != "reviewed-local-pinned":
        errors.append(f"asset {asset.get('id')}: invalid review status")
    return errors


def validate_pack(pack: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if pack.get("script_prefix") != SCRIPT_PREFIX:
        errors.append("package must declare script_prefix 'OT - '")
    if pack.get("mitre_domain") != "ics-attack":
        errors.append("package mitre_domain must be ics-attack")
    assets = {asset.get("id"): asset for asset in pack.get("assets", []) if isinstance(asset, dict)}
    for asset in assets.values():
        errors.extend(validate_asset(asset))
    tags = {
        tag.get("key"): tag
        for category in pack.get("tag_categories", [])
        if isinstance(category, dict)
        for tag in category.get("tags", [])
        if isinstance(tag, dict) and tag.get("key")
    }
    names: set[str] = set()
    for index, script in enumerate(pack.get("scripts", [])):
        name = str(script.get("name") or "")
        if not name.startswith(SCRIPT_PREFIX):
            errors.append(f"script {index}: invalid prefix")
        if name in names:
            errors.append(f"script {index}: duplicate name")
        names.add(name)
        if not VALID_TCODE.fullmatch(str(script.get("tcode") or "")):
            errors.append(f"script {index}: invalid TCode")
        if script.get("operational_risk") not in RISK_LEVELS:
            errors.append(f"script {index}: invalid operational_risk")
        if script.get("ot_protocol") != pack.get("ot_protocol"):
            errors.append(f"script {index}: protocol mismatch")
        if script.get("executor") not in set(EXECUTORS.values()):
            errors.append(f"script {index}: invalid executor")
        if script.get("platform") not in set(PLATFORMS.values()):
            errors.append(f"script {index}: invalid platform")
        required_tags = set(script.get("required_tags", []))
        placeholders = set(
            FACT_PLACEHOLDER.findall(
                f"{script.get('command') or ''}\n{script.get('cleanup_command') or ''}"
            )
        )
        if required_tags != placeholders:
            errors.append(f"script {index}: required_tags do not match placeholders")
        if required_tags - set(tags):
            errors.append(f"script {index}: undefined required tags")
        required_assets = set(script.get("required_assets", []))
        asset_placeholders = set(ASSET_PLACEHOLDER.findall(str(script.get("command") or "")))
        if required_assets != asset_placeholders:
            errors.append(f"script {index}: required_assets do not match asset placeholders")
        if required_assets - set(assets):
            errors.append(f"script {index}: undefined required assets")
        if not script.get("source_metadata"):
            errors.append(f"script {index}: missing source_metadata")
        for key in required_tags:
            if tags[key].get("default") or tags[key].get("example"):
                errors.append(f"script {index}: OT tag {key} has a default public value")
    for index, chain in enumerate(pack.get("chains", [])):
        refs = chain.get("script_refs", []) if isinstance(chain, dict) else []
        if len(refs) != 1:
            errors.append(f"chain {index}: OT chains must be one-step")
        if any(ref not in names for ref in refs):
            errors.append(f"chain {index}: unresolved script reference")
    return errors


def legal_files(plugin_root: Path) -> list[Path]:
    found = []
    for pattern in ("LICENSE", "LICENSE.*", "NOTICE", "NOTICE.*"):
        found.extend(path for path in plugin_root.glob(pattern) if path.is_file())
    return sorted(set(found), key=lambda path: path.name.lower())


def catalog_entry(pack: dict[str, Any]) -> dict[str, Any]:
    protocol = pack["ot_protocol"]
    risks = sorted(
        {script["operational_risk"] for script in pack["scripts"]},
        key=RISK_LEVELS.index,
    )
    return {
        "package_id": pack["package_id"],
        "package_name": pack["package_name"],
        "version": pack["version"],
        "description": pack["description"],
        "mitre_tactic": pack["mitre_tactic"],
        "mitre_tcodes": pack["mitre_tcodes"],
        "mitre_domain": "ics-attack",
        "script_count": len(pack["scripts"]),
        "chain_count": len(pack["chains"]),
        "asset_count": len(pack["assets"]),
        "platform": pack["platform"],
        "prerequisites": pack["prerequisites"],
        "sentinel_connectors": [],
        "status": "community",
        "provider": SOURCE_NAME,
        "source": SOURCE_NAME,
        "source_commit": pack["source_commit"],
        "protocol": protocol,
        "risk_badges": risks,
        "category": f"ot/{protocol}",
        "url": f"{CATALOG_BASE_URL}/{protocol}/{pack['package_id']}.json",
    }


def category_metadata() -> list[dict[str, Any]]:
    categories = [
        {"id": "enterprise/windows", "label": "Enterprise / Windows", "group": "Enterprise", "order": 10},
        {"id": "enterprise/linux", "label": "Enterprise / Linux", "group": "Enterprise", "order": 20},
        {"id": "general", "label": "General Utilities", "group": "Core", "order": 30},
        {"id": "technology", "label": "Technology", "group": "Core", "order": 40},
        {"id": "ics/windows", "label": "ICS / Windows", "group": "Legacy ICS", "order": 50},
        {"id": "ics/linux", "label": "ICS / Linux", "group": "Legacy ICS", "order": 60},
        {"id": "mobile/android", "label": "Mobile / Android", "group": "Mobile", "order": 70},
        {"id": "mobile/ios", "label": "Mobile / iOS", "group": "Mobile", "order": 80},
        {"id": "art", "label": "Atomic Red Team (Red Canary)", "group": "Community", "order": 90},
        {"id": "stockpile", "label": "MITRE CALDERA Stockpile", "group": "Community", "order": 100},
        {"id": "ot", "label": "OT / ICS", "group": "MITRE CALDERA for OT", "order": 110},
    ]
    for order, protocol in enumerate(PLUGINS, start=111):
        categories.append(
            {
                "id": f"ot/{protocol}",
                "label": PLUGINS[protocol]["label"],
                "group": "MITRE CALDERA for OT",
                "parent": "ot",
                "order": order,
                "provider": SOURCE_NAME,
            }
        )
    return categories


def provider_metadata() -> list[dict[str, Any]]:
    return [
        {"id": "x3m-ai", "name": "X3M.AI", "type": "first-party"},
        {"id": "atomic-red-team", "name": "Red Canary Atomic Red Team", "type": "upstream"},
        {"id": "mitre-stockpile", "name": "MITRE CALDERA Stockpile", "type": "upstream"},
        {
            "id": SOURCE_NAME,
            "name": "MITRE CALDERA for OT",
            "type": "upstream",
            "repository": SOURCE_REPOSITORY,
            "domain": "ics-attack",
        },
    ]


def updated_catalog(catalog: dict[str, Any], packs: list[dict[str, Any]], source_date: str) -> dict[str, Any]:
    entries = {pack["package_id"]: catalog_entry(pack) for pack in packs}
    existing = catalog.get("packs") if isinstance(catalog.get("packs"), list) else []
    non_ot_count = sum(1 for entry in existing if not str(entry.get("package_id") or "").startswith("ot-"))
    if non_ot_count < 26:
        raise ValueError(f"catalog safety check failed: expected at least 26 existing non-OT entries, found {non_ot_count}")
    merged = [entries.get(entry.get("package_id"), entry) for entry in existing]
    represented = {entry.get("package_id") for entry in merged}
    merged.extend(entries[key] for key in sorted(entries) if key not in represented)
    result = dict(catalog)
    result["catalog_version"] = "1.4.0"
    result["updated"] = max(str(catalog.get("updated") or ""), source_date)
    result["providers"] = provider_metadata()
    result["categories"] = category_metadata()
    result["packs"] = merged
    return result


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def swap_output(staging: Path, output: Path) -> None:
    backup = output.with_name(f".{output.name}.previous")
    if backup.exists():
        shutil.rmtree(backup)
    try:
        if output.exists():
            os.replace(output, backup)
        os.replace(staging, output)
    except OSError:
        if not output.exists() and backup.exists():
            os.replace(backup, output)
        raise
    if backup.exists():
        shutil.rmtree(backup)


def readme_text(commits: dict[str, str], packs: list[dict[str, Any]], report: dict[str, Any]) -> str:
    rows = "\n".join(
        f"| {PLUGINS[protocol]['label']} | {sum(1 for pack in packs if pack['ot_protocol'] == protocol)} | "
        f"{report['statistics']['by_protocol'].get(protocol, 0)} |"
        for protocol in PLUGINS
    )
    external_release_count = report["statistics"]["asset_references_by_status"].get("external_release", 0)
    return f"""# MITRE CALDERA for OT Packs

Morgana-native content converted from the six official MITRE CALDERA for OT plugins. Morgana consumes the content without requiring a CALDERA server at runtime. The packs use ATT&CK for ICS (`ics-attack`), preserve source technique and tactic metadata, and declare the `OT - ` script prefix.

> Some CALDERA for OT abilities can change device or process state. Use them only in an explicitly authorized lab, simulation, or approved production exercise.

Tag values are intentionally empty. No public or default OT target is supplied, and installing a pack never downloads an asset to an Agent or executes a command.

## Supported Protocols

| Protocol | Packs | Scripts |
|---|---:|---:|
{rows}

Packs are split by protocol and ATT&CK for ICS tactic, for example `ot-modbus-discovery-v1`. One upstream platform/executor variant becomes one deterministic Morgana Script.

## Risk Model

Every Script has an operational risk level:

| Risk | Meaning |
|---|---|
| `observe` | Read-only discovery, metadata, or value queries |
| `interact` | Protocol requests not intended to alter process state |
| `modify` | May change configuration, parameters, coils, registers, or control values |
| `disrupt` | May stop, disable, inhibit, delete, or significantly affect operation |

Morgana displays risk badges in the Excalibur catalog and Scripts view. Direct Script, Chain, and Campaign execution containing `modify` or `disrupt` content requires explicit operator acknowledgement. Imported high-risk content is never executed automatically.

## Parameters And Assets

CALDERA facts are converted to scoped Morgana tags. Connection, read, process-write, and control parameters remain empty until an operator assigns values.

Protocol utilities are distributed as package assets rather than embedded in the database. Each asset records its controlled HTTPS URL, safe filename, platform, architecture, source repository and commit, license, size, and SHA256. On execution the Agent:

1. Downloads required assets into its per-Test work directory.
2. Enforces platform, architecture, filename, and size policy.
3. Verifies SHA256 before resolving `{{{{asset:<id>}}}}` placeholders.
4. Applies executable permission only when declared.
5. Removes the work directory after execution.

The legacy `download_url` and `{{{{payload}}}}` path remains supported for older content.

## Install In Morgana

1. Open **Scripts > Excalibur Packs**.
2. Select **Refresh catalog**.
3. Expand **MITRE CALDERA for OT** and review protocol and risk badges.
4. Import only the required packs.
5. Open an imported Script and assign all required tags for the authorized target.

Import stores Scripts, one-step Chains, tags, and asset metadata. Assets are delivered only after explicit execution.

## Safe Lab Validation

Use an isolated, authorized simulator or cyber range. The recommended first validation is the Modbus Discovery pack and an `observe` Script such as Read Device Information. Verify the simulator address and port, select a matching Agent platform, and confirm expected telemetry before considering higher-risk content.

Do not begin with write-coil, restart, shutdown, disable, denial-of-service, or network-configuration abilities. No test in this repository should be pointed at a live industrial device without written approval and an agreed rollback plan.

## Update Process

From `morgana/excalibur/tools`, run `update-caldera-ot-packs.ps1`. The updater recursively refreshes the umbrella repository and its six official submodules under `C:\\ProgramData\\Morgana\\temp\\caldera-ot`, records every source SHA, regenerates packs and inventories, and runs deterministic/static validation. Publication requires the explicit `-Publish` switch.

The converter reads and packages upstream content; it never runs source commands or assets. Review `conversion-report.json`, `source-inventory.json`, and `asset-inventory.json` before publication.

## Provenance And Licensing

Umbrella source commit: `{commits['caldera-ot']}`.

Each protocol directory contains the LICENSE and NOTICE files found in its pinned plugin checkout. Asset entries preserve source repository, source commit, license, and SHA256. Licensing must be reviewed independently for every plugin and external payload source before redistribution.

## Known Limitations

IEC 61850 abilities require separately published binaries from `mitre/iec61850-payloads`. Those {external_release_count} variants are classified as `external_release` in the inventories and are intentionally not published until a release/version, repository, license, and SHA256 are pinned. Source-build-required or unresolved variants are likewise excluded rather than emitted as executable Scripts.

Only the six official MITRE plugins are included in this phase. Community plugins and simulator deployment are outside scope.
"""


def build_pack(
    protocol: str,
    tactic_slug: str,
    tactic_id: str,
    tactic_name: str,
    scripts: list[dict[str, Any]],
    tags: dict[str, dict[str, Any]],
    assets: dict[str, dict[str, Any]],
    commits: dict[str, str],
    dates: dict[str, str],
) -> dict[str, Any]:
    package_id = f"ot-{protocol}-{tactic_slug}-v1"
    for script in scripts:
        script["package"] = package_id
    used_asset_ids = {asset_id for script in scripts for asset_id in script["required_assets"]}
    clean_assets = [
        {key: value for key, value in assets[key].items() if not key.startswith("_")}
        for key in sorted(used_asset_ids)
    ]
    used_tags = {tag for script in scripts for tag in script["required_tags"]}
    clean_tags = [tags[key] for key in sorted(used_tags)]
    chains = [
        {
            "name": script["name"],
            "description": f"Single-step authorized OT test for {script['tcode']} - {script['technique_name']}.",
            "package": package_id,
            "tcode": script["tcode"],
            "tactic": tactic_name,
            "operational_risk": script["operational_risk"],
            "script_refs": [script["name"]],
        }
        for script in scripts
    ]
    return {
        "package_id": package_id,
        "package_name": f"OT - {PLUGINS[protocol]['label']} - {tactic_name} Pack (MITRE)",
        "version": "1.0.0",
        "description": (
            f"Official MITRE CALDERA for OT {PLUGINS[protocol]['label']} abilities converted "
            f"for ATT&CK for ICS {tactic_name}. CALDERA is not required at runtime."
        ),
        "author": "MITRE (converted by X3M.AI for Morgana)",
        "created": dates[protocol],
        "script_prefix": SCRIPT_PREFIX,
        "source": SOURCE_NAME,
        "source_repository": SOURCE_REPOSITORY,
        "source_plugin_repository": PLUGINS[protocol]["repository"],
        "source_commit": commits[protocol],
        "source_commits": commits,
        "mitre_domain": "ics-attack",
        "mitre_tactic": f"{tactic_name} ({tactic_id})",
        "mitre_tactic_name": tactic_name,
        "mitre_tactic_source": tactic_slug,
        "mitre_tcodes": sorted({script["tcode"] for script in scripts}),
        "ot_protocol": protocol,
        "platform": sorted({script["platform"] for script in scripts}),
        "execution_environment": ["lab", "simulation", "approved-production-test"],
        "ot_live_system_warning": True,
        "prerequisites": [
            "Morgana agent installed on an explicitly authorized execution host",
            "Required OT facts supplied as Morgana tag values; no target defaults are provided",
            "Required assets downloaded from Camelot and verified by SHA256",
        ],
        "license": PLUGINS[protocol]["license"],
        "assets": clean_assets,
        "tag_categories": [
            {
                "category_id": f"ot_{protocol}_{tactic_slug}_parameters",
                "label": f"{PLUGINS[protocol]['label']} {tactic_name} Parameters",
                "description": "Operator-supplied OT connection, read, process-write, and control values.",
                "scope": "local",
                "used_by_tcodes": sorted({script["tcode"] for script in scripts}),
                "tags": clean_tags,
            }
        ] if clean_tags else [],
        "scripts": scripts,
        "chains": chains,
    }


def convert(arguments: argparse.Namespace) -> tuple[list[dict[str, Any]], dict[str, Any], dict[str, Any], dict[str, Any], dict[str, dict[str, Any]]]:
    root = Path(arguments.caldera_ot_dir).resolve()
    for protocol in PLUGINS:
        if not (root / protocol / "data" / "abilities").is_dir():
            raise ValueError(f"missing official plugin abilities directory: {protocol}")
    overrides = load_overrides(Path(arguments.risk_overrides).resolve())
    commits, dates = source_identity(root)
    if any(value == "unknown" for value in commits.values()):
        raise ValueError(f"could not determine all pinned source commits: {commits}")

    state = ConversionState()
    grouped_scripts: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    grouped_tags: dict[tuple[str, str], dict[str, dict[str, Any]]] = defaultdict(dict)
    grouped_assets: dict[tuple[str, str], dict[str, dict[str, Any]]] = defaultdict(dict)
    tactic_meta: dict[tuple[str, str], tuple[str, str]] = {}
    all_assets: dict[str, dict[str, Any]] = {}

    for protocol in PLUGINS:
        plugin_root = root / protocol
        ability_root = plugin_root / "data" / "abilities"
        yaml_files = sorted([*ability_root.rglob("*.yml"), *ability_root.rglob("*.yaml")])
        state.yaml_files_scanned += len(yaml_files)
        protocol_inventory = {
            "repository": PLUGINS[protocol]["repository"],
            "commit": commits[protocol],
            "commit_date": dates[protocol],
            "yaml_files": len(yaml_files),
            "abilities": 0,
            "variants": 0,
            "generated_scripts": 0,
            "skipped_variants": 0,
            "ability_inventory": [],
        }
        state.source_inventory[protocol] = protocol_inventory
        state.asset_inventory[protocol] = {"references": []}

        for source_file in yaml_files:
            source_path = source_file.relative_to(root).as_posix()
            for ability in iter_abilities(source_file, state, source_path):
                ability_id = str(ability.get("id") or "").strip()
                ability_name = str(ability.get("name") or "").strip()
                tcode, technique_name = technique_fields(ability)
                tactic = resolve_tactic(ability, source_file)
                variants = list(iter_variants(ability))
                missing = [
                    name for name, value in (
                        ("id", ability_id), ("name", ability_name), ("tcode", tcode),
                        ("tactic", tactic), ("variants", variants),
                    ) if not value
                ]
                if missing or not VALID_TCODE.fullmatch(tcode):
                    state.hard_errors.append(
                        {"source_path": source_path, "ability_id": ability_id, "error": f"invalid ability: {missing or ['tcode']}"}
                    )
                    continue
                tactic_slug, tactic_id, tactic_name = tactic
                if arguments.protocol and protocol != arguments.protocol:
                    continue
                if arguments.tactic and sanitize(arguments.tactic).replace("_", "-") not in {
                    tactic_slug, tactic_id.lower(), sanitize(tactic_name).replace("_", "-"),
                }:
                    continue

                state.abilities_parsed += 1
                protocol_inventory["abilities"] += 1
                group = (protocol, tactic_slug)
                tactic_meta[group] = (tactic_id, tactic_name)
                protocol_inventory["ability_inventory"].append(
                    {
                        "ability_uuid": ability_id,
                        "source_path": source_path,
                        "tactic": tactic_slug,
                        "technique_id": tcode,
                        "technique_name": technique_name,
                        "variant_count": len(variants),
                    }
                )

                for raw_platform, raw_executor, definition in variants:
                    state.variants_discovered += 1
                    protocol_inventory["variants"] += 1
                    platform = PLATFORMS.get(raw_platform.lower())
                    executor = EXECUTORS.get(raw_executor.lower())
                    detail = {
                        "protocol": protocol,
                        "ability_id": ability_id,
                        "source_path": source_path,
                        "source_platform": raw_platform,
                        "source_executor": raw_executor,
                    }
                    if not platform or not executor:
                        state.skip({**detail, "status": "unsupported", "reason": "unsupported platform or executor"})
                        protocol_inventory["skipped_variants"] += 1
                        continue
                    if arguments.platform and platform != arguments.platform:
                        continue
                    raw_command = command_text(definition.get("command"))
                    if not raw_command:
                        state.skip({**detail, "status": "unsupported", "reason": "empty command"})
                        protocol_inventory["skipped_variants"] += 1
                        continue

                    raw_cleanup = command_text(definition.get("cleanup") or definition.get("cleanup_command"))
                    payloads = payload_names(definition)
                    state.payload_references += len(payloads)
                    command = raw_command
                    cleanup = raw_cleanup
                    required_assets: list[str] = []
                    variant_assets: list[dict[str, Any]] = []
                    unresolved = False
                    for payload in sorted(set(payloads)):
                        resolved, inventory = resolve_asset(root, protocol, payload, platform, commits[protocol])
                        state.asset_inventory[protocol]["references"].append({**detail, **inventory})
                        state.asset_status_counts[inventory["status"]] += 1
                        if not resolved:
                            unresolved = True
                            continue
                        command, command_replaced = rewrite_asset_path(command, payload, resolved["id"])
                        cleanup, cleanup_replaced = rewrite_asset_path(cleanup, payload, resolved["id"])
                        if not command_replaced and not cleanup_replaced:
                            state.hard_errors.append(
                                {**detail, "error": f"payload {payload} is listed but its executable path was not found in command"}
                            )
                            unresolved = True
                            continue
                        required_assets.append(resolved["id"])
                        variant_assets.append(resolved)
                        all_assets[resolved["id"]] = resolved
                    if unresolved:
                        status = "external_release" if protocol == "iec61850" else "missing_asset"
                        state.skip({**detail, "status": status, "reason": "one or more required payloads were not safely resolved"})
                        protocol_inventory["skipped_variants"] += 1
                        continue

                    risk, risk_source = classify_risk(
                        ability_id, ability_name, tactic_slug, tcode, command, overrides
                    )
                    boundary = "\n__MORGANA_OT_CLEANUP_BOUNDARY__\n"
                    combined = f"{command}{boundary}{cleanup}" if cleanup else command
                    rewritten, tags = rewrite_facts(
                        combined, protocol, tactic_slug, tcode, risk, ability.get("additional_info")
                    )
                    state.facts_converted += len(tags)
                    if cleanup:
                        command, cleanup = (part.strip() for part in rewritten.split(boundary, 1))
                    else:
                        command, cleanup = rewritten.strip(), no_cleanup(executor, tcode)

                    variant_label = f"{PLATFORM_LABELS[platform]}/{EXECUTOR_LABELS[executor]}"
                    name = f"{SCRIPT_PREFIX}{PLUGINS[protocol]['label'].upper()} - {tcode} - {trim(ability_name, 90)} [{variant_label}]"
                    script = {
                        "id": name,
                        "name": name,
                        "description": trim(ability.get("description") or f"Official MITRE {protocol} OT ability.", 1000),
                        "tactic": tactic_name,
                        "tcode": tcode,
                        "technique_name": trim(technique_name or ability_name, 160),
                        "mitre_domain": "ics-attack",
                        "executor": executor,
                        "platform": platform,
                        "required_tags": [tag["key"] for tag in tags],
                        "tag_params": {
                            tag["key"]: {
                                key: tag[key]
                                for key in ("label", "description", "default", "sensitive", "parameter_class")
                            }
                            for tag in tags
                        },
                        "required_assets": sorted(required_assets),
                        "command": command,
                        "cleanup_command": cleanup,
                        "operational_risk": risk,
                        "operational_risk_source": risk_source,
                        "ot_protocol": protocol,
                        "execution_environment": ["lab", "simulation", "approved-production-test"],
                        "ot_live_system_warning": True,
                        "source": SOURCE_NAME,
                        "source_metadata": {
                            "ability_uuid": ability_id,
                            "source_path": source_path,
                            "source_repository": PLUGINS[protocol]["repository"],
                            "source_commit": commits[protocol],
                            "umbrella_repository": SOURCE_REPOSITORY,
                            "umbrella_commit": commits["caldera-ot"],
                            "source_platform": raw_platform,
                            "source_executor": raw_executor,
                            "protocol": protocol,
                            "technique_id": tcode,
                            "technique_name": technique_name,
                            "tactic": tactic_slug,
                            "mitre_domain": "ics-attack",
                        },
                    }
                    grouped_scripts[group].append(script)
                    for tag in tags:
                        existing = grouped_tags[group].get(tag["key"])
                        if existing and existing["source_fact"] != tag["source_fact"]:
                            state.hard_errors.append(
                                {**detail, "error": f"tag collision: {tag['key']}"}
                            )
                        grouped_tags[group][tag["key"]] = tag
                    for asset in variant_assets:
                        grouped_assets[group][asset["id"]] = asset
                    state.generated_scripts += 1
                    state.protocol_counts[protocol] += 1
                    state.tactic_counts[tactic_slug] += 1
                    state.risk_counts[risk] += 1
                    state.platform_counts[platform] += 1
                    state.executor_counts[executor] += 1
                    protocol_inventory["generated_scripts"] += 1

    packs = []
    for group in sorted(grouped_scripts):
        protocol, tactic_slug = group
        scripts = sorted(
            grouped_scripts[group],
            key=lambda item: (item["tcode"], item["name"], item["source_metadata"]["ability_uuid"]),
        )
        tactic_id, tactic_name = tactic_meta[group]
        pack = build_pack(
            protocol, tactic_slug, tactic_id, tactic_name, scripts,
            grouped_tags[group], grouped_assets[group], commits, dates,
        )
        errors = validate_pack(pack)
        if errors:
            state.hard_errors.extend({"package_id": pack["package_id"], "error": error} for error in errors)
        packs.append(pack)

    for protocol in PLUGINS:
        references = state.asset_inventory[protocol]["references"]
        references.sort(
            key=lambda item: (
                item.get("payload", ""), item.get("ability_id", ""),
                item.get("source_platform", ""), item.get("source_executor", ""),
            )
        )
        counts = Counter(reference["status"] for reference in references)
        state.asset_inventory[protocol]["status_counts"] = dict(sorted(counts.items()))

    generated_at = f"{dates['caldera-ot']}T00:00:00+00:00"
    provenance = {
        "source": SOURCE_NAME,
        "source_repository": SOURCE_REPOSITORY,
        "source_commits": commits,
        "source_commit_dates": dates,
        "generated_at": generated_at,
    }
    source_inventory = {
        **provenance,
        "protocols": state.source_inventory,
    }
    asset_inventory = {
        **provenance,
        "maximum_asset_size_bytes": MAX_ASSET_SIZE,
        "protocols": state.asset_inventory,
    }
    report = {
        **provenance,
        "summary": {
            "yaml_files_scanned": state.yaml_files_scanned,
            "abilities_parsed": state.abilities_parsed,
            "variants_discovered": state.variants_discovered,
            "generated_scripts": state.generated_scripts,
            "skipped_variants": state.skipped_variants,
            "packs_generated": len(packs),
            "facts_converted": state.facts_converted,
            "payload_references": state.payload_references,
            "unique_assets": len(all_assets),
            "hard_errors": len(state.hard_errors),
        },
        "statistics": {
            "by_protocol": dict(sorted(state.protocol_counts.items())),
            "by_tactic": dict(sorted(state.tactic_counts.items())),
            "by_risk": dict(sorted(state.risk_counts.items())),
            "by_platform": dict(sorted(state.platform_counts.items())),
            "by_executor": dict(sorted(state.executor_counts.items())),
            "asset_references_by_status": dict(sorted(state.asset_status_counts.items())),
        },
        "packs": [
            {
                "package_id": pack["package_id"],
                "protocol": pack["ot_protocol"],
                "tactic": pack["mitre_tactic_source"],
                "scripts": len(pack["scripts"]),
                "chains": len(pack["chains"]),
                "assets": len(pack["assets"]),
                "platforms": pack["platform"],
                "risks": dict(sorted(Counter(script["operational_risk"] for script in pack["scripts"]).items())),
            }
            for pack in packs
        ],
        "skips": sorted(
            state.skips,
            key=lambda item: (
                item.get("protocol", ""), item.get("source_path", ""),
                item.get("ability_id", ""), item.get("source_platform", ""),
                item.get("source_executor", ""),
            ),
        ),
        "errors": state.hard_errors,
    }
    return packs, report, source_inventory, asset_inventory, all_assets


def main() -> int:
    parser = argparse.ArgumentParser(description="Convert MITRE CALDERA for OT plugins to Morgana packs")
    parser.add_argument(
        "--caldera-ot-dir", default=r"C:\ProgramData\Morgana\temp\caldera-ot",
        help="Pinned recursive checkout of mitre/caldera-ot",
    )
    parser.add_argument("--out-dir", default=str(DEFAULT_OUTPUT_DIR), help="Output hierarchy")
    parser.add_argument("--risk-overrides", default=str(OVERRIDES_FILE), help="Explicit risk override JSON")
    parser.add_argument("--protocol", choices=sorted(PLUGINS), help="Convert one protocol")
    parser.add_argument("--tactic", help="Convert one ICS tactic")
    parser.add_argument("--platform", choices=sorted(set(PLATFORMS.values())), help="Convert one platform")
    parser.add_argument("--dry-run", action="store_true", help="Parse and validate without replacing files")
    parser.add_argument("--no-update-catalog", action="store_true", help="Do not update catalog.json")
    arguments = parser.parse_args()

    try:
        packs, report, source_inventory, asset_inventory, all_assets = convert(arguments)
        if report["errors"]:
            raise ValueError(f"conversion produced {len(report['errors'])} hard validation errors")
        if not packs:
            raise ValueError("conversion produced no executable packs")
        if not arguments.protocol and not arguments.tactic and not arguments.platform:
            represented = {pack["ot_protocol"] for pack in packs}
            expected = set(PLUGINS) - {"iec61850"}
            if not expected.issubset(represented):
                raise ValueError(f"incomplete full conversion; missing executable protocols: {sorted(expected - represented)}")

        output = Path(arguments.out_dir).resolve()
        catalog = None
        if not arguments.no_update_catalog:
            catalog = json.loads(CATALOG_FILE.read_text(encoding="utf-8"))
            catalog = updated_catalog(catalog, packs, source_inventory["source_commit_dates"]["caldera-ot"])
            json.dumps(catalog, ensure_ascii=False)

        if arguments.dry_run:
            log(f"Dry run validated {len(packs)} packs and {report['summary']['generated_scripts']} scripts")
            return 0

        output.parent.mkdir(parents=True, exist_ok=True)
        staging = Path(tempfile.mkdtemp(prefix=".ot-staging-", dir=output.parent))
        try:
            for pack in packs:
                protocol_dir = staging / pack["ot_protocol"]
                write_json(protocol_dir / f"{pack['package_id']}.json", pack)
            for asset in all_assets.values():
                destination = staging / asset["source"].split("/", 1)[1] / "assets" / asset["filename"]
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(asset["_local_source"], destination)
            for protocol in PLUGINS:
                if any(pack["ot_protocol"] == protocol and pack["assets"] for pack in packs):
                    destination = staging / protocol / "assets"
                    destination.mkdir(parents=True, exist_ok=True)
                    for legal in legal_files(Path(arguments.caldera_ot_dir).resolve() / protocol):
                        shutil.copy2(legal, destination / legal.name)
            write_json(staging / "conversion-report.json", report)
            write_json(staging / "source-inventory.json", source_inventory)
            write_json(staging / "asset-inventory.json", asset_inventory)
            (staging / "README.md").write_text(
                readme_text(source_inventory["source_commits"], packs, report), encoding="utf-8"
            )
            swap_output(staging, output)
        finally:
            if staging.exists():
                shutil.rmtree(staging)
        if catalog is not None:
            write_json(CATALOG_FILE, catalog)
        log(
            f"Wrote {len(packs)} packs, {report['summary']['generated_scripts']} scripts, "
            f"and {report['summary']['unique_assets']} assets"
        )
        return 0
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"[ERROR] {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())