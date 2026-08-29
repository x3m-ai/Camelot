#!/usr/bin/env python3
"""lolrmm_source.py — Parse and normalize LOLRMM YAML corpus."""
from __future__ import annotations

import hashlib
import re
import subprocess
from pathlib import Path
from typing import Optional

try:
    import yaml
except ImportError:
    raise ImportError("pyyaml required: pip install pyyaml")

LOLRMM_COMMIT  = "fa859607fb05af91878ac8d44a59655f44d286fe"
LOLRMM_LICENSE = "Apache-2.0"
LOLRMM_REPO    = "magicsword-io/LOLRMM"

OS_NORM = {
    "windows": "windows", "Windows": "windows",
    "linux": "linux", "Linux": "linux",
    "mac": "macos", "Mac": "macos", "MacOS": "macos", "macOS": "macos", "macos": "macos",
}


def _norm_os(raw: str) -> str:
    return OS_NORM.get(raw.strip(), raw.strip().lower())


def _slug(name: str) -> str:
    s = name.lower()
    s = re.sub(r'[^a-z0-9]+', '-', s)
    return s.strip('-')


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _coerce_list(v) -> list:
    if v is None: return []
    if isinstance(v, list): return v
    if isinstance(v, str) and v.strip(): return [v]
    return []


def parse_yaml(path: Path) -> Optional[dict]:
    try:
        raw = path.read_text(encoding="utf-8", errors="replace")
        data = yaml.safe_load(raw)
        if not data or not isinstance(data, dict):
            return None
        return data
    except Exception as exc:
        return {"_parse_error": str(exc), "_path": str(path)}


def extract_pe_metadata(details: dict) -> list[dict]:
    pe_raw = details.get("PEMetadata", {})
    if not pe_raw:
        return []
    if isinstance(pe_raw, dict):
        items = [pe_raw]
    elif isinstance(pe_raw, list):
        items = pe_raw
    else:
        return []
    result = []
    for item in items:
        if not isinstance(item, dict): continue
        entry = {
            "filename": (item.get("Filename") or "").strip(),
            "original_filename": (item.get("OriginalFileName") or "").strip(),
            "description": (item.get("Description") or "").strip(),
            "company": (item.get("Company") or "").strip(),
            "product": (item.get("Product") or "").strip(),
        }
        if any(entry.values()):
            result.append(entry)
    return result


def extract_artifacts(raw: dict) -> dict:
    a = raw.get("Artifacts", {}) or {}
    disk      = _coerce_list(a.get("Disk"))
    evtlog    = _coerce_list(a.get("EventLog"))
    registry  = _coerce_list(a.get("Registry"))
    network   = _coerce_list(a.get("Network"))

    files = []
    filenames = []
    reg_keys = []
    evts = []
    domains = []
    ports = []
    unknown_classes = {}

    for item in disk:
        if not isinstance(item, dict): continue
        f = (item.get("File") or item.get("Path") or "").strip()
        if f: files.append({"path": f, "description": item.get("Description",""), "os": item.get("OS","")})

    for item in evtlog:
        if not isinstance(item, dict): continue
        evts.append({
            "event_id": item.get("EventID",""),
            "provider": item.get("ProviderName",""),
            "log": item.get("LogFile",""),
            "description": item.get("Description",""),
            "service_name": item.get("ServiceName",""),
            "image_path": item.get("ImagePath",""),
            "command_line": item.get("CommandLine",""),
        })

    for item in registry:
        if not isinstance(item, dict): continue
        key = (item.get("Regkey") or item.get("Key") or item.get("Path") or "").strip()
        if key: reg_keys.append({"key": key, "description": item.get("Description","")})

    for item in network:
        if not isinstance(item, dict): continue
        for d in _coerce_list(item.get("Domains")):
            if d: domains.append(d)
        for p in _coerce_list(item.get("Ports")):
            if p: ports.append(str(p))

    for cls in a:
        if cls not in ("Disk", "EventLog", "Registry", "Network"):
            unknown_classes[cls] = a[cls]

    return {
        "files": files,
        "filenames": filenames,
        "registry": reg_keys,
        "event_logs": evts,
        "domains": domains,
        "ports": ports,
        "unknown_classes": unknown_classes,
    }


def extract_code_signing(raw: dict) -> list[dict]:
    cs = raw.get("CodeSigning", {}) or {}
    if not cs: return []
    return [{
        "search_names": _coerce_list(cs.get("search_names")),
        "company_names": _coerce_list(cs.get("company_names")),
        "signer_names": _coerce_list(cs.get("signer_names")),
        "cert_count": len(_coerce_list(cs.get("certificates"))),
    }]


def extract_file_hashes(raw: dict) -> list[dict]:
    fh = raw.get("FileHashes", {}) or {}
    if not fh: return []
    entries = []
    for hash_type, items in fh.items():
        for item in _coerce_list(items):
            if isinstance(item, dict):
                entries.append({
                    "hash_type": hash_type,
                    "filename": item.get("file_name", ""),
                    "sha256": item.get("sha256", ""),
                    "sha1": item.get("sha1", ""),
                })
    return entries


def extract_detections(raw: dict) -> list[dict]:
    detections = []
    for item in _coerce_list(raw.get("Detections")):
        if not isinstance(item, dict): continue
        detections.append({
            "sigma_url": item.get("Sigma",""),
            "description": item.get("Description","") or item.get("Name",""),
        })
    return detections


def normalize_tool(path: Path, source_commit: str) -> dict:
    data = parse_yaml(path)
    if data is None:
        return {"_error": "empty_file", "_path": str(path)}
    if "_parse_error" in data:
        return data

    details  = data.get("Details", {}) or {}
    installs = _coerce_list(details.get("InstallationPaths"))
    pe_meta  = extract_pe_metadata(details)
    raw_os   = _coerce_list(details.get("SupportedOS"))
    platforms_norm = sorted(set(_norm_os(o) for o in raw_os if o))

    artifacts  = extract_artifacts(data)
    code_sign  = extract_code_signing(data)
    file_hashes = extract_file_hashes(data)
    detections = extract_detections(data)

    # Installation paths → add to files/filenames
    for ip in installs:
        if ip.strip():
            artifacts["filenames"].append(ip.strip())

    # PE metadata filenames → filenames list
    for pe in pe_meta:
        if pe.get("filename"): artifacts["filenames"].append(pe["filename"])
        if pe.get("original_filename"): artifacts["filenames"].append(pe["original_filename"])

    artifacts["filenames"] = list(dict.fromkeys(f for f in artifacts["filenames"] if f))

    name = (data.get("Name") or path.stem).strip()
    # Use filename stem as the stable ID base (not the display name) to ensure uniqueness
    slug = _slug(path.stem)

    # Probe capability: can we do something useful?
    has_files     = bool(artifacts["files"])
    has_filenames = bool(artifacts["filenames"])
    has_registry  = bool(artifacts["registry"])
    has_evtlog    = bool(artifacts["event_logs"])
    has_domains   = bool(artifacts["domains"])
    has_hashes    = bool(file_hashes)
    probe_capable = has_files or has_filenames or has_registry or has_evtlog or has_hashes

    return {
        "tool_id": f"lolrmm:{slug}",
        "source_file": path.name,
        "source_sha": _sha256(path),
        "source_commit": source_commit,
        "name": name,
        "slug": slug,
        "category": (data.get("Category") or "RMM").strip(),
        "description": (data.get("Description") or "").strip(),
        "author": (data.get("Author") or "").strip(),
        "created": str(data.get("Created") or ""),
        "last_modified": str(data.get("LastModified") or ""),
        "website": (details.get("Website") or "").strip(),
        "privileges": (details.get("Privileges") or "").strip(),
        "free": details.get("Free"),
        "verification": str(details.get("Verification") or "").strip(),
        "capabilities": _coerce_list(details.get("Capabilities")),
        "vulnerabilities": _coerce_list(details.get("Vulnerabilities")),
        "platforms_raw": raw_os,
        "platforms": platforms_norm,
        "pe_metadata": pe_meta,
        "installation_paths": installs,
        "artifacts": artifacts,
        "code_signing": code_sign,
        "file_hashes": file_hashes,
        "detections": detections,
        "references": _coerce_list(data.get("References")),
        "acknowledgements": [{"person": a.get("Person",""), "handle": a.get("Handle","")}
                             for a in _coerce_list(data.get("Acknowledgement")) if isinstance(a, dict)],
        "probe_capable": probe_capable,
        "has_files": has_files,
        "has_filenames": has_filenames,
        "has_registry": has_registry,
        "has_evtlog": has_evtlog,
        "has_domains": has_domains,
        "has_file_hashes": has_hashes,
        "unknown_artifact_classes": list((artifacts.get("unknown_classes") or {}).keys()),
    }


def enumerate_tools(source_dir: Path, source_commit: str) -> tuple[list[dict], list[dict]]:
    yaml_dir = source_dir / "yaml"
    if not yaml_dir.exists():
        raise FileNotFoundError(f"yaml/ directory not found in {source_dir}")
    files = sorted(yaml_dir.glob("*.yaml")) + sorted(yaml_dir.glob("*.yml"))
    files = sorted(set(files))
    valid, errors = [], []
    for f in files:
        tool = normalize_tool(f, source_commit)
        if "_error" in tool or "_parse_error" in tool:
            errors.append(tool)
        elif tool.get("name"):
            valid.append(tool)
        else:
            errors.append({**tool, "_error": "missing_name"})
    return valid, errors


def get_source_commit(source_dir: Path) -> str:
    try:
        r = subprocess.run(["git", "-C", str(source_dir), "rev-parse", "HEAD"],
                          capture_output=True, text=True, check=True)
        return r.stdout.strip()
    except Exception:
        return LOLRMM_COMMIT
