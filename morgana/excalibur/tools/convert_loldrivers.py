#!/usr/bin/env python3
"""Convert LOLDrivers metadata into Morgana driver-security validation packs.

The converter never downloads, packages, loads, or exploits an upstream driver.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import tempfile
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any, Iterable

import yaml

TOOLS_DIR = Path(__file__).resolve().parent
EXCALIBUR_DIR = TOOLS_DIR.parent
DEFAULT_OUTPUT_DIR = EXCALIBUR_DIR / "loldrivers"
CATALOG_FILE = EXCALIBUR_DIR / "catalog.json"
OVERRIDES_FILE = TOOLS_DIR / "loldrivers_overrides.json"
SOURCE_REPOSITORY = "https://github.com/magicsword-io/LOLDrivers"
CATALOG_BASE_URL = "https://raw.githubusercontent.com/x3m-ai/Camelot/main/morgana/excalibur/loldrivers"
PROVIDER_ID = "loldrivers"
SCRIPT_PREFIX = "LOLDRIVERS - "
VALID_TCODE = re.compile(r"T\d{4}(?:\.\d{3})?")
VALID_HASH = {
    "SHA256": re.compile(r"^[a-fA-F0-9]{64}$"),
    "SHA1": re.compile(r"^[a-fA-F0-9]{40}$"),
    "MD5": re.compile(r"^[a-fA-F0-9]{32}$"),
}
VALID_READINESS = {
    "ready", "ready_with_parameters", "environment_prerequisite",
    "benign_driver_required", "manual_validation",
}
PROCEDURE_FAMILIES = (
    "hash_presence",
    "filename_presence",
    "loaded_driver_inventory",
    "driver_service_inventory",
    "event_code_integrity",
    "event_sysmon_driver_load",
    "event_service_control_manager",
    "event_defender",
    "blocklist_validation",
    "cve_exposure",
    "signer_publisher_hunt",
    "source_command_simulation",
)


def slug(value: str) -> str:
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", value.lower())).strip("-") or "other"


def compact(value: Any, maximum: int = 700) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    return text if len(text) <= maximum else f"{text[:maximum - 3].rstrip()}..."


def string_list(value: Any) -> list[str]:
    if value is None:
        return []
    values = value if isinstance(value, list) else [value]
    return [compact(item, 500) for item in values if compact(item, 500)]


def git_identity(directory: Path) -> tuple[str, str]:
    def run(*arguments: str) -> str:
        try:
            result = subprocess.run(
                ["git", "-C", str(directory), *arguments], check=True,
                capture_output=True, text=True, timeout=20,
            )
            return result.stdout.strip() or "unknown"
        except (OSError, subprocess.SubprocessError):
            return "unknown"
    return run("rev-parse", "HEAD"), run("show", "-s", "--format=%cs", "HEAD")


def ps_quote(value: Any) -> str:
    return "'" + str(value or "").replace("'", "''") + "'"


def normalize_category(value: Any) -> str:
    normalized = str(value or "unknown").strip().lower()
    return "vulnerable" if normalized == "vulnerable driver" else "malicious" if normalized == "malicious" else slug(normalized)


def extract_tcodes(value: Any) -> list[str]:
    return sorted(set(VALID_TCODE.findall(" ".join(string_list(value)).upper())))


def extract_cves(source: dict[str, Any]) -> list[str]:
    value = source.get("CVE", source.get("CVEs"))
    return sorted(set(re.findall(r"CVE-\d{4}-\d{4,}", " ".join(string_list(value)).upper())))


def normalize_hash(value: Any, algorithm: str) -> str:
    text = str(value or "").strip().lower()
    return text if VALID_HASH[algorithm].fullmatch(text) else ""


def nested_hash(sample: dict[str, Any], section: str, algorithm: str) -> str:
    value = sample.get(section)
    if isinstance(value, dict):
        return normalize_hash(value.get(algorithm), algorithm)
    legacy = sample.get(f"{section}{algorithm}")
    return normalize_hash(legacy, algorithm)


def signer_values(sample: dict[str, Any]) -> list[str]:
    values: set[str] = set()
    for key in ("Publisher", "Company", "CompanyName", "Signature"):
        raw = sample.get(key)
        for value in string_list(raw):
            if len(value) >= 3 and value.lower() not in {"none", "unknown", "unsigned"}:
                values.add(value)
    for signature in sample.get("Signatures") or []:
        if not isinstance(signature, dict):
            continue
        signer_info = signature.get("SignerInfo")
        for value in string_list(signer_info):
            if len(value) >= 3:
                values.add(value)
        for certificate in signature.get("Certificates") or []:
            if not isinstance(certificate, dict) or not certificate.get("IsCodeSigning"):
                continue
            subject = compact(certificate.get("Subject"), 500)
            if subject:
                values.add(subject)
    return sorted(values, key=lambda value: (value.lower(), value))


def sample_identity(sample: dict[str, Any], object_id: str, sample_index: int) -> tuple[str, str, str]:
    for algorithm in ("SHA256", "SHA1", "MD5"):
        value = normalize_hash(sample.get(algorithm), algorithm)
        if value:
            return f"{algorithm.lower()}:{value}", algorithm, value
    filename = compact(sample.get("Filename") or sample.get("OriginalFilename"), 260)
    if filename:
        fallback = hashlib.sha256(f"{filename.lower()}|{object_id}|{sample_index}".encode()).hexdigest()
        return f"filename:{fallback}", "FILENAME", filename
    fallback = hashlib.sha256(f"{object_id}|{sample_index}".encode()).hexdigest()
    return f"index:{fallback}", "INDEX", str(sample_index)


def compact_detection(value: Any) -> list[dict[str, str]]:
    result: list[dict[str, str]] = []
    for item in value or []:
        if not isinstance(item, dict):
            continue
        if "type" in item or "value" in item:
            result.append({"type": compact(item.get("type"), 100), "value": compact(item.get("value"), 1000)})
        else:
            for key, entry in item.items():
                result.append({"type": compact(key, 100), "value": compact(entry, 1000)})
    return result


@dataclass
class Association:
    object_id: str
    source_file: str
    sample_index: int
    category: str
    verified: bool
    tcodes: list[str]
    cves: list[str]
    tags: list[str]
    resources: list[str]
    detection: list[dict[str, str]]
    command: dict[str, str]


@dataclass
class DriverSample:
    identity: str
    identity_type: str
    identity_value: str
    filenames: set[str] = field(default_factory=set)
    md5: set[str] = field(default_factory=set)
    sha1: set[str] = field(default_factory=set)
    sha256: set[str] = field(default_factory=set)
    publishers: set[str] = field(default_factory=set)
    companies: set[str] = field(default_factory=set)
    products: set[str] = field(default_factory=set)
    descriptions: set[str] = field(default_factory=set)
    product_versions: set[str] = field(default_factory=set)
    file_versions: set[str] = field(default_factory=set)
    machine_types: set[str] = field(default_factory=set)
    original_filenames: set[str] = field(default_factory=set)
    imphashes: set[str] = field(default_factory=set)
    authentihashes: set[str] = field(default_factory=set)
    rich_header_hashes: set[str] = field(default_factory=set)
    internal_names: set[str] = field(default_factory=set)
    pdb_paths: set[str] = field(default_factory=set)
    signer_names: set[str] = field(default_factory=set)
    loads_despite_hvci: set[str] = field(default_factory=set)
    import_count: int = 0
    imported_function_count: int = 0
    exported_function_count: int = 0
    associations: list[Association] = field(default_factory=list)

    def add(self, sample: dict[str, Any], association: Association) -> None:
        scalar_sets = {
            "Filename": self.filenames,
            "MD5": self.md5,
            "SHA1": self.sha1,
            "SHA256": self.sha256,
            "Publisher": self.publishers,
            "Company": self.companies,
            "CompanyName": self.companies,
            "Product": self.products,
            "ProductName": self.products,
            "Description": self.descriptions,
            "FileDescription": self.descriptions,
            "ProductVersion": self.product_versions,
            "FileVersion": self.file_versions,
            "MachineType": self.machine_types,
            "Machine": self.machine_types,
            "OriginalFilename": self.original_filenames,
            "Imphash": self.imphashes,
            "InternalName": self.internal_names,
            "PDBPath": self.pdb_paths,
            "LoadsDespiteHVCI": self.loads_despite_hvci,
        }
        for key, destination in scalar_sets.items():
            value = compact(sample.get(key), 500)
            if value:
                destination.add(value)
        for value in signer_values(sample):
            self.signer_names.add(value)
        for algorithm in ("MD5", "SHA1", "SHA256"):
            value = nested_hash(sample, "Authentihash", algorithm)
            if value:
                self.authentihashes.add(value)
            value = nested_hash(sample, "RichPEHeaderHash", algorithm)
            if value:
                self.rich_header_hashes.add(value)
        self.import_count = max(self.import_count, len(sample.get("Imports") or []))
        self.imported_function_count = max(self.imported_function_count, len(sample.get("ImportedFunctions") or []))
        exported = sample.get("ExportedFunctions") or []
        self.exported_function_count = max(self.exported_function_count, len(exported) if isinstance(exported, list) else int(bool(exported)))
        self.associations.append(association)

    def categories(self) -> list[str]:
        return sorted({association.category for association in self.associations})

    def primary_category(self) -> str:
        categories = self.categories()
        return "malicious" if "malicious" in categories else categories[0] if categories else "unknown"

    def tcodes(self) -> list[str]:
        return sorted({tcode for association in self.associations for tcode in association.tcodes})

    def cves(self) -> list[str]:
        return sorted({cve for association in self.associations for cve in association.cves})

    def verified(self) -> bool:
        return any(association.verified for association in self.associations)

    def filename(self) -> str:
        return sorted(
            self.filenames or self.original_filenames,
            key=lambda value: (value.lower(), value),
        )[0] if self.filenames or self.original_filenames else ""

    def strongest_hash(self) -> tuple[str, str]:
        for algorithm, values in (("SHA256", self.sha256), ("SHA1", self.sha1), ("MD5", self.md5)):
            if values:
                return algorithm, sorted(values)[0].lower()
        return "", ""


@dataclass
class Procedure:
    source_id: str
    family: str
    category: str
    name: str
    command: str
    tcode: str
    source_tcodes: list[str]
    risk: str
    readiness: str
    required_tags: list[str]
    description: str
    source_metadata: dict[str, Any]
    cleanup_command: str | None = None

    def identity(self) -> str:
        normalized = re.sub(r"\s+", " ", self.command).strip().lower()
        return f"{self.source_id}|{self.family}|{normalized}|windows|powershell"


@dataclass
class ConversionState:
    yaml_files: int = 0
    yaml_objects: int = 0
    sample_associations: int = 0
    unique_samples: int = 0
    duplicate_sample_associations: int = 0
    candidate_variants: int = 0
    published: int = 0
    duplicates: int = 0
    skipped: int = 0
    unsupported: int = 0
    errors: int = 0
    procedure_counts: Counter[str] = field(default_factory=Counter)
    category_counts: Counter[str] = field(default_factory=Counter)
    readiness_counts: Counter[str] = field(default_factory=Counter)
    issues: list[dict[str, Any]] = field(default_factory=list)

    def reconciles(self) -> bool:
        return self.candidate_variants == self.published + self.duplicates + self.skipped + self.unsupported


TAG_DEFINITIONS = {
    "loldrivers_scan_roots": {
        "key": "loldrivers_scan_roots", "label": "Driver Scan Roots",
        "description": "Semicolon-separated authorized roots searched for driver files.",
        "default": r"C:\Windows\System32\drivers;C:\Windows\System32\DriverStore\FileRepository",
        "example": "", "sensitive": False, "required": True, "parameter_class": "local_path",
    },
    "loldrivers_event_hours": {
        "key": "loldrivers_event_hours", "label": "Event Lookback Hours",
        "description": "Historical event-log lookback window in hours.",
        "default": "168", "example": "", "sensitive": False, "required": True, "parameter_class": "value",
    },
    "loldrivers_benign_driver_path": {
        "key": "loldrivers_benign_driver_path", "label": "Benign Test-Signed Driver Path",
        "description": "Absolute path to an operator-approved benign/test-signed driver. LOLDrivers binaries are never supplied.",
        "default": "", "example": "", "sensitive": False, "required": True, "parameter_class": "local_path",
    },
    "loldrivers_benign_service_name": {
        "key": "loldrivers_benign_service_name", "label": "Benign Driver Service Name",
        "description": "Temporary service name used only for the approved benign driver simulation.",
        "default": "MorganaBenignDriverValidation", "example": "", "sensitive": False, "required": True, "parameter_class": "service",
    },
}


def primary_tcode(sample: DriverSample) -> str:
    return sample.tcodes()[0] if sample.tcodes() else "T1068"


def sample_metadata(sample: DriverSample) -> dict[str, Any]:
    algorithm, strongest_hash = sample.strongest_hash()
    detections = [item for association in sample.associations for item in association.detection]
    resources = {item for association in sample.associations for item in association.resources}
    return {
        "sample_identity": sample.identity,
        "identity_type": sample.identity_type,
        "identity_value": sample.identity_value,
        "sample_filename": sample.filename(),
        "hash_algorithm": algorithm,
        "strongest_hash": strongest_hash,
        "md5": sorted(sample.md5),
        "sha1": sorted(sample.sha1),
        "sha256": sorted(sample.sha256),
        "category": sample.primary_category(),
        "categories": sample.categories(),
        "verified": sample.verified(),
        "cves": sample.cves(),
        "publisher": sorted(sample.publishers),
        "company": sorted(sample.companies),
        "product": sorted(sample.products),
        "product_version": sorted(sample.product_versions),
        "file_version": sorted(sample.file_versions),
        "machine_type": sorted(sample.machine_types),
        "original_filename": sorted(sample.original_filenames),
        "source_object_ids": sorted({association.object_id for association in sample.associations}),
        "source_files": sorted({association.source_file for association in sample.associations}),
        "source_detection_types": sorted({item.get("type", "") for item in detections if item.get("type")}),
        "source_detection_reference_count": len({(item.get("type", ""), item.get("value", "")) for item in detections}),
        "source_resource_count": len(resources),
    }


def roots_prefix() -> str:
    return (
        "$roots = '#{loldrivers_scan_roots}'.Split(';',[System.StringSplitOptions]::RemoveEmptyEntries); "
        "$roots = $roots | ForEach-Object { $_.Trim() } | Where-Object { $_ -and (Test-Path $_) }; "
    )


def candidates_command(filename: str) -> str:
    filter_value = filename or "*.sys"
    return (
        roots_prefix()
        + f"$candidates = @($roots | ForEach-Object {{ Get-ChildItem -LiteralPath $_ -Filter {ps_quote(filter_value)} -File -Recurse -ErrorAction SilentlyContinue }}); "
    )


def result_command(label: str, collection: str = "$matches") -> str:
    return f"if (@({collection}).Count) {{ Write-Output {ps_quote(label + '=PRESENT')}; @({collection}) | ConvertTo-Json -Depth 5 -Compress }} else {{ Write-Output {ps_quote(label + '=NOT_PRESENT')} }}"


def procedure_name(family: str, sample: DriverSample, suffix: str = "") -> str:
    label = family.replace("_", " ").title()
    driver = sample.filename() or sample.identity_value[:24]
    digest = hashlib.sha1(f"{sample.identity}|{family}|{suffix}".encode()).hexdigest()[:8]
    return f"LOLDRIVERS - {primary_tcode(sample)} - {label} - {driver} [{digest}]"


def make_sample_procedures(sample: DriverSample) -> list[Procedure]:
    procedures: list[Procedure] = []
    category = sample.primary_category()
    tcode = primary_tcode(sample)
    tcodes = sample.tcodes()
    filename = sample.filename()
    algorithm, expected_hash = sample.strongest_hash()
    metadata = sample_metadata(sample)
    base_description = f"LOLDrivers {category} sample validation for {filename or sample.identity_value}. No driver binary is provided, loaded, or exploited."

    def add(family: str, command: str, readiness: str = "ready", tags: list[str] | None = None, risk: str = "observe", extra: dict[str, Any] | None = None) -> None:
        procedures.append(Procedure(
            source_id=f"loldrivers:{sample.identity}:{family}",
            family=family,
            category=category,
            name=procedure_name(family, sample),
            command=command,
            tcode=tcode,
            source_tcodes=tcodes,
            risk=risk,
            readiness=readiness,
            required_tags=tags or [],
            description=f"{base_description} Procedure: {family.replace('_', ' ')}.",
            source_metadata={**metadata, **(extra or {})},
        ))

    if expected_hash:
        command = candidates_command(filename)
        command += f"$expected = {ps_quote(expected_hash)}; $matches = @($candidates | ForEach-Object {{ try {{ $actual = (Get-FileHash -LiteralPath $_.FullName -Algorithm {algorithm}).Hash.ToLowerInvariant(); if ($actual -eq $expected) {{ [pscustomobject]@{{Path=$_.FullName;Algorithm={ps_quote(algorithm)};Hash=$actual}} }} }} catch {{}} }}); "
        command += result_command("HASH_PRESENCE")
        add("hash_presence", command, "ready_with_parameters", ["loldrivers_scan_roots"])

    if filename:
        command = candidates_command(filename) + "$matches = $candidates | Select-Object FullName,Length,CreationTimeUtc,LastWriteTimeUtc; " + result_command("FILENAME_PRESENCE")
        add("filename_presence", command, "ready_with_parameters", ["loldrivers_scan_roots"])

        escaped = ps_quote(filename)
        service_filter = f"$needle = {escaped}; $stem = [IO.Path]::GetFileNameWithoutExtension($needle); $drivers = @(Get-CimInstance Win32_SystemDriver -ErrorAction SilentlyContinue | Where-Object {{ $_.PathName -match [regex]::Escape($needle) -or $_.Name -eq $stem }}); "
        add("loaded_driver_inventory", service_filter + "$matches = $drivers | Where-Object { $_.State -eq 'Running' } | Select-Object Name,DisplayName,State,StartMode,PathName; " + result_command("LOADED_DRIVER"))
        add("driver_service_inventory", service_filter + "$matches = $drivers | Select-Object Name,DisplayName,State,StartMode,ServiceType,PathName; " + result_command("DRIVER_SERVICE"))

    hunt_terms = [value for value in (filename, expected_hash) if value]
    terms_literal = "@(" + ",".join(ps_quote(value) for value in hunt_terms) + ")"
    event_sources = {
        "event_code_integrity": ("Microsoft-Windows-CodeIntegrity/Operational", "CODE_INTEGRITY_EVENT"),
        "event_sysmon_driver_load": ("Microsoft-Windows-Sysmon/Operational", "SYSMON_DRIVER_LOAD_EVENT"),
        "event_service_control_manager": ("System", "SERVICE_CONTROL_MANAGER_EVENT"),
        "event_defender": ("Microsoft-Windows-Windows Defender/Operational", "DEFENDER_EVENT"),
    }
    for family, (log_name, result_label) in event_sources.items():
        command = (
            "$hours = [Math]::Max(1,[int]'#{loldrivers_event_hours}'); "
            f"$terms = {terms_literal}; $events = @(); try {{ $events = @(Get-WinEvent -FilterHashtable @{{LogName={ps_quote(log_name)};StartTime=(Get-Date).AddHours(-$hours)}} -ErrorAction Stop | Where-Object {{ $message=$_.Message; $terms | Where-Object {{ $message -like ('*'+$_+'*') }} }} | Select-Object -First 200 TimeCreated,Id,ProviderName,LevelDisplayName,Message) }} catch {{ Write-Output ('LOG_UNAVAILABLE=' + $_.Exception.Message) }}; "
            + result_command(result_label, "$events")
        )
        add(family, command, "ready_with_parameters", ["loldrivers_event_hours"], extra={"event_log": log_name})

    command = (
        "$state = [ordered]@{}; "
        "$state['MicrosoftVulnerableDriverBlocklistEnable'] = (Get-ItemProperty -Path 'HKLM:\\SYSTEM\\CurrentControlSet\\Control\\CI\\Config' -Name VulnerableDriverBlocklistEnable -ErrorAction SilentlyContinue).VulnerableDriverBlocklistEnable; "
        "$state['HVCIEnabled'] = (Get-ItemProperty -Path 'HKLM:\\SYSTEM\\CurrentControlSet\\Control\\DeviceGuard\\Scenarios\\HypervisorEnforcedCodeIntegrity' -Name Enabled -ErrorAction SilentlyContinue).Enabled; "
        '$state[\'WDACPolicies\'] = @(Get-ChildItem "$env:windir\\System32\\CodeIntegrity\\CiPolicies\\Active" -File -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Name); '
        f"$state['SampleHash'] = {ps_quote(expected_hash)}; $state['SampleFilename'] = {ps_quote(filename)}; "
        "if ($state.MicrosoftVulnerableDriverBlocklistEnable -eq 1 -or $state.HVCIEnabled -eq 1 -or $state.WDACPolicies.Count) { Write-Output 'BLOCKLIST_POLICY=PRESENT' } else { Write-Output 'BLOCKLIST_POLICY=UNKNOWN' }; $state | ConvertTo-Json -Depth 4 -Compress"
    )
    add("blocklist_validation", command, extra={"coverage_claim": "Policy presence only; sample-specific blocking is not inferred without explicit policy evidence."})

    cves = sample.cves()
    if cves:
        command = candidates_command(filename)
        if expected_hash:
            command += f"$expected={ps_quote(expected_hash)}; $evidence=@($candidates | ForEach-Object {{ try {{ if ((Get-FileHash -LiteralPath $_.FullName -Algorithm {algorithm}).Hash.ToLowerInvariant() -eq $expected) {{ $_.FullName }} }} catch {{}} }}); "
        else:
            command += "$evidence=@($candidates | Select-Object -ExpandProperty FullName); "
        command += f"$cves=@({','.join(ps_quote(cve) for cve in cves)}); if ($evidence.Count) {{ Write-Output 'CVE_EXPOSURE=PRESENT'; [pscustomobject]@{{CVEs=$cves;Evidence=$evidence;Product={ps_quote('; '.join(sorted(sample.products)))};Versions={ps_quote('; '.join(sorted(sample.file_versions | sample.product_versions)))}}} | ConvertTo-Json -Depth 5 -Compress }} elseif ($candidates.Count -eq 0) {{ Write-Output 'CVE_EXPOSURE=NOT_PRESENT' }} else {{ Write-Output 'CVE_EXPOSURE=UNKNOWN' }}"
        add("cve_exposure", command, "ready_with_parameters", ["loldrivers_scan_roots"])

    return procedures


def make_signer_procedure(signer: str, samples: list[DriverSample]) -> Procedure:
    digest = hashlib.sha256(signer.lower().encode()).hexdigest()
    categories = sorted({sample.primary_category() for sample in samples})
    tcodes = sorted({tcode for sample in samples for tcode in sample.tcodes()})
    command = (
        roots_prefix()
        + f"$signer={ps_quote(signer)}; $matches=@($roots | ForEach-Object {{ Get-ChildItem -LiteralPath $_ -Filter '*.sys' -File -Recurse -ErrorAction SilentlyContinue }} | ForEach-Object {{ try {{ $signature=Get-AuthenticodeSignature -LiteralPath $_.FullName -ErrorAction Stop; if ($signature.SignerCertificate.Subject -like ('*'+$signer+'*')) {{ [pscustomobject]@{{Path=$_.FullName;Status=$signature.Status;Subject=$signature.SignerCertificate.Subject;Thumbprint=$signature.SignerCertificate.Thumbprint}} }} }} catch {{}} }}); "
        + result_command("SIGNER_PUBLISHER_HUNT")
    )
    return Procedure(
        source_id=f"loldrivers:signer:{digest}", family="signer_publisher_hunt", category="hunting",
        name=f"LOLDRIVERS - T1068 - Signer Publisher Hunt - {compact(signer, 80)} [{digest[:8]}]",
        command=command, tcode=tcodes[0] if tcodes else "T1068", source_tcodes=tcodes,
        risk="observe", readiness="ready_with_parameters", required_tags=["loldrivers_scan_roots"],
        description=f"Hunt authorized driver roots for Authenticode signer or publisher evidence matching {compact(signer, 200)}.",
        source_metadata={
            "signer_publisher": signer, "sample_count": len(samples), "driver_categories": categories,
            "sample_identities": [sample.identity for sample in samples[:100]],
            "sample_identity_count": len(samples),
        },
    )


def make_command_simulation(category: str, sources: list[dict[str, Any]]) -> Procedure | None:
    available = [
        source for source in sources
        if isinstance(source.get("Commands"), dict)
        and compact(source["Commands"].get("Command"), 4000)
    ]
    if not available:
        return None
    tcodes = sorted({tcode for source in available for tcode in extract_tcodes(source.get("MitreID"))})
    tcode = tcodes[0] if tcodes else "T1068"
    digest = hashlib.sha1(category.encode()).hexdigest()[:8]
    command = (
        "$driverPath='#{loldrivers_benign_driver_path}'; $serviceName='#{loldrivers_benign_service_name}'; "
        "if (-not (Test-Path -LiteralPath $driverPath -PathType Leaf)) { throw 'Operator-approved benign driver path does not exist.' }; "
        "$signature=Get-AuthenticodeSignature -LiteralPath $driverPath; if ($signature.Status -ne 'Valid') { throw ('Benign driver signature is not valid: '+$signature.Status) }; "
        "$created=$false; try { & sc.exe create $serviceName binPath= $driverPath type= kernel start= demand | Out-String | Write-Output; if ($LASTEXITCODE -ne 0) { throw 'Driver service creation failed.' }; $created=$true; & sc.exe start $serviceName | Out-String | Write-Output; Write-Output ('BENIGN_DRIVER_LOAD_EXIT='+$LASTEXITCODE) } finally { if ($created) { & sc.exe stop $serviceName | Out-Null; & sc.exe delete $serviceName | Out-Null } }"
    )
    return Procedure(
        source_id=f"loldrivers:{category}:source_command_simulation",
        family="source_command_simulation", category=category,
        name=f"LOLDRIVERS - {tcode} - Benign Driver Telemetry Simulation - {category.title()} [{digest}]",
        command=command, tcode=tcode, source_tcodes=tcodes,
        risk="modify", readiness="benign_driver_required",
        required_tags=["loldrivers_benign_driver_path", "loldrivers_benign_service_name"],
        description="Reproduce kernel-driver service creation, start-attempt, and cleanup telemetry using only an operator-supplied valid benign/test-signed driver.",
        source_metadata={
            "driver_category": category,
            "source_object_count": len(available),
            "source_object_ids": sorted(compact(source.get("Id"), 100) for source in available),
            "source_files": sorted(source.get("_source_file", "") for source in available),
            "verified_source_objects": sum(str(source.get("Verified") or "").upper() == "TRUE" for source in available),
            "cves": sorted({cve for source in available for cve in extract_cves(source)}),
            "source_tcodes": tcodes,
            "source_command_examples": [compact(source["Commands"].get("Command"), 1000) for source in available[:20]],
            "payload_policy": "The source driver is metadata-only and is never acquired, packaged, or loaded.",
        },
    )


def parse_source(source_dir: Path, state: ConversionState) -> tuple[list[DriverSample], list[dict[str, Any]], list[dict[str, Any]]]:
    samples_by_identity: dict[str, DriverSample] = {}
    objects: list[dict[str, Any]] = []
    inventory: list[dict[str, Any]] = []
    paths = sorted([*source_dir.joinpath("yaml").glob("*.yaml"), *source_dir.joinpath("yaml").glob("*.yml")])
    state.yaml_files = len(paths)
    for path in paths:
        source_file = str(path.relative_to(source_dir)).replace("\\", "/")
        try:
            loaded = yaml.safe_load(path.read_text(encoding="utf-8-sig", errors="replace"))
        except (OSError, yaml.YAMLError) as exc:
            state.errors += 1
            state.issues.append({"source_file": source_file, "status": "error", "reason": str(exc)})
            continue
        source_objects = loaded if isinstance(loaded, list) else [loaded]
        for source in source_objects:
            if not isinstance(source, dict):
                state.errors += 1
                state.issues.append({"source_file": source_file, "status": "error", "reason": "root is not a mapping"})
                continue
            state.yaml_objects += 1
            object_id = compact(source.get("Id") or path.stem, 100)
            category = normalize_category(source.get("Category"))
            verified = str(source.get("Verified") or "").strip().upper() == "TRUE"
            tcodes = extract_tcodes(source.get("MitreID"))
            cves = extract_cves(source)
            command_raw = source.get("Commands") if isinstance(source.get("Commands"), dict) else {}
            command_metadata = {key.lower(): compact(value, 4000 if key == "Command" else 1000) for key, value in command_raw.items()}
            detection = compact_detection(source.get("Detection"))
            source_copy = dict(source)
            source_copy["_source_file"] = source_file
            objects.append(source_copy)
            entries = source.get("KnownVulnerableSamples") or []
            if isinstance(entries, dict):
                entries = [entries]
            for sample_index, sample in enumerate(entries):
                state.sample_associations += 1
                if not isinstance(sample, dict):
                    state.errors += 1
                    inventory.append({"source_file": source_file, "object_id": object_id, "sample_index": sample_index, "status": "error", "reason": "sample is not a mapping"})
                    continue
                identity, identity_type, identity_value = sample_identity(sample, object_id, sample_index)
                driver = samples_by_identity.setdefault(identity, DriverSample(identity, identity_type, identity_value))
                association = Association(
                    object_id=object_id, source_file=source_file, sample_index=sample_index,
                    category=category, verified=verified, tcodes=tcodes, cves=cves,
                    tags=string_list(source.get("Tags")), resources=string_list(source.get("Resources")),
                    detection=detection, command=command_metadata,
                )
                driver.add(sample, association)
                inventory.append({
                    "sample_identity": identity, "identity_type": identity_type,
                    "object_id": object_id, "source_file": source_file, "sample_index": sample_index,
                    "category": category, "verified": verified, "tcodes": tcodes, "cves": cves,
                    "filename": compact(sample.get("Filename"), 260),
                    "md5": normalize_hash(sample.get("MD5"), "MD5"),
                    "sha1": normalize_hash(sample.get("SHA1"), "SHA1"),
                    "sha256": normalize_hash(sample.get("SHA256"), "SHA256"),
                    "publisher": compact(sample.get("Publisher"), 500),
                    "company": compact(sample.get("Company") or sample.get("CompanyName"), 500),
                    "product": compact(sample.get("Product") or sample.get("ProductName"), 500),
                    "product_version": compact(sample.get("ProductVersion"), 200),
                    "file_version": compact(sample.get("FileVersion"), 200),
                    "machine_type": compact(sample.get("MachineType") or sample.get("Machine"), 100),
                    "original_filename": compact(sample.get("OriginalFilename"), 260),
                    "imphash": compact(sample.get("Imphash"), 100),
                    "authentihash": sample.get("Authentihash") if isinstance(sample.get("Authentihash"), dict) else {},
                    "rich_pe_header_hash": sample.get("RichPEHeaderHash") if isinstance(sample.get("RichPEHeaderHash"), dict) else {},
                    "pdb_path": compact(sample.get("PDBPath"), 500),
                    "signer_names": signer_values(sample),
                    "loads_despite_hvci": compact(sample.get("LoadsDespiteHVCI"), 20),
                    "import_count": len(sample.get("Imports") or []),
                    "imported_function_count": len(sample.get("ImportedFunctions") or []),
                    "exported_function_count": len(sample.get("ExportedFunctions") or []) if isinstance(sample.get("ExportedFunctions"), list) else int(bool(sample.get("ExportedFunctions"))),
                    "detection": detection, "resources": string_list(source.get("Resources")),
                    "source_command": command_metadata,
                    "status": "accounted",
                })
    samples = sorted(samples_by_identity.values(), key=lambda item: item.identity)
    state.unique_samples = len(samples)
    state.duplicate_sample_associations = state.sample_associations - state.unique_samples
    return samples, objects, inventory


def generate_procedures(samples: list[DriverSample], objects: list[dict[str, Any]], state: ConversionState, overrides: dict[str, Any]) -> list[Procedure]:
    candidates: list[Procedure] = []
    for sample in samples:
        candidates.extend(make_sample_procedures(sample))

    signer_samples: dict[str, dict[str, DriverSample]] = defaultdict(dict)
    signer_display: dict[str, str] = {}
    for sample in samples:
        signers = sorted(
            sample.signer_names | sample.publishers | sample.companies,
            key=lambda value: (value.lower(), value),
        )
        for signer in signers:
            if len(signer) >= 3:
                key = signer.lower()
                signer_display.setdefault(key, signer)
                signer_samples[key][sample.identity] = sample
    for key in sorted(signer_samples):
        associated_samples = [signer_samples[key][identity] for identity in sorted(signer_samples[key])]
        candidates.append(make_signer_procedure(signer_display[key], associated_samples))

    disabled_objects = set(overrides.get("disabled_source_command_objects", []))
    eligible_objects = [source for source in objects if compact(source.get("Id"), 100) not in disabled_objects]
    state.skipped += len(objects) - len(eligible_objects)
    by_category: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for source in eligible_objects:
        by_category[normalize_category(source.get("Category"))].append(source)
    for category, category_objects in sorted(by_category.items()):
        procedure = make_command_simulation(category, category_objects)
        if procedure:
            candidates.append(procedure)

    state.candidate_variants = len(candidates) + state.skipped
    unique: dict[str, Procedure] = {}
    for procedure in candidates:
        identity = procedure.identity()
        if identity in unique:
            state.duplicates += 1
            continue
        unique[identity] = procedure
    procedures = sorted(unique.values(), key=lambda item: (item.category, item.family, item.source_id))
    state.published = len(procedures)
    for procedure in procedures:
        state.procedure_counts[procedure.family] += 1
        state.category_counts[procedure.category] += 1
        state.readiness_counts[procedure.readiness] += 1
    return procedures


def validate_procedure(procedure: Procedure) -> list[str]:
    errors: list[str] = []
    if not procedure.name.startswith(SCRIPT_PREFIX): errors.append("invalid prefix")
    if not procedure.command.strip(): errors.append("blank command")
    if not VALID_TCODE.fullmatch(procedure.tcode): errors.append("invalid TCode")
    if procedure.risk not in {"observe", "interact", "modify", "disrupt"}: errors.append("invalid risk")
    if procedure.readiness not in VALID_READINESS: errors.append("invalid readiness")
    placeholders = set(re.findall(r"#\{([^{}]+)\}", procedure.command + "\n" + (procedure.cleanup_command or "")))
    if placeholders != set(procedure.required_tags): errors.append("placeholder mismatch")
    if not set(procedure.required_tags).issubset(TAG_DEFINITIONS): errors.append("undefined tag")
    if not procedure.source_metadata: errors.append("missing metadata")
    return errors


def script_from(procedure: Procedure) -> dict[str, Any]:
    return {
        "id": procedure.source_id,
        "name": procedure.name,
        "description": procedure.description,
        "tactic": "Privilege Escalation" if procedure.tcode == "T1068" else "Driver Security",
        "tcode": procedure.tcode,
        "executor": "powershell",
        "platform": "windows",
        "command": procedure.command,
        "cleanup_command": procedure.cleanup_command,
        "required_tags": procedure.required_tags,
        "required_assets": [],
        "operational_risk": procedure.risk,
        "source_metadata": {
            **procedure.source_metadata,
            "provider": PROVIDER_ID,
            "procedure_family": procedure.family,
            "readiness": procedure.readiness,
            "source_tcodes": procedure.source_tcodes,
            "payload_policy": "Metadata only; no known vulnerable or malicious driver is acquired, distributed, loaded, or exploited.",
        },
    }


def catalog_category(category: str, family: str) -> str:
    if family == "blocklist_validation": return "drivers/blocklist"
    if family.startswith("event_") or family == "signer_publisher_hunt": return "drivers/hunting"
    return "drivers/malicious" if category == "malicious" else "drivers/vulnerable"


def output_group(category: str, family: str) -> str:
    return "detection" if family == "signer_publisher_hunt" else "malicious" if category == "malicious" else "vulnerable"


def build_packs(procedures: list[Procedure], source_commit: str, max_per_pack: int) -> list[tuple[dict[str, Any], str]]:
    grouped: dict[tuple[str, str], list[Procedure]] = defaultdict(list)
    for procedure in procedures:
        grouped[(procedure.category, procedure.family)].append(procedure)
    result: list[tuple[dict[str, Any], str]] = []
    for (category, family), items in sorted(grouped.items()):
        items.sort(key=lambda item: item.source_id)
        for chunk_index, offset in enumerate(range(0, len(items), max_per_pack), start=1):
            chunk = items[offset:offset + max_per_pack]
            total_chunks = (len(items) + max_per_pack - 1) // max_per_pack
            suffix = f"-{chunk_index:02d}" if total_chunks > 1 else ""
            category_slug = slug(category)
            family_slug = slug(family)
            package_id = f"loldrivers-{category_slug}-{family_slug}{suffix}-v1"
            scripts = [script_from(item) for item in chunk]
            tcodes = sorted({item.tcode for item in chunk})
            sample_ids = {
                item.source_metadata.get("sample_identity") for item in chunk
                if item.source_metadata.get("sample_identity")
            }
            cves = sorted({cve for item in chunk for cve in item.source_metadata.get("cves", [])})
            detection_sources = sorted({
                value for item in chunk
                for value in ([item.source_metadata.get("event_log")] + item.source_metadata.get("source_detection_types", []))
                if value
            })
            tags = sorted({tag for item in chunk for tag in item.required_tags})
            procedure_label = family.replace("_", " ").title()
            category_label = category.replace("_", " ").title()
            risks = sorted({item.risk for item in chunk}, key=("observe", "interact", "modify", "disrupt").index)
            package = {
                "package_id": package_id,
                "package_name": f"LOLDrivers - {category_label} - {procedure_label}{' Part ' + str(chunk_index) if total_chunks > 1 else ''}",
                "version": "1.0.0",
                "summary": f"{len(chunk)} source-derived LOLDrivers {procedure_label.lower()} procedures for Windows driver threat validation.",
                "description": "Metadata-only Windows driver validation content derived from LOLDrivers. It inventories files, hashes, loaded drivers, services, policies, and historical telemetry without distributing dangerous samples.",
                "purpose": "Validate vulnerable/malicious driver exposure, hunting, Code Integrity, WDAC, Defender, Sysmon, and kernel-service telemetry in an authorized environment.",
                "capabilities": [
                    f"Contains {len(chunk)} {procedure_label.lower()} procedures covering {len(sample_ids)} unique driver sample identities.",
                    f"Driver category: {category_label}; CVE coverage: {len(cves)}; ATT&CK techniques: {len(tcodes)}.",
                    "Preserves LOLDrivers hashes, filenames, publishers, products, verification state, source associations, and detection references.",
                ],
                "use_cases": [
                    "Assess endpoints for known vulnerable or malicious driver evidence without loading source samples.",
                    "Validate driver inventory, service, Code Integrity, Sysmon, Defender, WDAC, and blocklist visibility.",
                    "Import only the procedure family and driver category needed for a focused Purple Team exercise.",
                ],
                "prerequisites": [
                    "Morgana Agent on an explicitly authorized Windows endpoint.",
                    "Administrative event-log or driver inventory access where required by the selected procedure.",
                    "Operator-approved scan roots and lookback window; benign simulation additionally requires a valid test-signed driver.",
                ],
                "safety_notes": [
                    "No known vulnerable or malicious driver binary is included, downloaded, or loaded by this package.",
                    "Presence and policy procedures report evidence; they do not claim exploitability or sample-specific blocking without proof.",
                    "Benign simulation Scripts accept only an operator-supplied valid signed driver and clean up the temporary service.",
                ],
                "author": "LOLDrivers / X3M.AI conversion",
                "created": str(date.today()),
                "script_prefix": SCRIPT_PREFIX,
                "provider": PROVIDER_ID,
                "source": PROVIDER_ID,
                "source_repository": SOURCE_REPOSITORY,
                "source_commit": source_commit,
                "source_license": "Apache-2.0",
                "documentation_url": SOURCE_REPOSITORY,
                "mitre_domain": "enterprise-attack",
                "mitre_tactic": "Windows Driver Security",
                "mitre_tcodes": tcodes,
                "platform": ["windows"],
                "risk_badges": risks,
                "category": catalog_category(category, family),
                "driver_category": category,
                "procedure_types": [family],
                "unique_driver_samples": len(sample_ids),
                "cve_count": len(cves),
                "cves": cves,
                "detection_sources": detection_sources,
                "readiness_counts": dict(Counter(item.readiness for item in chunk)),
                "tag_categories": [{
                    "category_id": "loldrivers_runtime",
                    "label": "LOLDrivers Validation Parameters",
                    "description": "Authorized paths, event lookback, and optional benign-driver simulation parameters.",
                    "scope": "local",
                    "tags": [TAG_DEFINITIONS[key] for key in tags],
                }] if tags else [],
                "assets": [],
                "scripts": scripts,
                "chains": [],
            }
            relative = f"{output_group(category, family)}/{package_id}.json"
            result.append((package, relative))
    return result


def catalog_entry(package: dict[str, Any], relative: str) -> dict[str, Any]:
    fields = (
        "package_id", "package_name", "version", "summary", "description", "purpose",
        "capabilities", "use_cases", "prerequisites", "safety_notes", "provider", "category",
        "platform", "mitre_tactic", "mitre_tcodes", "source", "source_commit", "source_license",
        "documentation_url", "risk_badges", "driver_category", "procedure_types",
        "unique_driver_samples", "cve_count", "cves", "detection_sources", "readiness_counts",
    )
    return {key: package[key] for key in fields} | {
        "script_count": len(package["scripts"]), "chain_count": 0, "asset_count": 0,
        "status": "community", "author": package["author"],
        "url": f"{CATALOG_BASE_URL}/{relative}",
    }


def update_catalog(entries: list[dict[str, Any]]) -> None:
    catalog = json.loads(CATALOG_FILE.read_text(encoding="utf-8"))
    catalog["packs"] = [entry for entry in catalog.get("packs", []) if entry.get("provider") != PROVIDER_ID] + entries
    catalog["catalog_version"] = "1.8.0"
    catalog["updated"] = str(date.today())
    catalog["providers"] = [entry for entry in catalog.get("providers", []) if entry.get("id") != PROVIDER_ID] + [{
        "id": PROVIDER_ID, "name": "LOLDrivers", "type": "upstream",
        "repository": SOURCE_REPOSITORY, "domain": "enterprise-attack",
    }]
    category_ids = {"drivers/vulnerable", "drivers/malicious", "drivers/hunting", "drivers/blocklist"}
    catalog["categories"] = [entry for entry in catalog.get("categories", []) if entry.get("id") not in category_ids] + [
        {"id": "drivers/vulnerable", "label": "Vulnerable Drivers", "group": "Windows Driver Security", "order": 500, "provider": PROVIDER_ID},
        {"id": "drivers/malicious", "label": "Malicious Drivers", "group": "Windows Driver Security", "order": 510, "provider": PROVIDER_ID},
        {"id": "drivers/hunting", "label": "Driver Hunting", "group": "Windows Driver Security", "order": 520, "provider": PROVIDER_ID},
        {"id": "drivers/blocklist", "label": "WDAC / Blocklist", "group": "Windows Driver Security", "order": 530, "provider": PROVIDER_ID},
    ]
    write_json(CATALOG_FILE, catalog)


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def readme_text(report: dict[str, Any]) -> str:
    return f"""# LOLDrivers Windows Driver Security Packs

Metadata-only Morgana procedures derived from the complete LOLDrivers structured corpus. No known vulnerable or malicious driver binary is downloaded, packaged, loaded, or exploited.

## Corpus

- Source commit: `{report['source_commit']}`
- YAML objects: {report['yaml_objects']}
- Sample associations: {report['sample_associations']}
- Unique sample identities: {report['unique_samples']}
- Published procedures: {report['published']}
- Packages: {report['packs']}
- Validation: {report['validation']}

## Procedure Families

{chr(10).join(f"- `{family}`: {count}" for family, count in report['procedure_counts'].items())}

Search roots and event lookback values are operator-configurable Morgana Tags. Benign telemetry simulations require an operator-supplied valid test-signed driver and never use LOLDrivers sample binaries.

Run `morgana/excalibur/tools/update-loldrivers-packs.ps1` for deterministic source updates, full static validation, and optional representative imports.
"""


def main() -> int:
    parser = argparse.ArgumentParser(description="Convert LOLDrivers metadata into Morgana packages")
    parser.add_argument("--source-dir", required=True, type=Path)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--category")
    parser.add_argument("--procedure-family", choices=PROCEDURE_FAMILIES)
    parser.add_argument("--verified-only", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--report-only", action="store_true")
    parser.add_argument("--no-update-catalog", action="store_true")
    parser.add_argument("--max-per-pack", type=int, default=400)
    parser.add_argument("--verbose", action="store_true")
    arguments = parser.parse_args()
    if not 50 <= arguments.max_per_pack <= 1000:
        raise ValueError("--max-per-pack must be between 50 and 1000")

    source_dir = arguments.source_dir.resolve()
    source_commit, source_commit_date = git_identity(source_dir)
    state = ConversionState()
    samples, objects, inventory = parse_source(source_dir, state)
    if arguments.verified_only:
        samples = [sample for sample in samples if sample.verified()]
        verified_ids = {association.object_id for sample in samples for association in sample.associations}
        objects = [source for source in objects if compact(source.get("Id"), 100) in verified_ids]
    if arguments.category:
        requested = normalize_category(arguments.category)
        samples = [sample for sample in samples if requested in sample.categories()]
        objects = [source for source in objects if normalize_category(source.get("Category")) == requested]
    overrides = json.loads(OVERRIDES_FILE.read_text(encoding="utf-8")) if OVERRIDES_FILE.is_file() else {}
    procedures = generate_procedures(samples, objects, state, overrides)
    if arguments.procedure_family:
        excluded = [procedure for procedure in procedures if procedure.family != arguments.procedure_family]
        state.skipped += len(excluded)
        state.published -= len(excluded)
        procedures = [procedure for procedure in procedures if procedure.family == arguments.procedure_family]

    validation_errors = [
        {"source_id": procedure.source_id, "errors": errors}
        for procedure in procedures if (errors := validate_procedure(procedure))
    ]
    if validation_errors:
        raise ValueError(f"{len(validation_errors)} generated procedures failed validation: {validation_errors[:3]}")
    if not state.reconciles():
        raise ValueError(f"procedure reconciliation failed: {state}")
    if state.sample_associations != len(inventory):
        raise ValueError("sample inventory reconciliation failed")

    packs = build_packs(procedures, source_commit, arguments.max_per_pack)
    unique_filenames = {filename.lower() for sample in samples for filename in sample.filenames if filename}
    unique_publishers = {value.lower() for sample in samples for value in sample.publishers | sample.companies | sample.signer_names if value}
    unique_cves = {cve for sample in samples for cve in sample.cves()}
    unique_tcodes = {tcode for sample in samples for tcode in sample.tcodes()}
    report = {
        "source_repository": SOURCE_REPOSITORY,
        "source_commit": source_commit,
        "source_commit_date": source_commit_date,
        "source_license": "Apache-2.0",
        "yaml_files": state.yaml_files,
        "yaml_objects": state.yaml_objects,
        "sample_associations": state.sample_associations,
        "unique_samples": state.unique_samples,
        "duplicate_sample_associations": state.duplicate_sample_associations,
        "verified_associations": sum(row["verified"] for row in inventory),
        "unverified_associations": sum(not row["verified"] for row in inventory),
        "verified_unique_samples": sum(sample.verified() for sample in samples),
        "unverified_unique_samples": sum(not sample.verified() for sample in samples),
        "category_associations": dict(Counter(row["category"] for row in inventory)),
        "category_unique_samples": dict(Counter(sample.primary_category() for sample in samples)),
        "unique_sha256": len({value for sample in samples for value in sample.sha256}),
        "unique_filenames": len(unique_filenames),
        "unique_publishers_signers": len(unique_publishers),
        "unique_cves": len(unique_cves),
        "unique_tcodes": len(unique_tcodes),
        "candidate_variants": state.candidate_variants,
        "published": state.published,
        "duplicates": state.duplicates,
        "skipped": state.skipped,
        "unsupported": state.unsupported,
        "errors": state.errors,
        "packs": len(packs),
        "procedure_counts": dict(sorted(state.procedure_counts.items())),
        "category_counts": dict(sorted(state.category_counts.items())),
        "readiness_counts": dict(sorted(state.readiness_counts.items())),
        "risk_counts": dict(sorted(Counter(procedure.risk for procedure in procedures).items())),
        "largest_pack_scripts": max((len(package["scripts"]) for package, _ in packs), default=0),
        "average_scripts_per_pack": round(len(procedures) / len(packs), 2) if packs else 0,
        "issues": state.issues,
        "sample_inventory_reconciled": state.sample_associations == len(inventory),
        "procedure_reconciled": state.reconciles(),
        "validation": "PASS",
    }
    if arguments.dry_run or arguments.report_only:
        print(json.dumps(report, indent=2))
        return 0

    staging = Path(tempfile.mkdtemp(prefix="loldrivers-output-", dir=str(arguments.out_dir.parent)))
    try:
        for package, relative in packs:
            write_json(staging / relative, package)
        write_json(staging / "conversion-report.json", report)
        write_json(staging / "source-inventory.json", inventory)
        (staging / "README.md").write_text(readme_text(report), encoding="utf-8")
        (staging / "LICENSE-NOTICE.md").write_text(
            "# License Notice\n\nLOLDrivers repository metadata is licensed under Apache-2.0. Generated packages preserve source repository, commit, object, and sample attribution. Referenced third-party drivers are not included and may have separate licenses.\n",
            encoding="utf-8",
        )
        if arguments.out_dir.exists():
            shutil.rmtree(arguments.out_dir)
        staging.replace(arguments.out_dir)
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    if not arguments.no_update_catalog:
        update_catalog([catalog_entry(package, relative) for package, relative in packs])
    print(f"[LOLDRIVERS] Wrote {len(packs)} packs and {len(procedures)} scripts; validation PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())