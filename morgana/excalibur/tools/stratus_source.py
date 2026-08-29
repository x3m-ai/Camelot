#!/usr/bin/env python3
"""
stratus_source.py — Parse Stratus Red Team Go source to extract technique metadata.

Reads main.go files from the attacktechniques directory and extracts AttackTechnique
struct fields using targeted regex (no full Go AST required).
"""
from __future__ import annotations

import re
import subprocess
from pathlib import Path
from typing import Optional

# Platform slug → canonical name + target environments
PLATFORM_META = {
    "aws":      {"name": "AWS",           "target_environments": ["cloud", "aws"],                  "short": "AWS"},
    "azure":    {"name": "Azure",         "target_environments": ["cloud", "azure"],                 "short": "AZURE"},
    "entra-id": {"name": "Entra ID",      "target_environments": ["cloud", "azure", "entra-id"],    "short": "ENTRA"},
    "gcp":      {"name": "GCP",           "target_environments": ["cloud", "gcp"],                   "short": "GCP"},
    "k8s":      {"name": "Kubernetes",    "target_environments": ["cloud-native", "kubernetes"],     "short": "KUBERNETES"},
    "eks":      {"name": "Amazon EKS",    "target_environments": ["cloud", "aws", "eks", "kubernetes"], "short": "EKS"},
}

# Tactic-level risk mapping
TACTIC_RISK = {
    "persistence":          "modify",
    "privilege-escalation": "modify",
    "defense-evasion":      "modify",
    "credential-access":    "modify",
    "initial-access":       "interact",
    "execution":            "modify",
    "discovery":            "interact",
    "lateral-movement":     "modify",
    "exfiltration":         "disrupt",
    "impact":               "disrupt",
    "collection":           "modify",
}

# Human-friendly tactic labels (from directory slug)
TACTIC_LABELS = {
    "persistence":          "Persistence",
    "privilege-escalation": "Privilege Escalation",
    "defense-evasion":      "Defense Evasion",
    "credential-access":    "Credential Access",
    "initial-access":       "Initial Access",
    "execution":            "Execution",
    "discovery":            "Discovery",
    "lateral-movement":     "Lateral Movement",
    "exfiltration":         "Exfiltration",
    "impact":               "Impact",
    "collection":           "Collection",
}


def _extract_go_string(content: str, field: str) -> str:
    """Extract a backtick or double-quoted string value from a Go struct literal."""
    # Backtick multiline
    m = re.search(rf'{field}:\s*`(.*?)`', content, re.DOTALL)
    if m:
        return m.group(1).strip()
    # Double-quoted single line
    m = re.search(rf'{field}:\s*"([^"]*)"', content)
    if m:
        return m.group(1).strip()
    return ""


def _extract_technique_id(content: str) -> str:
    m = re.search(r'ID:\s*"([^"]+)"', content)
    return m.group(1) if m else ""


def _extract_friendly_name(content: str) -> str:
    m = re.search(r'FriendlyName:\s*"([^"]+)"', content)
    return m.group(1) if m else ""


def _extract_tactics(content: str) -> list[str]:
    """Extract MitreAttackTactics list as human-readable strings."""
    m = re.search(r'MitreAttackTactics:\s*\[\]mitreattack\.Tactic\{([^}]+)\}', content, re.DOTALL)
    if not m:
        return []
    body = m.group(1)
    raw = re.findall(r'mitreattack\.(\w+)', body)
    # Convert CamelCase to Title Case  e.g. PrivilegeEscalation → Privilege Escalation
    result = []
    for r in raw:
        # Insert space before each capital that follows a lowercase
        label = re.sub(r'([a-z])([A-Z])', r'\1 \2', r)
        result.append(label)
    return result


def _extract_is_idempotent(content: str) -> bool:
    m = re.search(r'IsIdempotent:\s*(true|false)', content)
    return m.group(1) == "true" if m else False


def _has_terraform(path: Path) -> bool:
    return (path.parent / "main.tf").exists()


def _has_revert(content: str) -> bool:
    return "Revert:" in content and "revert," in content or "revert," in content


def _clean_html(text: str) -> str:
    """Strip HTML tags from detection/description text."""
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def parse_technique(go_file: Path, platform_slug: str, tactic_slug: str) -> Optional[dict]:
    """Parse a single main.go file and return a technique metadata dict."""
    try:
        content = go_file.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return None

    tech_id = _extract_technique_id(content)
    if not tech_id:
        return None

    friendly_name = _extract_friendly_name(content)
    description_raw = _extract_go_string(content, "Description")
    detection_raw = _extract_go_string(content, "Detection")
    tactics_raw = _extract_tactics(content)
    is_idempotent = _extract_is_idempotent(content)
    has_tf = _has_terraform(go_file)
    has_revert = _has_revert(content)

    plat_meta = PLATFORM_META.get(platform_slug, {"name": platform_slug, "target_environments": ["cloud"], "short": platform_slug.upper()})
    tactic_label = TACTIC_LABELS.get(tactic_slug, tactic_slug.replace("-", " ").title())

    # Use parsed tactics if available, else fall back to directory tactic
    if not tactics_raw:
        tactics_raw = [tactic_label]

    # Risk = highest tactic risk
    risk = "interact"
    for t in [tactic_slug] + [t.lower().replace(" ", "-") for t in tactics_raw]:
        r = TACTIC_RISK.get(t, "interact")
        if {"interact": 0, "modify": 1, "disrupt": 2}.get(r, 0) > {"interact": 0, "modify": 1, "disrupt": 2}.get(risk, 0):
            risk = r

    return {
        "technique_id": tech_id,
        "friendly_name": friendly_name,
        "platform": platform_slug,
        "platform_name": plat_meta["name"],
        "tactic_slug": tactic_slug,
        "tactic_label": tactic_label,
        "mitre_tactics": tactics_raw,
        "description": _clean_html(description_raw),
        "detection": _clean_html(detection_raw),
        "is_idempotent": is_idempotent,
        "has_terraform": has_tf,
        "has_revert": has_revert,
        "risk": risk,
        "target_environments": plat_meta["target_environments"],
        "source_path": str(go_file),
        "script_id": f"stratus:{tech_id}",
        "script_name": f"STRATUS - {plat_meta['short']} - {friendly_name}",
        "package_key": f"stratus-{platform_slug}-{tactic_slug}-v1",
    }


def enumerate_techniques(source_dir: Path) -> list[dict]:
    """Walk the attacktechniques directory and return all parsed techniques."""
    at_dir = source_dir / "v2" / "internal" / "attacktechniques"
    if not at_dir.exists():
        raise FileNotFoundError(f"attacktechniques directory not found: {at_dir}")

    techniques = []
    for platform_dir in sorted(at_dir.iterdir()):
        if not platform_dir.is_dir():
            continue
        platform_slug = platform_dir.name
        for tactic_dir in sorted(platform_dir.iterdir()):
            if not tactic_dir.is_dir():
                continue
            tactic_slug = tactic_dir.name
            for technique_dir in sorted(tactic_dir.iterdir()):
                if not technique_dir.is_dir():
                    continue
                go_file = technique_dir / "main.go"
                if not go_file.exists():
                    continue
                tech = parse_technique(go_file, platform_slug, tactic_slug)
                if tech:
                    techniques.append(tech)
    return techniques


def get_source_commit(source_dir: Path) -> str:
    try:
        r = subprocess.run(["git", "-C", str(source_dir), "rev-parse", "HEAD"],
                          capture_output=True, text=True, check=True)
        return r.stdout.strip()
    except Exception:
        return "UNKNOWN"
