#!/usr/bin/env python3
"""Shared Living-Off-The-Land normalization, validation, and pack generation."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import tempfile
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, field
from datetime import date
from pathlib import Path
from typing import Any, Iterable

TOOLS_DIR = Path(__file__).resolve().parent
EXCALIBUR_DIR = TOOLS_DIR.parent
DEFAULT_OUTPUT_DIR = EXCALIBUR_DIR / "lotl"
CATALOG_FILE = EXCALIBUR_DIR / "catalog.json"
RISK_OVERRIDES_FILE = TOOLS_DIR / "lotl_risk_overrides.json"
CATALOG_BASE_URL = "https://raw.githubusercontent.com/x3m-ai/Camelot/main/morgana/excalibur/lotl"
VALID_TCODE = re.compile(r"^T\d{4}(?:\.\d{3})?$")
MORGANA_PLACEHOLDER = re.compile(r"#\{([^{}]+)\}")
SENSITIVE_TERMS = ("password", "passwd", "secret", "token", "credential", "private_key", "api_key")

TACTIC_BY_TCODE: dict[str, tuple[str, str]] = {
    "T1003": ("TA0006", "Credential Access"),
    "T1005": ("TA0009", "Collection"),
    "T1027": ("TA0005", "Defense Evasion"),
    "T1041": ("TA0010", "Exfiltration"),
    "T1059": ("TA0002", "Execution"),
    "T1071": ("TA0011", "Command and Control"),
    "T1105": ("TA0011", "Command and Control"),
    "T1140": ("TA0005", "Defense Evasion"),
    "T1218": ("TA0005", "Defense Evasion"),
    "T1548": ("TA0004", "Privilege Escalation"),
    "T1564": ("TA0005", "Defense Evasion"),
    "T1565": ("TA0040", "Impact"),
    "T1574": ("TA0005", "Defense Evasion"),
}


@dataclass
class TagDefinition:
    key: str
    label: str
    description: str
    sensitive: bool = False
    required: bool = True
    default: str = ""
    example: str = ""
    parameter_class: str = "value"


@dataclass
class NormalizedProcedure:
    provider: str
    source_id: str
    source_name: str
    name: str
    platform: str
    executor: str
    command: str
    primary_tcode: str
    source_tcodes: list[str]
    category: str
    context: str
    risk: str
    readiness: str
    description: str
    required_tags: list[str] = field(default_factory=list)
    tags: list[TagDefinition] = field(default_factory=list)
    prerequisites: list[str] = field(default_factory=list)
    source_metadata: dict[str, Any] = field(default_factory=dict)
    cleanup_command: str | None = None

    def identity(self) -> str:
        normalized_command = re.sub(r"\s+", " ", self.command).strip().lower()
        return "|".join((
            self.provider,
            self.source_name.lower(),
            self.category.lower(),
            self.context.lower(),
            normalized_command,
            self.platform,
            self.executor,
        ))


@dataclass
class ProviderStats:
    source_objects: int = 0
    source_entries: int = 0
    context_expansions: int = 0
    raw_variants: int = 0
    published: int = 0
    duplicates: int = 0
    skipped: int = 0
    unsupported: int = 0
    errors: int = 0
    counts_by_category: Counter[str] = field(default_factory=Counter)
    counts_by_context: Counter[str] = field(default_factory=Counter)
    counts_by_tcode: Counter[str] = field(default_factory=Counter)
    counts_by_readiness: Counter[str] = field(default_factory=Counter)
    counts_by_source_directory: Counter[str] = field(default_factory=Counter)
    counts_by_privilege: Counter[str] = field(default_factory=Counter)
    issues: list[dict[str, Any]] = field(default_factory=list)
    metrics: dict[str, Any] = field(default_factory=dict)

    def reconciles(self) -> bool:
        return self.raw_variants == self.published + self.duplicates + self.skipped + self.unsupported

    def report(self) -> dict[str, Any]:
        return {
            "source_objects": self.source_objects,
            "source_entries": self.source_entries,
            "context_expansions": self.context_expansions,
            "raw_variants": self.raw_variants,
            "published": self.published,
            "duplicates": self.duplicates,
            "skipped": self.skipped,
            "unsupported": self.unsupported,
            "errors": self.errors,
            "counts_by_category": dict(sorted(self.counts_by_category.items())),
            "counts_by_context": dict(sorted(self.counts_by_context.items())),
            "counts_by_tcode": dict(sorted(self.counts_by_tcode.items())),
            "counts_by_readiness": dict(sorted(self.counts_by_readiness.items())),
            "counts_by_source_directory": dict(sorted(self.counts_by_source_directory.items())),
            "counts_by_privilege": dict(sorted(self.counts_by_privilege.items())),
            "issues": self.issues,
            "metrics": self.metrics,
            "reconciled": self.reconciles(),
        }


def slug(value: str) -> str:
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", value.lower())).strip("-") or "other"


def compact(value: Any, maximum: int = 600) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    return text if len(text) <= maximum else f"{text[:maximum - 3].rstrip()}..."


def git_identity(directory: Path) -> tuple[str, str]:
    def run(*arguments: str) -> str:
        try:
            result = subprocess.run(
                ["git", "-C", str(directory), *arguments], check=True,
                capture_output=True, text=True, timeout=20,
            )
            return result.stdout.strip()
        except (OSError, subprocess.SubprocessError):
            return "unknown"
    return run("rev-parse", "HEAD"), run("show", "-s", "--format=%cs", "HEAD")


def tag_key(provider: str, parameter_class: str, qualifier: str = "") -> str:
    base = f"lotl_{slug(provider).replace('-', '_')}_{slug(parameter_class).replace('-', '_')}"
    if qualifier:
        digest = hashlib.sha1(qualifier.encode("utf-8")).hexdigest()[:7]
        base = f"{base}_{digest}"
    return base[:64]


def make_tag(provider: str, parameter_class: str, source_token: str = "") -> TagDefinition:
    sensitive = any(term in parameter_class.lower() for term in SENSITIVE_TERMS)
    labels = {
        "input_file": "Input File", "output_file": "Output File", "remote_url": "Remote URL",
        "remote_host": "Remote Host", "remote_port": "Remote Port", "local_path": "Local Path",
        "payload_path": "Payload Path", "command": "Command", "argument": "Argument",
        "username": "Username", "domain": "Domain", "service": "Service",
        "registry_path": "Registry Path", "data": "Data",
    }
    return TagDefinition(
        key=tag_key(provider, parameter_class),
        label=labels.get(parameter_class, parameter_class.replace("_", " ").title()),
        description=f"Operator-supplied {parameter_class.replace('_', ' ')} for this authorized LOTL procedure. Source token: {source_token or parameter_class}.",
        sensitive=sensitive,
        parameter_class="credential" if sensitive else ("connection" if parameter_class in {"remote_url", "remote_host", "remote_port"} else parameter_class),
    )


def classify_risk(provider: str, category: str, command: str, context: str, overrides: dict[str, str]) -> str:
    override_key = f"{provider}:{category}:{context}".lower()
    if override_key in overrides:
        return overrides[override_key]
    value = f"{category} {command} {context}".lower()
    if re.search(r"delete|erase|wipe|ransom|encrypt|shutdown|reboot|tamper|shadow", value):
        return "disrupt"
    if re.search(r"sudo|suid|capabilit|privilege|uac|persistence|credential|dump|file-write|upload", value):
        return "modify"
    if re.search(r"download|network|reverse-shell|bind-shell|execute|command|shell|compile|library-load", value):
        return "interact"
    return "observe"


def tactic_for(tcode: str) -> tuple[str, str]:
    base = tcode.split(".")[0]
    return TACTIC_BY_TCODE.get(tcode) or TACTIC_BY_TCODE.get(base) or ("", "Multiple")


def deduplicate(procedures: Iterable[NormalizedProcedure], stats: ProviderStats) -> list[NormalizedProcedure]:
    unique: dict[str, NormalizedProcedure] = {}
    duplicate_source_ids: list[str] = []
    for procedure in procedures:
        identity = procedure.identity()
        if identity in unique:
            stats.duplicates += 1
            duplicate_source_ids.append(procedure.source_id)
            continue
        unique[identity] = procedure
    stats.metrics["duplicate_source_ids"] = duplicate_source_ids
    result = sorted(unique.values(), key=lambda item: (item.category.lower(), item.context.lower(), item.source_name.lower(), item.source_id))
    stats.published = len(result)
    return result


def validate_procedure(procedure: NormalizedProcedure) -> list[str]:
    errors: list[str] = []
    if procedure.provider not in {"lolbas", "gtfobins"}:
        errors.append("invalid provider")
    if procedure.platform not in {"windows", "linux"}:
        errors.append("invalid platform")
    if procedure.executor not in {"cmd", "powershell", "bash", "python"}:
        errors.append("invalid executor")
    if not procedure.name or not procedure.command.strip():
        errors.append("blank name or command")
    if procedure.primary_tcode != "T0000" and not VALID_TCODE.fullmatch(procedure.primary_tcode):
        errors.append("invalid primary TCode")
    if set(MORGANA_PLACEHOLDER.findall(procedure.command)) != set(procedure.required_tags):
        errors.append("required_tags do not match placeholders")
    if len({tag.key for tag in procedure.tags}) != len(procedure.tags):
        errors.append("duplicate tag keys")
    if not isinstance(procedure.source_metadata, dict) or not procedure.source_metadata:
        errors.append("missing source metadata")
    if procedure.risk not in {"observe", "interact", "modify", "disrupt"}:
        errors.append("invalid risk")
    return errors


def script_from(procedure: NormalizedProcedure) -> dict[str, Any]:
    return {
        "id": procedure.source_id,
        "name": procedure.name,
        "description": procedure.description,
        "tactic": tactic_for(procedure.primary_tcode)[1],
        "tcode": procedure.primary_tcode,
        "executor": procedure.executor,
        "platform": procedure.platform,
        "command": procedure.command,
        "cleanup_command": procedure.cleanup_command,
        "required_tags": procedure.required_tags,
        "required_assets": [],
        "operational_risk": procedure.risk,
        "source_metadata": {
            **procedure.source_metadata,
            "provider": procedure.provider,
            "source_id": procedure.source_id,
            "source_name": procedure.source_name,
            "source_tcodes": procedure.source_tcodes,
            "category": procedure.category,
            "context": procedure.context,
            "readiness": procedure.readiness,
            "prerequisites": procedure.prerequisites,
        },
    }


def build_packs(
    procedures: list[NormalizedProcedure], provider: str, source_commit: str,
    source_repository: str, source_license: str, max_per_pack: int,
) -> list[tuple[dict[str, Any], str]]:
    grouped: dict[tuple[str, str], list[NormalizedProcedure]] = defaultdict(list)
    for procedure in procedures:
        group_context = procedure.context if provider == "gtfobins" else "all"
        grouped[(procedure.category, group_context)].append(procedure)

    built: list[tuple[dict[str, Any], str]] = []
    for (category, context), items in sorted(grouped.items()):
        items.sort(key=lambda item: item.identity())
        for chunk_index, offset in enumerate(range(0, len(items), max_per_pack), start=1):
            chunk = items[offset:offset + max_per_pack]
            category_slug = slug(category)
            context_slug = slug(context)
            group_slug = category_slug if provider == "lolbas" else f"{category_slug}-{context_slug}"
            chunk_suffix = f"-{chunk_index:02d}" if len(items) > max_per_pack else ""
            package_id = f"{provider}-{group_slug}{chunk_suffix}-v1"
            provider_name = "LOLBAS Project" if provider == "lolbas" else "GTFOBins"
            platform = "windows" if provider == "lolbas" else "linux"
            scripts = [script_from(item) for item in chunk]
            tcodes = sorted({item.primary_tcode for item in chunk if item.primary_tcode != "T0000"})
            risks = sorted({item.risk for item in chunk}, key=("observe", "interact", "modify", "disrupt").index)
            readiness = Counter(item.readiness for item in chunk)
            tags = {tag.key: tag for item in chunk for tag in item.tags}
            title_context = "" if provider == "lolbas" else f" / {context.replace('-', ' ').title()}"
            package = {
                "package_id": package_id,
                "package_name": f"{'LOLBAS' if provider == 'lolbas' else 'GTFOBins'} - {category.replace('-', ' ').title()}{title_context}{chunk_suffix.replace('-', ' Part ')}",
                "version": "1.0.0",
                "summary": f"{len(chunk)} source-derived {provider_name} Living-Off-The-Land procedures for {category.replace('-', ' ')}{title_context}.",
                "description": f"Faithful, deterministic conversion of explicit {provider_name} procedures. Commands retain upstream behavior while environment values use Morgana Tags.",
                "purpose": "Run authorized Living-Off-The-Land detection validation using legitimate native or commonly available utilities in adversary-like ways.",
                "capabilities": [
                    f"Provides {len(chunk)} distinct source procedures grouped by {category}{title_context}.",
                    "Preserves source identity, ATT&CK mappings, execution context, prerequisites, and provider metadata.",
                    "Supports deterministic content-only updates from pinned upstream commits.",
                ],
                "use_cases": [
                    "Validate endpoint and network detections for authorized Living-Off-The-Land behavior.",
                    "Search and import only the utility, function, context, platform, or ATT&CK coverage needed for an exercise.",
                ],
                "safety_notes": [
                    "Review every command, Tag, privilege requirement, and readiness classification before execution.",
                    "Interactive, elevated, SUID, capability, and counterpart-dependent procedures require an explicitly prepared lab.",
                    "No upstream command is executed during conversion or import.",
                ],
                "prerequisites": [
                    f"The referenced {'Windows binary' if provider == 'lolbas' else 'Linux/Unix binary'} must exist on the target.",
                    "Operator-supplied Tags and any declared privilege or network counterpart must be configured.",
                    "Explicit authorization for the target and procedure behavior.",
                ],
                "author": f"{provider_name} / X3M.AI conversion",
                "created": str(date.today()),
                "script_prefix": "LOLBAS - " if provider == "lolbas" else "GTFOBINS - ",
                "provider": provider,
                "source": provider,
                "source_repository": source_repository,
                "source_commit": source_commit,
                "source_license": source_license,
                "documentation_url": source_repository,
                "mitre_domain": "enterprise-attack",
                "mitre_tactic": category.replace("-", " ").title(),
                "mitre_tcodes": tcodes,
                "platform": [platform],
                "risk_badges": risks,
                "readiness_counts": dict(sorted(readiness.items())),
                "category": f"lotl/{provider}",
                "tag_categories": [{
                    "category_id": f"lotl_{provider}_parameters",
                    "label": f"{provider_name} Runtime Parameters",
                    "description": "Operator-supplied values shared by Living-Off-The-Land procedures.",
                    "scope": "local",
                    "tags": [asdict(tag) for tag in sorted(tags.values(), key=lambda item: item.key)],
                }] if tags else [],
                "assets": [],
                "scripts": scripts,
                "chains": [],
            }
            relative = f"{provider}/{package_id}.json"
            built.append((package, relative))
    return built


def catalog_entry(package: dict[str, Any], relative: str) -> dict[str, Any]:
    return {
        key: package[key] for key in (
            "package_id", "package_name", "version", "summary", "description", "purpose",
            "capabilities", "use_cases", "prerequisites", "safety_notes", "provider", "category",
            "platform", "mitre_tactic", "mitre_tcodes", "source", "source_commit", "source_license",
            "documentation_url", "risk_badges", "readiness_counts",
        )
    } | {
        "script_count": len(package["scripts"]),
        "chain_count": 0,
        "asset_count": 0,
        "status": "community",
        "author": package["author"],
        "url": f"{CATALOG_BASE_URL}/{relative}",
    }


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def readme_text(report: dict[str, Any]) -> str:
    lolbas = report.get("lolbas", {})
    gtfobins = report.get("gtfobins", {})
    combined = report["combined"]
    return f"""# Morgana Living-Off-The-Land Packs

Source-derived LOLBAS and GTFOBins procedures for authorized detection validation and Purple Team exercises. Conversion and import are static operations: no generated command is executed by the build pipeline.

## Corpus

| Provider | Source objects | Raw variants | Published Scripts | Duplicates | Packs |
|---|---:|---:|---:|---:|---:|
| LOLBAS | {lolbas.get('source_objects', 0)} | {lolbas.get('raw_variants', 0)} | {lolbas.get('published', 0)} | {lolbas.get('duplicates', 0)} | {lolbas.get('packs', 0)} |
| GTFOBins | {gtfobins.get('source_objects', 0)} | {gtfobins.get('raw_variants', 0)} | {gtfobins.get('published', 0)} | {gtfobins.get('duplicates', 0)} | {gtfobins.get('packs', 0)} |
| **Combined** | **{combined['source_objects']}** | **{combined['raw_variants']}** | **{combined['published_scripts']}** | **{lolbas.get('duplicates', 0) + gtfobins.get('duplicates', 0)}** | **{combined['packs']}** |

LOLBAS packs contain Windows procedures grouped by the current upstream behavioral category. GTFOBins packs contain Linux/Unix procedures grouped by function and explicit execution context. Packs are deterministically chunked at a maximum of 400 Scripts and intentionally contain no mass-generated one-step Chains.

## Execution Readiness

- `ready`: self-contained source command.
- `ready_with_parameters`: requires operator-supplied Morgana Tags.
- `environment_prerequisite`: requires a preconfigured sudo, SUID, or capability context.
- `interactive`: retains source interactive behavior and requires an appropriate session.
- `manual_counterpart_required`: requires separately controlled listener, connector, sender, or receiver infrastructure.

Morgana does not grant privileges, modify sudoers, configure SUID/capabilities, or start attacker-side infrastructure. Remote targets and paths are blank operator-supplied Tags.

## Updating

Run `morgana/excalibur/tools/update-lotl-packs.ps1`. It updates both source repositories, records SHAs, runs compact fixture tests, converts the complete corpus, reconciles all variants, validates every generated Script/package/catalog entry, and stops. Use `-SmokeImport` only to import one representative package per provider without execution. Publication requires explicit `-Publish` approval.

## Provenance

- LOLBAS: `{lolbas.get('source_commit', 'not converted')}` / GPL-3.0
- GTFOBins: `{gtfobins.get('source_commit', 'not converted')}` / GPL-3.0
- Unique ATT&CK techniques: {combined['unique_tcodes']}
- Conversion validation: {combined['validation']}

See `conversion-report.json` for provider/category/context/TCode/readiness counts and `source-inventory.json` for source-level coverage accounting.
"""


def update_catalog(entries: list[dict[str, Any]]) -> None:
    catalog = json.loads(CATALOG_FILE.read_text(encoding="utf-8"))
    catalog["packs"] = [
        item for item in catalog.get("packs", [])
        if item.get("provider") not in {"lolbas", "gtfobins"}
    ] + entries
    catalog["catalog_version"] = "1.7.0"
    catalog["updated"] = str(date.today())
    providers = [item for item in catalog.get("providers", []) if item.get("id") not in {"lolbas", "gtfobins"}]
    providers.extend([
        {"id": "lolbas", "name": "LOLBAS Project", "type": "upstream", "repository": "https://github.com/LOLBAS-Project/LOLBAS", "domain": "enterprise-attack"},
        {"id": "gtfobins", "name": "GTFOBins", "type": "upstream", "repository": "https://github.com/GTFOBins/GTFOBins.github.io", "domain": "enterprise-attack"},
    ])
    catalog["providers"] = providers
    categories = [item for item in catalog.get("categories", []) if item.get("id") not in {"lotl/lolbas", "lotl/gtfobins"}]
    categories.extend([
        {"id": "lotl/lolbas", "label": "LOLBAS / Windows", "group": "Living Off The Land", "order": 400, "provider": "lolbas"},
        {"id": "lotl/gtfobins", "label": "GTFOBins / Linux", "group": "Living Off The Land", "order": 410, "provider": "gtfobins"},
    ])
    catalog["categories"] = categories
    write_json(CATALOG_FILE, catalog)


def load_risk_overrides(path: Path = RISK_OVERRIDES_FILE) -> dict[str, str]:
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}


def main() -> int:
    parser = argparse.ArgumentParser(description="Build complete LOLBAS + GTFOBins Morgana packs")
    parser.add_argument("--lolbas-dir", type=Path, required=True)
    parser.add_argument("--gtfobins-dir", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--provider", choices=("both", "lolbas", "gtfobins"), default="both")
    parser.add_argument("--category")
    parser.add_argument("--function")
    parser.add_argument("--context")
    parser.add_argument("--max-per-pack", type=int, default=400)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--report-only", action="store_true")
    parser.add_argument("--no-update-catalog", action="store_true")
    parser.add_argument("--verbose", action="store_true")
    arguments = parser.parse_args()
    if not 50 <= arguments.max_per_pack <= 1000:
        raise ValueError("--max-per-pack must be between 50 and 1000")

    from convert_gtfobins import convert_gtfobins
    from convert_lolbas import convert_lolbas

    overrides = load_risk_overrides()
    packages: list[tuple[dict[str, Any], str]] = []
    reports: dict[str, Any] = {}
    inventory: list[dict[str, Any]] = []
    sources = {
        "lolbas": (arguments.lolbas_dir.resolve(), "https://github.com/LOLBAS-Project/LOLBAS"),
        "gtfobins": (arguments.gtfobins_dir.resolve(), "https://github.com/GTFOBins/GTFOBins.github.io"),
    }
    selected = ("lolbas", "gtfobins") if arguments.provider == "both" else (arguments.provider,)
    for provider in selected:
        source_dir, repository = sources[provider]
        commit, commit_date = git_identity(source_dir)
        converter = convert_lolbas if provider == "lolbas" else convert_gtfobins
        procedures, stats, rows = converter(
            source_dir, overrides, arguments.category,
            arguments.function, arguments.context, arguments.verbose,
        )
        unique = deduplicate(procedures, stats)
        duplicate_source_ids = set(stats.metrics.pop("duplicate_source_ids", []))
        for row in rows:
            if row.get("source_id") in duplicate_source_ids:
                row["status"] = "duplicate"
        validation_errors = [
            {"source_id": procedure.source_id, "errors": errors}
            for procedure in unique if (errors := validate_procedure(procedure))
        ]
        if validation_errors:
            raise ValueError(f"{provider}: {len(validation_errors)} normalized procedures failed validation: {validation_errors[:3]}")
        if not stats.reconciles():
            raise ValueError(f"{provider}: coverage reconciliation failed: {stats.report()}")
        provider_packages = build_packs(unique, provider, commit, repository, "GPL-3.0", arguments.max_per_pack)
        packages.extend(provider_packages)
        reports[provider] = {
            "source_repository": repository,
            "source_commit": commit,
            "source_commit_date": commit_date,
            "source_license": "GPL-3.0",
            "packs": len(provider_packages),
            **stats.report(),
        }
        inventory.extend(rows)

    combined_procedures = sum(item["published"] for item in reports.values())
    report = {
        **reports,
        "combined": {
            "source_objects": sum(item["source_objects"] for item in reports.values()),
            "raw_variants": sum(item["raw_variants"] for item in reports.values()),
            "published_scripts": combined_procedures,
            "packs": len(packages),
            "unique_tcodes": len({tcode for package, _ in packages for tcode in package["mitre_tcodes"]}),
            "windows": sum(len(package["scripts"]) for package, _ in packages if package["platform"] == ["windows"]),
            "linux": sum(len(package["scripts"]) for package, _ in packages if package["platform"] == ["linux"]),
            "risk_counts": dict(Counter(script["operational_risk"] for package, _ in packages for script in package["scripts"])),
            "readiness_counts": dict(Counter(script["source_metadata"]["readiness"] for package, _ in packages for script in package["scripts"])),
            "validation": "PASS",
        },
    }
    if arguments.dry_run or arguments.report_only:
        print(json.dumps(report, indent=2))
        return 0

    staging = Path(tempfile.mkdtemp(prefix="lotl-output-", dir=str(arguments.out_dir.parent)))
    try:
        for package, relative in packages:
            write_json(staging / relative, package)
        write_json(staging / "conversion-report.json", report)
        write_json(staging / "source-inventory.json", inventory)
        (staging / "README.md").write_text(readme_text(report), encoding="utf-8")
        (staging / "LICENSE-NOTICE.md").write_text(
            "# License Notice\n\nLOLBAS and GTFOBins source content is licensed GPL-3.0. Generated packages preserve provider, repository, commit, and source-path attribution. Separate legal review is recommended before proprietary redistribution.\n",
            encoding="utf-8",
        )
        if arguments.out_dir.exists():
            shutil.rmtree(arguments.out_dir)
        staging.replace(arguments.out_dir)
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    if not arguments.no_update_catalog:
        update_catalog([catalog_entry(package, relative) for package, relative in packages])
    print(f"[LOTL] Wrote {len(packages)} packs and {combined_procedures} scripts; validation PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())