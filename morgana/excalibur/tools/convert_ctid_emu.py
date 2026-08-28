#!/usr/bin/env python3
"""Convert CTID threat-informed plans into Morgana packages and complex Chains.

The converter reads source documents and commands but never executes procedures,
payloads, source code, build instructions, or external tools.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
from collections import Counter
from datetime import date
from pathlib import Path
from typing import Any

import yaml

TOOLS_DIR = Path(__file__).resolve().parent
EXCALIBUR_DIR = TOOLS_DIR.parent
DEFAULT_OUTPUT_DIR = EXCALIBUR_DIR / "ctid"
CATALOG_FILE = EXCALIBUR_DIR / "catalog.json"
OVERRIDES_FILE = TOOLS_DIR / "ctid_plan_overrides.json"
SOURCE_NAME = "mitre-ctid"
SOURCE_REPOSITORY = "https://github.com/center-for-threat-informed-defense/adversary_emulation_library"
EMU_REPOSITORY = "https://github.com/mitre/emu"
CATALOG_BASE_URL = "https://raw.githubusercontent.com/x3m-ai/Camelot/main/morgana/excalibur/ctid"
VALID_TCODE = re.compile(r"^T\d{4}(?:\.\d{3})?$")
PLACEHOLDER = re.compile(r"#\{([^{}]+)\}")
SENSITIVE = re.compile(r"password|passwd|secret|token|credential|private.?key|hash", re.I)
TARGET_VALUE = re.compile(r"(?:^|\.)(?:ip|host|hostname|server|domain|user|username|share|path|url)(?:$|\.)", re.I)
UNSAFE_RUNTIME = re.compile(
    r"(?:/file/download|\bsandcat\b|\bexec-background\b|\bcaldera\b|\bmeterpreter\b|\bimplant\b)",
    re.I,
)
REMOTE_URL = re.compile(r"https?://[^\s'\"`]+", re.I)
IPV4 = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
LITERAL_CREDENTIAL = re.compile(r"(?:/p:|--password\b|-password\b|password\s*=)\s*['\"]?[^#\s'\"]+", re.I)
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
RISK_LEVELS = ("observe", "interact", "modify", "disrupt")
INITIAL_FULL_PLAN = "wizard_spider"
INITIAL_MICRO_PLAN = "ad_enum"


def slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def tag_key(plan_slug: str, source_key: str) -> str:
    key = re.sub(r"[^a-z0-9]+", "_", source_key.lower()).strip("_")
    return f"ctid_{plan_slug.replace('-', '_')}_{key}"[:120]


def git_value(path: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(path), *args], capture_output=True, text=True, check=True
    )
    return result.stdout.strip()


def source_date(path: Path) -> str:
    return git_value(path, "show", "-s", "--format=%cs", "HEAD")


def executor_name(raw: str) -> str | None:
    names = [name.strip().lower() for name in raw.split(",") if name.strip()]
    resolved = {EXECUTORS.get(name) for name in names}
    if None in resolved or len(resolved) != 1:
        return None
    return resolved.pop()


def risk_for(tactic: str, command: str) -> str:
    value = f"{tactic} {command}".lower()
    if re.search(r"ransom|encrypt|delete.*shadow|clear.*log|shutdown|reboot|stop-service|format\b", value):
        return "disrupt"
    if re.search(r"persistence|privilege|credential|lateral|reg(?:\.exe)?\s+add|net\s+user|schtasks.*create", value):
        return "modify"
    if re.search(r"collection|command-and-control|exfiltration|initial-access|execution", value):
        return "interact"
    return "observe"


def behavior_family(tactic: str, tcode: str, name: str) -> str:
    value = f"{tactic} {tcode} {name}".lower()
    if re.search(r"impact|ransom|encrypt|inhibit|shadow|recovery", value):
        return "impact"
    if re.search(r"exfil|command.and.control|\bc2\b|named.pipe", value):
        return "network"
    if re.search(r"collect|archive|stage|screenshot|email|file.access", value):
        return "collection"
    if re.search(r"credential|password|token|kerberoast|hash", value):
        return "credential"
    if re.search(r"persist|registry|startup|service|scheduled", value):
        return "persistence"
    if re.search(r"lateral|remote|rdp|smb|ssh", value):
        return "lateral"
    if re.search(r"defen[cs]e.evasion|clear|delete|masquerad|obfuscat", value):
        return "evasion"
    if re.search(r"discover|enumerat|system info|process|network|account|group", value):
        return "discovery"
    if re.search(r"execution|initial.access|user execution|inject|loading|foothold|\brce\b|webshell", value):
        return "execution"
    return "readiness"


def simulation_platform(text: str, available: list[str]) -> str:
    value = text.lower()
    aliases = {
        "windows": ("windows", "powershell", "winrm"),
        "macos": ("macos", "osx", "mac os"),
        "linux": ("linux", "ubuntu", "kali"),
    }
    scores = {
        platform: sum(value.count(alias) for alias in aliases[platform])
        for platform in aliases
        if platform in available
    }
    if scores and max(scores.values()) > 0:
        return max(scores, key=scores.get)
    return available[0] if available and available[0] != "all" else "windows"


def simulation_script(platform: str, tactic: str, tcode: str, name: str, source_order: int) -> tuple[str, str, str, str]:
    family = behavior_family(tactic, tcode, name)
    marker = f"CTID-{source_order:03d}-{slug(tcode or 'na')}"
    if platform == "windows" or platform == "all":
        root = "$simulationRoot = Join-Path $env:TEMP 'Morgana\\CTID'; New-Item -ItemType Directory -Path $simulationRoot -Force | Out-Null; "
        artifact = f"$artifactPath = Join-Path $simulationRoot '{marker}.txt'; "
        actions = {
            "readiness": "$environment = [ordered]@{Computer=$env:COMPUTERNAME;User=$env:USERNAME;PowerShell=$PSVersionTable.PSVersion.ToString()}; $environment | ConvertTo-Json -Compress | Set-Content $artifactPath; Get-Content $artifactPath; ",
            "discovery": "Get-CimInstance Win32_OperatingSystem | Select-Object Caption,Version,LastBootUpTime; Get-Process | Select-Object -First 10 Name,Id,Path; Get-NetIPConfiguration -ErrorAction SilentlyContinue | Select-Object InterfaceAlias,IPv4Address; ",
            "execution": "$childPath = Join-Path $simulationRoot 'ctid-child.ps1'; Set-Content $childPath \"Write-Output 'CTID child process telemetry'\"; & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $childPath; ",
            "persistence": "$runKey = 'HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\Run'; New-ItemProperty -Path $runKey -Name 'MorganaCTIDSimulation' -Value 'cmd.exe /c exit 0' -PropertyType String -Force | Out-Null; Get-ItemProperty $runKey -Name 'MorganaCTIDSimulation'; ",
            "credential": "Set-Content $artifactPath 'credential_fixture=synthetic_value'; Select-String -Path $artifactPath -Pattern 'credential_fixture'; ",
            "collection": "$collectionDir = Join-Path $simulationRoot 'collection'; New-Item -ItemType Directory $collectionDir -Force | Out-Null; 1..3 | ForEach-Object { Set-Content (Join-Path $collectionDir \"sample-$_.txt\") \"CTID sample data $_\" }; Compress-Archive -Path (Join-Path $collectionDir '*') -DestinationPath (Join-Path $simulationRoot 'collection.zip') -Force; Get-Item (Join-Path $simulationRoot 'collection.zip'); ",
            "network": "$listener = [Net.Sockets.TcpListener]::new([Net.IPAddress]::Loopback,0); $listener.Start(); $port = ([Net.IPEndPoint]$listener.LocalEndpoint).Port; $client = [Net.Sockets.TcpClient]::new('127.0.0.1',$port); $serverClient = $listener.AcceptTcpClient(); $bytes = [Text.Encoding]::UTF8.GetBytes('CTID network simulation'); $client.GetStream().Write($bytes,0,$bytes.Length); $buffer = New-Object byte[] 64; $read = $serverClient.GetStream().Read($buffer,0,$buffer.Length); [Text.Encoding]::UTF8.GetString($buffer,0,$read); $client.Close(); $serverClient.Close(); $listener.Stop(); ",
            "lateral": "Test-NetConnection -ComputerName 127.0.0.1 -Port 445 -InformationLevel Detailed | Select-Object ComputerName,RemotePort,TcpTestSucceeded; ",
            "evasion": "Set-Content $artifactPath 'CTID transient activity'; Clear-Content $artifactPath; Get-Item $artifactPath | Select-Object FullName,Length,LastWriteTime; ",
            "impact": "$impactDir = Join-Path $simulationRoot 'impact-sandbox'; New-Item -ItemType Directory $impactDir -Force | Out-Null; 1..5 | ForEach-Object { Set-Content (Join-Path $impactDir \"sandbox-$_.txt\") 'original'; Set-Content (Join-Path $impactDir \"sandbox-$_.txt\") 'simulated-impact' }; Get-ChildItem $impactDir | Select-Object Name,Length; ",
        }
        command = (
            f"Write-Output '[START] CTID simulation {tcode}'; " + root + artifact
            + actions[family]
            + f"Write-Output '[SUCCESS] CTID simulation {tcode} family={family}';"
        )
        cleanup = (
            "$simulationRoot = Join-Path $env:TEMP 'Morgana\\CTID'; "
            "Remove-Item $simulationRoot -Recurse -Force -ErrorAction SilentlyContinue; "
            "Remove-ItemProperty 'HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\Run' -Name 'MorganaCTIDSimulation' -ErrorAction SilentlyContinue;"
        )
        return "powershell", "windows", command, cleanup

    root = "simulation_root=/tmp/morgana-ctid; mkdir -p \"$simulation_root\"; "
    actions = {
        "readiness": "printf 'host=%s user=%s kernel=%s\\n' \"$(hostname)\" \"$(id -un)\" \"$(uname -sr)\" | tee \"$simulation_root/readiness.txt\"; ",
        "discovery": "uname -a; id; ps -eo pid,ppid,user,comm | head -n 12; (ip addr 2>/dev/null || ifconfig 2>/dev/null || true); ",
        "execution": "printf '#!/bin/sh\\necho CTID child process telemetry\\n' > \"$simulation_root/ctid-child.sh\"; chmod 700 \"$simulation_root/ctid-child.sh\"; \"$simulation_root/ctid-child.sh\"; ",
        "persistence": "printf '@reboot /bin/true # Morgana CTID simulation\\n' > \"$simulation_root/ctid-crontab\"; cat \"$simulation_root/ctid-crontab\"; ",
        "credential": "printf 'credential_fixture=synthetic_value\\n' > \"$simulation_root/credentials.txt\"; grep 'credential_fixture' \"$simulation_root/credentials.txt\"; ",
        "collection": "mkdir -p \"$simulation_root/collection\"; printf 'CTID sample data\\n' > \"$simulation_root/collection/sample.txt\"; tar -czf \"$simulation_root/collection.tar.gz\" -C \"$simulation_root\" collection; ls -l \"$simulation_root/collection.tar.gz\"; ",
        "network": "python3 -c \"import socket,threading; s=socket.socket(); s.bind(('127.0.0.1',0)); s.listen(1); p=s.getsockname()[1]; threading.Thread(target=lambda: s.accept()[0].recv(64),daemon=True).start(); c=socket.create_connection(('127.0.0.1',p)); c.sendall(b'CTID network simulation'); c.close(); s.close(); print('loopback network telemetry',p)\"; ",
        "lateral": "(timeout 1 sh -c 'echo CTID > /dev/tcp/127.0.0.1/22' 2>/dev/null || true); echo 'loopback remote-service probe completed'; ",
        "evasion": "printf 'CTID transient activity\\n' > \"$simulation_root/transient.log\"; : > \"$simulation_root/transient.log\"; ls -l \"$simulation_root/transient.log\"; ",
        "impact": "mkdir -p \"$simulation_root/impact-sandbox\"; for item in 1 2 3 4 5; do printf 'original\\n' > \"$simulation_root/impact-sandbox/sandbox-$item.txt\"; printf 'simulated-impact\\n' > \"$simulation_root/impact-sandbox/sandbox-$item.txt\"; done; ls -l \"$simulation_root/impact-sandbox\"; ",
    }
    command = f"echo '[START] CTID simulation {tcode}'; {root}{actions[family]}echo '[SUCCESS] CTID simulation {tcode} family={family}'"
    cleanup = "rm -rf /tmp/morgana-ctid"
    return "bash", "macos" if platform == "macos" else "linux", command, cleanup


def clean_summary(text: str, limit: int = 700) -> str:
    compact = re.sub(r"\s+", " ", text or "").strip()
    return compact[:limit].rstrip()


def markdown_instruction_summary(section: str) -> str:
    overview = re.search(
        r"(?ims)^#{2,5}\s+[^\n]*overview[^\n]*\n(.*?)(?=^#{2,5}\s+|\Z)",
        section,
    )
    text = overview.group(1) if overview else section
    text = re.sub(r"```.*?```", " ", text, flags=re.DOTALL)
    text = re.sub(r"!\[[^\]]*\]\([^)]*\)", " ", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"(?im)^#{1,6}\s+.*$", " ", text)
    text = re.sub(r"(?m)^\s*---+\s*$", " ", text)
    text = re.sub(r"(?i)(password\s*[:=]\s*)\S+", r"\1<redacted>", text)
    text = re.sub(r"\b(?:\d{1,3}\.){3}\d{1,3}\b", "<target address>", text)
    return clean_summary(text, 900)


def github_anchor(value: str) -> str:
    return re.sub(r"[^a-z0-9 -]", "", value.lower()).replace(" ", "-")


def classify_requirements(requirements: Any) -> list[dict[str, Any]]:
    classified = []
    for requirement in requirements if isinstance(requirements, list) else []:
        text = json.dumps(requirement, sort_keys=True).lower()
        classes = []
        if "plugins.emu" in text or "caldera" in text or "registered" in text:
            classes.append("external_c2")
        if "source" in text or "fact" in text or "artifact" in text:
            classes.append("prior_step")
        if "payload" in text or "file" in text:
            classes.append("payload")
        if "admin" in text or "privilege" in text or "elevat" in text:
            classes.append("privilege")
        if "network" in text or "host" in text or "domain" in text:
            classes.append("network")
        if "user" in text or "interaction" in text or "manual" in text:
            classes.append("user_interaction")
        classified.append({
            "classes": sorted(set(classes)) or ["environment"],
            "source": requirement,
        })
    return classified


def plan_yaml_files(library_dir: Path) -> list[Path]:
    return sorted(
        path
        for path in library_dir.glob("*/Emulation_Plan/yaml/*")
        if path.suffix.lower() in {".yaml", ".yml"}
    )


def micro_plan_dirs(library_dir: Path) -> list[Path]:
    root = library_dir / "micro_emulation_plans" / "src"
    return sorted(path for path in root.iterdir() if path.is_dir()) if root.is_dir() else []


def full_plan_dirs(library_dir: Path) -> list[Path]:
    return sorted(path.parent for path in library_dir.glob("*/Emulation_Plan") if path.is_dir())


def read_yaml(path: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    loaded = yaml.safe_load(path.read_text(encoding="utf-8-sig")) or []
    if not isinstance(loaded, list):
        raise ValueError(f"{path}: plan root must be an array")
    details: dict[str, Any] = {}
    procedures: list[dict[str, Any]] = []
    for entry in loaded:
        if not isinstance(entry, dict):
            continue
        if isinstance(entry.get("emulation_plan_details"), dict):
            details = entry["emulation_plan_details"]
        else:
            procedures.append(entry)
    if not details or not procedures:
        raise ValueError(f"{path}: plan details or procedures are missing")
    return details, procedures


def input_metadata(plan_slug: str, procedures: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    metadata: dict[str, dict[str, Any]] = {}
    for procedure in procedures:
        for source_key, value in (procedure.get("input_arguments") or {}).items():
            item = value if isinstance(value, dict) else {}
            key = tag_key(plan_slug, str(source_key))
            sensitive = bool(SENSITIVE.search(str(source_key)))
            target = bool(TARGET_VALUE.search(str(source_key)))
            default = item.get("default")
            preserve_default = default if not sensitive and not target and isinstance(default, (str, int, float, bool)) else ""
            default_class = "credential-like" if sensitive else "network-target" if target else "generic"
            metadata[str(source_key)] = {
                "key": key,
                "label": str(source_key).replace(".", " ").replace("_", " ").title(),
                "description": clean_summary(str(item.get("description") or f"CTID plan input: {source_key}"), 300),
                "default": str(preserve_default) if preserve_default != "" else "",
                "example": "",
                "sensitive": sensitive,
                "required": True,
                "parameter_class": "connection" if target else "control",
                "source_default_class": default_class,
            }
    return metadata


def rewrite_placeholders(command: str, metadata: dict[str, dict[str, Any]]) -> tuple[str, list[str], list[str]]:
    required: list[str] = []
    unknown: list[str] = []

    def replace(match: re.Match) -> str:
        source_key = match.group(1)
        item = metadata.get(source_key)
        if not item:
            unknown.append(source_key)
            return match.group(0)
        if item["key"] not in required:
            required.append(item["key"])
        return f"#{{{item['key']}}}"

    return PLACEHOLDER.sub(replace, command), required, unknown


def source_documentation_url(relative_plan: str) -> str:
    return f"{SOURCE_REPOSITORY}/tree/master/{relative_plan.replace(os.sep, '/')}"


def convert_full_plan(path: Path, library_dir: Path, source_commit: str, emu_commit: str) -> tuple[dict, dict, list[dict]]:
    details, procedures = read_yaml(path)
    actor = str(details.get("adversary_name") or path.stem)
    plan_slug = slug(actor)
    package_id = f"ctid-{plan_slug}-v1"
    inputs = input_metadata(plan_slug, procedures)
    scripts: list[dict[str, Any]] = []
    flow_nodes: list[dict[str, Any]] = []
    inventory: list[dict[str, Any]] = []
    used_names: Counter[str] = Counter()
    statuses: Counter[str] = Counter()

    for source_order, procedure in enumerate(procedures, start=1):
        procedure_id = str(procedure.get("id") or f"procedure-{source_order}")
        procedure_name = clean_summary(str(procedure.get("name") or procedure_id), 180)
        tactic = str(procedure.get("tactic") or "Unknown")
        technique = procedure.get("technique") if isinstance(procedure.get("technique"), dict) else {}
        tcode = str(technique.get("attack_id") or "N/A").upper()
        technique_name = str(technique.get("name") or "Unmapped source procedure")
        source_requirements = procedure.get("requirements") or []
        classified_requirements = classify_requirements(source_requirements)
        variants = []
        for platform, executors in (procedure.get("platforms") or {}).items():
            if not isinstance(executors, dict):
                continue
            for raw_executor, executor_data in executors.items():
                variants.append((str(platform).lower(), str(raw_executor), executor_data or {}))
        if not variants:
            variants = [("all", "manual", {})]

        for variant_index, (platform, raw_executor, executor_data) in enumerate(variants, start=1):
            source_command = str(executor_data.get("command") or "").strip()
            source_cleanup = str(executor_data.get("cleanup") or "").strip()
            payloads = [str(item) for item in (executor_data.get("payloads") or [])]
            executor = executor_name(raw_executor)
            rewritten, required_tags, unknown_tags = rewrite_placeholders(source_command, inputs)
            cleanup, cleanup_tags, cleanup_unknown = rewrite_placeholders(source_cleanup, inputs)
            required_tags.extend(key for key in cleanup_tags if key not in required_tags)
            unknown_tags.extend(cleanup_unknown)

            reasons = []
            if payloads:
                reasons.append("required payloads are not approved for redistribution")
            if executor is None:
                reasons.append(f"unsupported source executor: {raw_executor}")
            if not source_command:
                reasons.append("source command is empty")
            if unknown_tags:
                reasons.append(f"unresolved source facts: {', '.join(sorted(set(unknown_tags)))}")
            if UNSAFE_RUNTIME.search(source_command):
                reasons.append("source command depends on CALDERA, external C2, or implant primitives")
            if classified_requirements:
                classes = sorted({value for item in classified_requirements for value in item["classes"]})
                reasons.append(f"source requirements need manual verification: {', '.join(classes)}")
            if REMOTE_URL.search(source_command):
                reasons.append("hard-coded remote URL requires explicit operator review")
            hardcoded_ips = [value for value in IPV4.findall(source_command) if not value.startswith("127.")]
            if hardcoded_ips:
                reasons.append("hard-coded network address requires explicit operator review")
            if LITERAL_CREDENTIAL.search(source_command):
                reasons.append("literal credential-like command argument requires explicit operator review")
            ready = not reasons
            status = "ready" if ready else "simulated"
            statuses[status] += 1

            base_name = f"CTID - {actor} - {tcode} - {procedure_name}"
            suffix = f" [{platform}/{raw_executor}]" if len(variants) > 1 else ""
            candidate = base_name + suffix
            used_names[candidate] += 1
            script_name = candidate
            if used_names[candidate] > 1:
                script_name = f"{candidate} [{source_order}.{variant_index}]"
            description = clean_summary(str(procedure.get("description") or procedure_name), 800)
            if not ready:
                description += " Morgana-native operational simulation used because: " + "; ".join(reasons) + "."
            source_path = str(path.relative_to(library_dir)).replace(os.sep, "/")
            source_url = f"{SOURCE_REPOSITORY}/blob/{source_commit}/{source_path}"
            if ready:
                resolved_executor = executor
                resolved_platform = "macos" if platform == "darwin" else platform
                command = rewritten
                cleanup_command = cleanup if cleanup else None
                resolved_tags = required_tags
            else:
                resolved_executor, resolved_platform, command, cleanup_command = simulation_script(
                    "macos" if platform == "darwin" else platform,
                    tactic,
                    tcode,
                    procedure_name,
                    source_order,
                )
                resolved_tags = []
            script = {
                "id": script_name,
                "name": script_name,
                "description": description,
                "tactic": tactic,
                "tcode": tcode,
                "technique_name": technique_name,
                "executor": resolved_executor,
                "platform": resolved_platform,
                "required_tags": resolved_tags,
                "required_assets": [],
                "command": command,
                "cleanup_command": cleanup_command,
                "operational_risk": risk_for(tactic, rewritten),
                "source_metadata": {
                    "provider": SOURCE_NAME,
                    "plan": actor,
                    "plan_type": "full-emulation",
                    "source_plan_id": details.get("id"),
                    "source_ability_id": procedure_id,
                    "source_order": source_order,
                    "procedure_step": procedure.get("procedure_step"),
                    "procedure_group": procedure.get("procedure_group"),
                    "cti_source": procedure.get("cti_source"),
                    "source_path": source_path,
                    "source_documentation": source_url,
                    "simulation_reasons": reasons if not ready else [],
                    "simulation_family": behavior_family(tactic, tcode, procedure_name) if not ready else None,
                    "source_commit": source_commit,
                    "conversion_status": status,
                    "manual_reasons": reasons,
                    "source_payloads": payloads,
                    "source_requirements": source_requirements,
                    "classified_requirements": classified_requirements,
                    "repeatable": procedure.get("repeatable"),
                },
            }
            scripts.append(script)
            flow_nodes.append({
                "id": f"procedure-{source_order:03d}-{variant_index}",
                "type": "script",
                "script_ref": script_name,
                "source_step": procedure.get("procedure_step"),
            })
            inventory.append({
                "plan": actor,
                "plan_type": "full-emulation",
                "procedure_id": procedure_id,
                "procedure_step": procedure.get("procedure_step"),
                "source_order": source_order,
                "name": procedure_name,
                "technique": tcode,
                "platform": platform,
                "executor": raw_executor,
                "payloads": payloads,
                "requirements": classified_requirements,
                "conversion_status": status,
                "generated_script": script_name,
                "limitations": reasons,
            })

    tags = [item for item in inputs.values() if item["key"] in {key for script in scripts for key in script["required_tags"]}]
    scenario_names = ["Canonical Emulation Flow"]
    documentation_url = source_documentation_url(str(path.parents[2].relative_to(library_dir)))
    description = (
        f"Threat-informed {actor} full emulation based on {len(procedures)} ordered CTID procedures. "
        f"Use it to assess cross-tactic detection and response across a documented multi-stage intrusion; "
        f"{statuses['ready']} procedure variants use source commands and {statuses['simulated']} use executable Morgana-native simulations."
    )
    canonical_chain = {
        "name": f"CTID - {actor} - Canonical Emulation Flow",
        "description": f"Source-ordered {actor} emulation flow. Self-contained source commands run directly; unavailable payload, C2, and executor dependencies use labeled operational simulations.",
        "objective": f"Emulate the documented multi-stage {actor} intrusion flow to validate cross-tactic detection and response coverage.",
        "author": "MITRE CTID / X3M.AI conversion",
        "tags": ["ctid", "threat-informed", "full-emulation", f"adversary:{plan_slug}"],
        "source_metadata": {
            "provider": SOURCE_NAME,
            "plan_type": "full-emulation",
            "adversary": actor,
            "source_plan_id": details.get("id"),
            "scenario_id": "canonical",
            "source_commit": source_commit,
            "source_documentation": documentation_url,
        },
        "plan_type": "full-emulation",
        "adversary": actor,
        "scenario_id": "canonical",
        "scenario_name": "Canonical Emulation Flow",
        "flow": {"nodes": flow_nodes},
    }
    chains = [canonical_chain]
    overrides = json.loads(OVERRIDES_FILE.read_text(encoding="utf-8")) if OVERRIDES_FILE.is_file() else {}
    plan_override = overrides.get(plan_slug, {})
    source_document = str(plan_override.get("source_document") or "")
    for phase in plan_override.get("phase_chains", []):
        prefixes = tuple(str(value) for value in phase.get("step_prefixes", []))
        phase_nodes = [
            node for node in flow_nodes
            if str(node.get("source_step") or "").startswith(prefixes)
        ]
        if not phase_nodes:
            continue
        phase_id = str(phase["id"])
        phase_name = str(phase["name"])
        chains.append({
            "name": f"CTID - {actor} - {phase_name}",
            "description": str(phase["description"]),
            "objective": str(phase["objective"]),
            "author": "MITRE CTID / X3M.AI conversion",
            "tags": ["ctid", "threat-informed", "full-emulation", "phase", f"adversary:{plan_slug}"],
            "source_metadata": {
                "provider": SOURCE_NAME,
                "plan_type": "full-emulation",
                "adversary": actor,
                "source_plan_id": details.get("id"),
                "scenario_id": phase_id,
                "source_commit": source_commit,
                "source_documentation": source_documentation_url(source_document) if source_document else documentation_url,
                "override_reason": plan_override.get("reason"),
            },
            "plan_type": "full-emulation",
            "adversary": actor,
            "scenario_id": phase_id,
            "scenario_name": phase_name,
            "flow": {"nodes": phase_nodes},
        })
    package = {
        "package_id": package_id,
        "package_name": f"CTID - {actor} Full Emulation",
        "version": "1.0.0",
        "description": description,
        "summary": f"Threat-informed emulation of documented {actor} behavior and attack progression.",
        "purpose": f"Validate defensive performance across a multi-stage {actor} scenario rather than isolated techniques.",
        "capabilities": [
            f"Preserves {len(procedures)} CTID procedures in source order across {len({script['tactic'] for script in scripts})} tactics.",
            "Creates operational Morgana Attack Chains using source commands and labeled telemetry simulations.",
            "Retains CTI references, procedure steps, source requirements, ATT&CK mappings, and conversion limitations.",
        ],
        "use_cases": [
            f"Run a threat-informed Purple Team assessment modeled on documented {actor} behaviors.",
            "Evaluate cross-stage prevention, telemetry, detection, investigation, and response handoffs.",
            "Customize a source-faithful baseline Chain for an authorized environment while retaining provenance.",
        ],
        "safety_notes": [
            "Review every source command, simulation, required Tag, and cleanup action before execution.",
            "Payload-dependent and external C2 procedures use sandboxed or loopback Morgana simulations until exact dependencies are packaged.",
            "Threat-informed adversary emulation content is for explicitly authorized security validation and defensive testing only.",
        ],
        "author": "MITRE CTID / X3M.AI conversion",
        "created": str(date.today()),
        "script_prefix": "CTID - ",
        "provider": SOURCE_NAME,
        "source": "ctid-adversary-emulation-library",
        "source_repository": SOURCE_REPOSITORY,
        "source_commit": source_commit,
        "source_license": "Apache-2.0",
        "reference_converter": {"name": "MITRE Emu", "repository": EMU_REPOSITORY, "commit": emu_commit},
        "documentation_url": documentation_url,
        "mitre_domain": "enterprise-attack",
        "attack_version": str(details.get("attack_version") or ""),
        "mitre_tactic": "Multiple",
        "mitre_tcodes": sorted({script["tcode"] for script in scripts if VALID_TCODE.fullmatch(script["tcode"])}),
        "platform": sorted({script["platform"] for script in scripts}),
        "plan_type": "full-emulation",
        "adversary": actor,
        "intelligence_summary": clean_summary(str(details.get("adversary_description") or ""), 600),
        "scenario_count": 1,
        "scenario_names": scenario_names,
        "chain_names": [chain["name"] for chain in chains],
        "complexity": "advanced",
        "source_procedure_count": len(procedures),
        "converted_procedure_count": len(scripts),
        "manual_procedure_count": 0,
        "simulated_procedure_count": statuses["simulated"],
        "skipped_procedure_count": 0,
        "prerequisites": [
            "Morgana Agent installed on each explicitly authorized execution host",
            "Plan Tags configured for the lab; credential and target defaults are intentionally blank",
            "Operator review of every source command, simulation, and external dependency before Chain execution",
        ],
        "tag_categories": [{
            "category_id": f"ctid_{plan_slug.replace('-', '_')}_inputs",
            "label": f"{actor} Scenario Inputs",
            "description": "Plan-wide CTID facts required by automated procedure variants.",
            "scope": "local",
            "used_by_tcodes": sorted({script["tcode"] for script in scripts if script["required_tags"]}),
            "tags": tags,
        }] if tags else [],
        "assets": [],
        "scripts": scripts,
        "chains": chains,
    }
    report = {
        "package_id": package_id,
        "plan": actor,
        "plan_type": "full-emulation",
        "source_procedures": len(procedures),
        "generated_scripts": len(scripts),
        "automated": len(scripts),
        "source_commands": statuses["ready"],
        "simulated": statuses["simulated"],
        "manual": 0,
        "status_counts": dict(statuses),
        "chains": len(chains),
        "phase_chains": len(chains) - 1,
        "scenarios": package["scenario_count"],
        "techniques": len(package["mitre_tcodes"]),
        "platforms": package["platform"],
        "known_limitations": sorted({reason for item in inventory for reason in item["limitations"]}),
    }
    return package, report, inventory


def convert_ad_enum(library_dir: Path, source_commit: str, emu_commit: str) -> tuple[dict, dict, list[dict]]:
    plan_dir = library_dir / "micro_emulation_plans" / "src" / INITIAL_MICRO_PLAN
    return convert_micro_plan(plan_dir, library_dir, source_commit, emu_commit)


def convert_micro_plan(plan_dir: Path, library_dir: Path, source_commit: str, emu_commit: str) -> tuple[dict, dict, list[dict]]:
    if not plan_dir.is_dir():
        raise ValueError(f"micro plan not found: {plan_dir}")
    readme_path = plan_dir / "README.md"
    readme = readme_path.read_text(encoding="utf-8-sig") if readme_path.is_file() else ""
    heading = re.search(r"^#\s+(?:Micro Emulation Plan:\s*)?(.+?)\s*$", readme, re.MULTILINE | re.I)
    behavior = clean_summary(heading.group(1), 120) if heading else plan_dir.name.replace("_", " ").title()
    plan_slug = slug(plan_dir.name)
    package_id = f"ctid-micro-{plan_slug}-v1"
    techniques = sorted(set(re.findall(r"\bT\d{4}(?:\.\d{3})?\b", readme)))
    primary_tcode = techniques[0] if techniques else "T0000"
    source_files = sorted(
        str(path.relative_to(plan_dir)).replace(os.sep, "/")
        for path in plan_dir.rglob("*")
        if path.is_file() and path.suffix.lower() in {".cs", ".go", ".c", ".cpp", ".py", ".ps1", ".php"}
    )
    asset_candidates = sorted(
        str(path.relative_to(plan_dir)).replace(os.sep, "/")
        for path in plan_dir.rglob("*")
        if path.is_file() and (path.suffix.lower() in {".exe", ".dll", ".zip"} or (not path.suffix and path.stat().st_size > 0))
    )
    searchable_files = " ".join(source_files + asset_candidates).lower()
    platforms = []
    if ".exe" in searchable_files or ".cs" in searchable_files or "windows" in searchable_files:
        platforms.append("windows")
    if "linux" in searchable_files or any(path.endswith(".go") for path in source_files):
        platforms.append("linux")
    if not platforms:
        platforms = ["windows"]
    plan_risk = risk_for("", f"{behavior} {readme[:4000]}")
    script_name = f"CTID MICRO - {behavior} - {primary_tcode} - Operational Simulation"
    documentation_url = source_documentation_url(str(plan_dir.relative_to(library_dir)))
    limitation = "Upstream executable or build output has not yet been pinned, licensed, hashed, and approved for Camelot redistribution."
    simulation_executor, simulation_platform, simulation_command, simulation_cleanup = simulation_script(
        platforms[0], "Focused Behavior", primary_tcode, behavior, 1
    )
    script = {
        "id": script_name,
        "name": script_name,
        "description": f"Executable Morgana-native simulation of {behavior}. " + limitation,
        "tactic": "Multiple" if len(techniques) > 1 else "Focused Behavior",
        "tcode": primary_tcode,
        "technique_name": behavior,
        "executor": simulation_executor,
        "platform": simulation_platform,
        "required_tags": [],
        "required_assets": [],
        "command": simulation_command,
        "cleanup_command": simulation_cleanup,
        "operational_risk": plan_risk,
        "source_metadata": {
            "provider": SOURCE_NAME,
            "plan": behavior,
            "plan_type": "micro-emulation",
            "source_path": str(plan_dir.relative_to(library_dir)).replace(os.sep, "/"),
            "source_commit": source_commit,
            "conversion_status": "simulated",
            "simulation_reasons": [limitation],
            "simulation_family": behavior_family("Focused Behavior", primary_tcode, behavior),
            "source_documentation": f"{SOURCE_REPOSITORY}/blob/{source_commit}/{str((plan_dir / 'README.md').relative_to(library_dir)).replace(os.sep, '/')}",
            "source_files": source_files,
            "unapproved_asset_candidates": asset_candidates,
            "build_documentation": (plan_dir / "BUILD.md").is_file(),
        },
    }
    summary_match = re.search(r"(?:^|\n)(?!#|\*\*Table)([^\n][^\n]+(?:\n[^\n#][^\n]*)*)", readme)
    source_summary = clean_summary(summary_match.group(1), 500) if summary_match else behavior
    package = {
        "package_id": package_id,
        "package_name": f"CTID Micro - {behavior}",
        "version": "1.0.0",
        "description": f"Focused CTID micro emulation for {behavior}. It runs a labeled Morgana-native behavior simulation while retaining provenance for upstream source and asset candidates.",
        "summary": source_summary,
        "purpose": f"Validate defensive telemetry and controls for the compound {behavior} behavior rather than testing one command in isolation.",
        "capabilities": [
            f"Preserves the CTID {behavior} defensive objective and source documentation as a focused Morgana Chain.",
            "Preserves ATT&CK coverage and defensive intent as a focused Morgana Chain.",
            "Runs an operational sandboxed simulation until a reviewed release asset is pinned with SHA256 and license provenance.",
        ],
        "use_cases": [
            f"Plan a repeatable detection-validation exercise for {behavior}.",
            "Review required telemetry and environmental prerequisites before approving the upstream tool.",
            "Compare detections for compound discovery behavior with isolated Atomic or Stockpile procedures.",
        ],
        "safety_notes": [
            "This package dispatches a labeled Morgana-native simulation, never an unreviewed upstream executable.",
            f"Use an explicitly authorized lab suitable for {behavior}; source behavior may alter system or security state.",
            "Pin a specific release asset, license, size, platform, architecture, and SHA256 before enabling automation.",
        ],
        "author": "MITRE CTID / X3M.AI conversion",
        "created": str(date.today()),
        "script_prefix": "CTID MICRO - ",
        "provider": SOURCE_NAME,
        "source": "ctid-adversary-emulation-library",
        "source_repository": SOURCE_REPOSITORY,
        "source_commit": source_commit,
        "source_license": "Apache-2.0",
        "reference_converter": {"name": "MITRE Emu", "repository": EMU_REPOSITORY, "commit": emu_commit},
        "documentation_url": documentation_url,
        "mitre_domain": "enterprise-attack",
        "mitre_tactic": "Multiple" if len(techniques) > 1 else "Focused Behavior",
        "mitre_tcodes": techniques,
        "platform": platforms,
        "plan_type": "micro-emulation",
        "behavior": behavior,
        "scenario_count": 1,
        "scenario_names": [behavior],
        "chain_names": [f"CTID Micro - {behavior}"],
        "complexity": "focused",
        "source_procedure_count": 1,
        "converted_procedure_count": 1,
        "manual_procedure_count": 0,
        "simulated_procedure_count": 1,
        "skipped_procedure_count": 0,
        "prerequisites": [
            f"Explicitly authorized lab suitable for {behavior}",
            "Execution host and privileges required by the upstream plan documentation",
            "Reviewed and pinned CTID release asset before automated execution",
        ],
        "tag_categories": [],
        "assets": [],
        "scripts": [script],
        "chains": [{
            "name": f"CTID Micro - {behavior}",
            "description": f"Focused compound {behavior} scenario implemented as an executable Morgana-native telemetry simulation.",
            "objective": f"Validate detection coverage for compound {behavior} behavior.",
            "author": "MITRE CTID / X3M.AI conversion",
            "tags": ["ctid", "threat-informed", "micro-emulation", f"behavior:{plan_slug}"],
            "source_metadata": {
                "provider": SOURCE_NAME,
                "plan_type": "micro-emulation",
                "behavior": behavior,
                "scenario_id": "primary",
                "source_commit": source_commit,
                "source_documentation": documentation_url,
            },
            "plan_type": "micro-emulation",
            "scenario_id": "primary",
            "scenario_name": behavior,
            "flow": {"nodes": [{"id": f"simulation-{plan_slug}", "type": "script", "script_ref": script_name}]},
        }],
    }
    report = {
        "package_id": package_id,
        "plan": behavior,
        "plan_type": "micro-emulation",
        "source_procedures": 1,
        "generated_scripts": 1,
        "automated": 1,
        "source_commands": 0,
        "simulated": 1,
        "manual": 0,
        "status_counts": {"simulated": 1},
        "chains": 1,
        "scenarios": 1,
        "techniques": len(techniques),
        "platforms": platforms,
        "known_limitations": [limitation],
    }
    inventory = [{
        "plan": behavior,
        "plan_type": "micro-emulation",
        "procedure_id": f"{plan_slug}-tool",
        "name": f"Run {behavior}",
        "techniques": techniques,
        "conversion_status": "simulated",
        "generated_script": script_name,
        "limitations": [limitation],
        "source_files": source_files,
        "unapproved_asset_candidates": asset_candidates,
    }]
    return package, report, inventory


def convert_manual_full_plan(plan_dir: Path, library_dir: Path, source_commit: str, emu_commit: str) -> tuple[dict, dict, list[dict]]:
    readme_path = plan_dir / "README.md"
    readme = readme_path.read_text(encoding="utf-8-sig") if readme_path.is_file() else ""
    documentation_files = sorted((plan_dir / "Emulation_Plan").glob("**/*.md"))
    emulation_docs = "\n".join(
        path.read_text(encoding="utf-8-sig", errors="replace") for path in documentation_files
    )
    heading = re.search(r"^#\s+(.+?)\s*$", readme, re.MULTILINE)
    actor = clean_summary(heading.group(1), 120) if heading else plan_dir.name.replace("_", " ").title()
    plan_slug = slug(actor)
    package_id = f"ctid-{plan_slug}-v1"
    techniques = sorted(set(re.findall(r"\bT\d{4}(?:\.\d{3})?\b", readme + "\n" + emulation_docs)))
    documented_steps = []
    seen_steps = set()
    for document_path in documentation_files:
        document = document_path.read_text(encoding="utf-8-sig", errors="replace")
        step_matches = list(re.finditer(
            r"(?im)^#{1,4}\s+((?:Phase\s+\d+\s*:?\s*)?Step\s+\d+[^\r\n]*)",
            document,
        ))
        for index, match in enumerate(step_matches):
            step_name = clean_summary(match.group(1), 160)
            if step_name in seen_steps:
                continue
            seen_steps.add(step_name)
            section_end = step_matches[index + 1].start() if index + 1 < len(step_matches) else len(document)
            section = document[match.end():section_end]
            relative_document = str(document_path.relative_to(library_dir)).replace(os.sep, "/")
            documented_steps.append({
                "name": step_name,
                "techniques": sorted(set(re.findall(r"\bT\d{4}(?:\.\d{3})?\b", section))),
                "instructions": markdown_instruction_summary(section),
                "source_document": relative_document,
            })
    if not documented_steps:
        documented_steps = [{
            "name": "Manual Canonical Scenario",
            "techniques": techniques,
            "instructions": "Review and perform the canonical source scenario in an explicitly authorized lab.",
            "source_document": str(readme_path.relative_to(library_dir)).replace(os.sep, "/"),
        }]
    step_count = len(documented_steps)
    source_text = f"{readme}\n{emulation_docs}".lower()
    platforms = []
    if "windows" in source_text:
        platforms.append("windows")
    if "linux" in source_text:
        platforms.append("linux")
    if "macos" in source_text or "osx" in source_text:
        platforms.append("macos")
    if not platforms:
        platforms = ["all"]
    documentation_url = source_documentation_url(str(plan_dir.relative_to(library_dir)))
    limitation = "The source plan has no machine-readable YAML; documented stages use labeled Morgana-native behavior simulations rather than inferred source commands."
    summary_match = re.search(r"(?:^|\n)(?!#|\[!)([^\n][^\n]+(?:\n[^\n#][^\n]*)*)", readme)
    summary = clean_summary(summary_match.group(1), 500) if summary_match else f"Threat-informed {actor} emulation plan."
    scripts = []
    flow_nodes = []
    inventory = []
    for order, step in enumerate(documented_steps, start=1):
        step_tcode = step["techniques"][0] if step["techniques"] else "N/A"
        script_name = f"CTID - {actor} - {step_tcode} - {step['name']}"
        step_platform = simulation_platform(f"{step['name']} {step['instructions']}", platforms)
        simulation_executor, resolved_platform, simulation_command, simulation_cleanup = simulation_script(
            step_platform, "Multiple", step_tcode, step["name"], order
        )
        step_documentation_url = (
            f"{SOURCE_REPOSITORY}/blob/{source_commit}/{step['source_document']}"
            f"#{github_anchor(step['name'])}"
        )
        script = {
            "id": script_name,
            "name": script_name,
            "description": f"Executable simulation for documented stage '{step['name']}'. Source context: {step['instructions']}",
            "tactic": "Multiple",
            "tcode": step_tcode,
            "technique_name": step["name"],
            "executor": simulation_executor,
            "platform": resolved_platform,
            "required_tags": [],
            "required_assets": [],
            "command": simulation_command,
            "cleanup_command": simulation_cleanup,
            "operational_risk": risk_for("", f"{step['name']} {step['instructions']}"),
            "source_metadata": {
                "provider": SOURCE_NAME,
                "plan": actor,
                "plan_type": "full-emulation",
                "source_path": str(plan_dir.relative_to(library_dir)).replace(os.sep, "/"),
                "source_commit": source_commit,
                "source_order": order,
                "procedure_step": step["name"],
                "source_documentation": step_documentation_url,
                "conversion_status": "simulated",
                "simulation_reasons": [limitation],
                "simulation_family": behavior_family("Multiple", step_tcode, step["name"]),
            },
        }
        scripts.append(script)
        flow_nodes.append({"id": f"simulation-step-{order:03d}", "type": "script", "script_ref": script_name})
        inventory.append({
            "plan": actor,
            "plan_type": "full-emulation",
            "procedure_id": f"simulation-step-{order:03d}",
            "procedure_step": step["name"],
            "source_order": order,
            "name": step["name"],
            "techniques": step["techniques"],
            "conversion_status": "simulated",
            "generated_script": script_name,
            "limitations": [limitation],
        })
    package = {
        "package_id": package_id,
        "package_name": f"CTID - {actor} Full Emulation",
        "version": "1.0.0",
        "description": f"Threat-informed {actor} full emulation translated from CTID human-readable scenario documentation into labeled executable Morgana-native simulations.",
        "summary": summary,
        "purpose": f"Use the documented {actor} progression to run a multi-stage defensive telemetry exercise without claiming unavailable source commands are original payload execution.",
        "capabilities": [
            f"Preserves the documented {actor} scenario, ATT&CK coverage, and source context as a Morgana Chain.",
            "Makes every documented stage executable through a sandboxed or loopback behavior simulation.",
            "Links every generated Script to the canonical CTID documentation and labels its simulation family.",
        ],
        "use_cases": [
            f"Plan a threat-informed Purple Team assessment based on documented {actor} behavior.",
            "Review scenario scope, infrastructure, techniques, and simulation fidelity before execution.",
            "Exercise an intelligence-led progression without dispatching undocumented offensive payloads.",
        ],
        "safety_notes": [
            limitation,
            "Source resources may include offensive code or encrypted artifacts and are not mirrored or executed by this package.",
            "Use only in an explicitly authorized lab or approved defensive exercise.",
        ],
        "author": "MITRE CTID / X3M.AI conversion",
        "created": str(date.today()),
        "script_prefix": "CTID - ",
        "provider": SOURCE_NAME,
        "source": "ctid-adversary-emulation-library",
        "source_repository": SOURCE_REPOSITORY,
        "source_commit": source_commit,
        "source_license": "Apache-2.0",
        "reference_converter": {"name": "MITRE Emu", "repository": EMU_REPOSITORY, "commit": emu_commit},
        "documentation_url": documentation_url,
        "mitre_domain": "enterprise-attack",
        "attack_version": "",
        "mitre_tactic": "Multiple",
        "mitre_tcodes": techniques,
        "platform": platforms,
        "plan_type": "full-emulation",
        "adversary": actor,
        "intelligence_summary": summary,
        "scenario_count": 1,
        "scenario_names": ["Operational Simulation Flow"],
        "chain_names": [f"CTID - {actor} - Operational Simulation Flow"],
        "complexity": "advanced",
        "source_procedure_count": step_count,
        "converted_procedure_count": step_count,
        "manual_procedure_count": 0,
        "simulated_procedure_count": step_count,
        "skipped_procedure_count": 0,
        "prerequisites": [
            "Review the complete CTID scenario and infrastructure documentation",
            "Explicitly authorize every target, dependency, and manual action",
            "Review each generated simulation and its cleanup before execution",
        ],
        "tag_categories": [],
        "assets": [],
        "scripts": scripts,
        "chains": [{
            "name": f"CTID - {actor} - Operational Simulation Flow",
            "description": f"Executable {actor} scenario using labeled behavior simulations for source-documented stages without machine-readable commands.",
            "objective": f"Generate defensive telemetry across the documented {actor} progression while preserving source limitations.",
            "author": "MITRE CTID / X3M.AI conversion",
            "tags": ["ctid", "threat-informed", "full-emulation", f"adversary:{plan_slug}"],
            "source_metadata": {
                "provider": SOURCE_NAME,
                "plan_type": "full-emulation",
                "adversary": actor,
                "scenario_id": "operational-simulation",
                "source_commit": source_commit,
                "source_documentation": documentation_url,
            },
            "plan_type": "full-emulation",
            "adversary": actor,
            "scenario_id": "operational-simulation",
            "scenario_name": "Operational Simulation Flow",
            "flow": {"nodes": flow_nodes},
        }],
    }
    report = {
        "package_id": package_id,
        "plan": actor,
        "plan_type": "full-emulation",
        "source_procedures": step_count,
        "generated_scripts": len(scripts),
        "automated": step_count,
        "source_commands": 0,
        "simulated": step_count,
        "manual": 0,
        "status_counts": {"simulated": step_count},
        "chains": 1,
        "scenarios": 1,
        "techniques": len(techniques),
        "platforms": platforms,
        "known_limitations": [limitation],
    }
    return package, report, inventory


def catalog_entry(package: dict, relative_url: str) -> dict:
    risks = sorted(
        {script.get("operational_risk") for script in package["scripts"] if script.get("operational_risk")},
        key=RISK_LEVELS.index,
    )
    return {
        "package_id": package["package_id"],
        "package_name": package["package_name"],
        "version": package["version"],
        "summary": package["summary"],
        "description": package["description"],
        "purpose": package["purpose"],
        "capabilities": package["capabilities"],
        "use_cases": package["use_cases"],
        "prerequisites": package["prerequisites"],
        "safety_notes": package["safety_notes"],
        "plan_type": package["plan_type"],
        "adversary": package.get("adversary"),
        "behavior": package.get("behavior"),
        "intelligence_summary": package.get("intelligence_summary"),
        "scenario_count": package["scenario_count"],
        "scenario_names": package["scenario_names"],
        "chain_names": package.get("chain_names", package["scenario_names"]),
        "complexity": package["complexity"],
        "source_procedure_count": package["source_procedure_count"],
        "converted_procedure_count": package["converted_procedure_count"],
        "manual_procedure_count": package["manual_procedure_count"],
        "skipped_procedure_count": package["skipped_procedure_count"],
        "mitre_tactic": package["mitre_tactic"],
        "mitre_tcodes": package["mitre_tcodes"],
        "mitre_domain": package["mitre_domain"],
        "script_count": len(package["scripts"]),
        "chain_count": len(package["chains"]),
        "asset_count": len(package["assets"]),
        "risk_badges": risks,
        "platform": package["platform"],
        "status": "community",
        "provider": SOURCE_NAME,
        "author": package["author"],
        "source": package["source"],
        "source_commit": package["source_commit"],
        "source_license": package["source_license"],
        "documentation_url": package["documentation_url"],
        "category": f"ctid/{package['plan_type']}",
        "url": f"{CATALOG_BASE_URL}/{relative_url}",
    }


def update_catalog(catalog: dict, entries: list[dict]) -> dict:
    by_id = {entry["package_id"]: entry for entry in entries}
    existing = [
        entry for entry in catalog.get("packs", [])
        if not str(entry.get("package_id") or "").startswith("ctid-")
    ]
    existing.extend(entries)
    result = dict(catalog)
    result["catalog_version"] = "1.6.0"
    result["updated"] = str(date.today())
    providers = [item for item in catalog.get("providers", []) if item.get("id") != SOURCE_NAME]
    providers.append({
        "id": SOURCE_NAME,
        "name": "MITRE Center for Threat-Informed Defense",
        "type": "upstream",
        "repository": SOURCE_REPOSITORY,
        "domain": "enterprise-attack",
    })
    categories = [
        item for item in catalog.get("categories", [])
        if item.get("id") not in {"ctid/full-emulation", "ctid/micro-emulation"}
    ]
    categories.extend([
        {"id": "ctid/full-emulation", "label": "CTID / Full Adversary Emulation", "group": "Threat-Informed Emulation", "order": 300, "provider": SOURCE_NAME},
        {"id": "ctid/micro-emulation", "label": "CTID / Micro Emulation", "group": "Threat-Informed Emulation", "order": 310, "provider": SOURCE_NAME},
    ])
    result["providers"] = providers
    result["categories"] = categories
    result["packs"] = existing
    return result


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def readme_text(report: dict) -> str:
    lines = "\n".join(
        f"| {item['plan']} | {item['plan_type'].replace('-', ' ').title()} | {item['generated_scripts']} | {item['automated']} | {item['manual']} | {item['chains']} |"
        for item in report["plans"]
    )
    return f"""# CTID Threat-Informed Emulation Packs

Morgana-native threat-informed packages derived from the MITRE Center for Threat-Informed Defense Adversary Emulation Library. The CTID library is the canonical intelligence and plan source; MITRE Emu is retained only as a conversion reference.

> Use this content only for explicitly authorized security validation, Purple Team exercises, research, and defensive testing.

## Initial Milestone

| Plan | Type | Scripts | Automated | Manual | Chains |
|---|---|---:|---:|---:|---:|
{lines}

The full package preserves CTID procedure order in a modern Morgana `chains[].flow`. No conditional logic is invented: the initial canonical Chain is linear because the selected source plan does not provide a machine-evaluable branch criterion.

## Operational Procedures

Self-contained CTID commands are preserved as source-command Scripts. Procedures that depend on unavailable payloads, external C2 primitives, unsupported executors, or unresolved runtime facts become labeled Morgana-native simulations. Every Chain node is dispatchable; simulations create representative host or network telemetry in a confined workspace and include cleanup.

Micro plans use operational behavior simulations until a specific CTID release asset is reviewed and pinned with source version, license, platform, architecture, size, URL, and SHA256.

## Package Contents

- `full/`: named adversary full-emulation packages and canonical Attack Chains.
- `micro/`: focused compound-behavior packages.
- `plan-manifest.json`: normalized plan/scenario/step representation.
- `source-inventory.json`: per-procedure conversion status, requirements, payload references, and generated Script identity.
- `conversion-report.json`: source/reference commits, completeness metrics, Chain counts, and known limitations.

## Safety And Assets

The converter reads and normalizes source content but never executes procedures, payloads, build instructions, or external tools. No encrypted or malware-like payload is automatically decrypted, downloaded, mirrored, or approved. Reviewed future assets must use Morgana's existing HTTPS and SHA256-verified package asset model.

Credential, target host, server, domain, user, path, share, and URL defaults are blanked for runtime configuration. Operators must supply values for an explicitly authorized environment.

## Updating

Run `morgana/excalibur/tools/update-ctid-emu-packs.ps1`. The pipeline updates both source checkouts, records their SHAs, runs fixture tests, converts content, validates package flows and catalog metadata, and prints the conversion report. It never executes a Chain. Package import is opt-in with `-SmokeImport`; publication is opt-in with `-Publish`.

## Provenance

- CTID source: `{report['source_repository']}`
- CTID commit: `{report['source_commit']}`
- MITRE Emu reference commit: `{report['emu_reference_commit']}`
- License: Apache-2.0

See the package `documentation_url` and per-procedure `cti_source` metadata for full source context.
"""


def main() -> int:
    parser = argparse.ArgumentParser(description="Convert CTID emulation plans into Morgana packages")
    parser.add_argument("--library-dir", required=True, type=Path)
    parser.add_argument("--emu-dir", required=True, type=Path)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--plan", default="all")
    parser.add_argument("--micro-plan", default="all")
    parser.add_argument("--plan-type", choices=["full", "micro", "both"], default="both")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--no-update-catalog", action="store_true")
    arguments = parser.parse_args()

    library_dir = arguments.library_dir.resolve()
    emu_dir = arguments.emu_dir.resolve()
    source_commit = git_value(library_dir, "rev-parse", "HEAD")
    emu_commit = git_value(emu_dir, "rev-parse", "HEAD")
    source_commit_date = source_date(library_dir)
    packages: list[tuple[dict, str]] = []
    reports = []
    inventory = []
    plan_manifest = []

    if arguments.plan_type in {"full", "both"}:
        all_yaml_candidates = plan_yaml_files(library_dir)
        yaml_directories = {path.parents[2].resolve() for path in all_yaml_candidates}
        all_manual_candidates = [
            path for path in full_plan_dirs(library_dir) if path.resolve() not in yaml_directories
        ]
        candidates = all_yaml_candidates
        manual_candidates = all_manual_candidates
        if arguments.plan.lower() != "all":
            requested = slug(arguments.plan)
            candidates = [
                path for path in candidates
                if requested in {slug(path.stem), slug(path.parents[2].name)}
                or requested in slug(read_yaml(path)[0].get("adversary_name", ""))
            ]
            manual_candidates = [
                path for path in manual_candidates
                if requested == slug(path.name)
                or requested in slug(path.name.replace("_", " "))
            ]
        if not candidates and not manual_candidates:
            raise ValueError(f"full plan not found: {arguments.plan}")
        for path in candidates:
            package, report, rows = convert_full_plan(path, library_dir, source_commit, emu_commit)
            output_slug = slug(package["adversary"]).replace("-", "_")
            relative = f"full/{output_slug}/{package['package_id']}.json"
            packages.append((package, relative))
            reports.append(report)
            inventory.extend(rows)
            plan_manifest.append({
                "id": package["package_id"], "name": package["adversary"], "type": "full-emulation",
                "scenarios": [
                    {
                        "id": chain["scenario_id"],
                        "name": chain["scenario_name"],
                        "steps": [node["id"] for node in chain["flow"]["nodes"]],
                    }
                    for chain in package["chains"]
                ],
            })
        for plan_dir in manual_candidates:
            package, report, rows = convert_manual_full_plan(
                plan_dir, library_dir, source_commit, emu_commit
            )
            output_slug = slug(package["adversary"]).replace("-", "_")
            relative = f"full/{output_slug}/{package['package_id']}.json"
            packages.append((package, relative))
            reports.append(report)
            inventory.extend(rows)
            plan_manifest.append({
                "id": package["package_id"], "name": package["adversary"], "type": "full-emulation",
                "scenarios": [
                    {
                        "id": chain["scenario_id"],
                        "name": chain["scenario_name"],
                        "steps": [node["id"] for node in chain["flow"]["nodes"]],
                    }
                    for chain in package["chains"]
                ],
            })

    if arguments.plan_type in {"micro", "both"}:
        micro_candidates = micro_plan_dirs(library_dir)
        if arguments.micro_plan.lower() != "all":
            requested_micro = slug(arguments.micro_plan)
            micro_candidates = [path for path in micro_candidates if slug(path.name) == requested_micro]
        if not micro_candidates:
            raise ValueError(f"micro plan not found: {arguments.micro_plan}")
        for plan_dir in micro_candidates:
            package, report, rows = convert_micro_plan(plan_dir, library_dir, source_commit, emu_commit)
            output_slug = slug(plan_dir.name).replace("-", "_")
            relative = f"micro/{output_slug}/{package['package_id']}.json"
            packages.append((package, relative))
            reports.append(report)
            inventory.extend(rows)
            plan_manifest.append({
                "id": package["package_id"], "name": package["behavior"], "type": "micro-emulation",
                "scenarios": [{"id": "primary", "name": package["scenario_names"][0], "steps": [package["chains"][0]["flow"]["nodes"][0]["id"]]}],
            })

    report = {
        "source": "ctid-adversary-emulation-library",
        "source_repository": SOURCE_REPOSITORY,
        "source_commit": source_commit,
        "source_commit_date": source_commit_date,
        "emu_reference_commit": emu_commit,
        "full_plans": {
            "discovered": len(plan_yaml_files(library_dir)) + len([
                path for path in full_plan_dirs(library_dir)
                if path.resolve() not in {item.parents[2].resolve() for item in plan_yaml_files(library_dir)}
            ]),
            "machine_readable": len(plan_yaml_files(library_dir)),
            "documentation_only_source": len([
                path for path in full_plan_dirs(library_dir)
                if path.resolve() not in {item.parents[2].resolve() for item in plan_yaml_files(library_dir)}
            ]),
            "converted": sum(item["plan_type"] == "full-emulation" for item in reports),
        },
        "micro_plans": {"discovered": len(micro_plan_dirs(library_dir)), "converted": sum(item["plan_type"] == "micro-emulation" for item in reports)},
        "procedures": {
            "discovered": sum(item["source_procedures"] for item in reports),
            "converted": sum(item["automated"] for item in reports),
            "manual": sum(item["manual"] for item in reports),
            "skipped": 0,
        },
        "chains": {
            "canonical": sum(item["plan_type"] == "full-emulation" for item in reports),
            "scenario": sum(item["plan_type"] == "micro-emulation" for item in reports),
            "phase": sum(item.get("phase_chains", 0) for item in reports),
            "conditional": 0,
        },
        "assets": {"approved": 0, "missing_or_unapproved": sum(item["status_counts"].get("unsupported_asset", 0) for item in reports)},
        "plans": reports,
        "known_limitations": [
            "Human-readable alternative scenario and phase boundaries are not converted without a reviewed machine-readable manifest override.",
            "Canonical full-plan Chains preserve YAML procedure order and do not invent conditional branch criteria.",
            "Micro-plan simulations remain substitutes until a specific release asset is licensed, reviewed, pinned, and hashed.",
            "Source requirements that depend on MITRE Emu, CALDERA facts, prior implants, or external infrastructure are replaced by labeled operational simulations.",
        ],
        "errors": [],
    }
    source_inventory = {
        "source": SOURCE_REPOSITORY,
        "source_commit": source_commit,
        "reference_repository": EMU_REPOSITORY,
        "reference_commit": emu_commit,
        "full_plan_directories": [
            str(path.relative_to(library_dir)).replace(os.sep, "/")
            for path in full_plan_dirs(library_dir)
        ],
        "procedures": inventory,
    }
    manifest = {"source_commit": source_commit, "plans": plan_manifest}

    if arguments.dry_run:
        print(json.dumps(report, indent=2))
        return 0

    staging = Path(tempfile.mkdtemp(prefix="ctid-output-", dir=str(arguments.out_dir.parent)))
    try:
        for package, relative in packages:
            write_json(staging / relative, package)
        write_json(staging / "conversion-report.json", report)
        write_json(staging / "source-inventory.json", source_inventory)
        write_json(staging / "plan-manifest.json", manifest)
        (staging / "README.md").write_text(readme_text(report), encoding="utf-8")
        shutil.copy2(library_dir / "LICENSE", staging / "LICENSE")
        for notice in sorted(library_dir.glob("*/NOTICE*")):
            if notice.is_file():
                destination = staging / "notices" / f"{notice.parent.name}-{notice.name}"
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(notice, destination)
        if arguments.out_dir.exists():
            shutil.rmtree(arguments.out_dir)
        os.replace(staging, arguments.out_dir)
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise

    if not arguments.no_update_catalog:
        catalog = json.loads(CATALOG_FILE.read_text(encoding="utf-8"))
        entries = [catalog_entry(package, relative) for package, relative in packages]
        write_json(CATALOG_FILE, update_catalog(catalog, entries))

    print(
        f"[CTID] Wrote {len(packages)} packages, "
        f"{sum(len(package['scripts']) for package, _ in packages)} scripts, "
        f"{sum(len(package['chains']) for package, _ in packages)} chains"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
