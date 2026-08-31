#!/usr/bin/env python3
"""drozer_risk.py — Risk + Mobile ATT&CK mapping for drozer modules.

Risk follows Morgana's observe/interact/modify/disrupt model:
  - enumeration/query            -> observe
  - benign component interaction -> interact
  - state-changing operation     -> modify
  - availability/destructive     -> disrupt

Higher-risk source modules are NOT suppressed; they are published with the
appropriate risk badge and explicit prerequisites.
"""
from __future__ import annotations

import json
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent
OVERRIDES_FILE = TOOLS_DIR / "drozer_risk_overrides.json"


def load_overrides() -> dict:
    if OVERRIDES_FILE.exists():
        try:
            return json.loads(OVERRIDES_FILE.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


# Namespace-level risk baselines. Namespace = first path component (or fqmn prefix).
NAMESPACE_RISK = {
    "app": "observe",            # app.* enumeration is read-only
    "information": "observe",    # device info/datetime
    "scanner": "observe",        # discovery scanners (read-only probes)
    "auxiliary": "interact",     # helper actions
    "tools": "interact",         # file transfer/checksum
    "shell": "modify",           # command execution on device
    "exploit": "disrupt",        # exploits change device/app state
    "post": "interact",          # drozer-modules post-exploitation
    "kernelerror": "disrupt",    # kernel-level modules
    "meatballs1": "interact",
    "metall0id": "interact",
    "mwrlabs": "interact",
}

# Finer-grained overrides by fqmn prefix for destructive/state-changing modules.
FQMN_RISK = {
    # app component state changes
    "app.activity.start": "interact",
    "app.broadcast.send": "interact",
    "app.broadcast.sniff": "observe",
    "app.service.start": "interact",
    "app.service.stop": "interact",
    "app.service.send": "interact",
    "app.provider.insert": "modify",
    "app.provider.update": "modify",
    "app.provider.delete": "modify",
    "app.provider.call": "modify",
    "app.provider.read": "observe",
    "app.provider.query": "observe",
    "app.provider.download": "observe",
    "app.package.backup": "modify",
    # exploits are destructive
    "exploit.remote.dos": "disrupt",
    "exploit.jdwp.check": "observe",
    # shell
    "shell.exec": "modify",
    "shell.send": "modify",
    "shell.start": "interact",
    # drozer-modules post
    "post.perform.call": "interact",
    "post.perform.setclipboard": "interact",
    "post.capture.clipboard": "observe",
    "post.pivot.portforward": "modify",
    "post.sms": "modify",
    "post.microphone": "modify",
    "post.contacts": "observe",
    "post.location": "modify",
}

# Mobile ATT&CK technique mapping by fqmn prefix.
ATTCK_MAP = {
    "app.package.info": {"tcode": "T1418", "tactic": "Discovery"},
    "app.package.list": {"tcode": "T1418", "tactic": "Discovery"},
    "app.activity.info": {"tcode": "T1418", "tactic": "Discovery"},
    "app.service.info": {"tcode": "T1418", "tactic": "Discovery"},
    "app.broadcast.info": {"tcode": "T1418", "tactic": "Discovery"},
    "app.provider.info": {"tcode": "T1418", "tactic": "Discovery"},
    "app.provider.finduri": {"tcode": "T1418", "tactic": "Discovery"},
    "scanner.provider.finduris": {"tcode": "T1418", "tactic": "Discovery"},
    "scanner.provider.sqltables": {"tcode": "T1409", "tactic": "Collection"},
    "scanner.provider.injection": {"tcode": "T1409", "tactic": "Collection"},
    "app.provider.query": {"tcode": "T1430", "tactic": "Collection"},
    "app.provider.read": {"tcode": "T1430", "tactic": "Collection"},
    "post.contacts": {"tcode": "T1430", "tactic": "Collection"},
    "post.capture.clipboard": {"tcode": "T1414", "tactic": "Collection"},
    "app.activity.start": {"tcode": "T1417", "tactic": "Execution"},
    "app.service.start": {"tcode": "T1417", "tactic": "Execution"},
    "app.broadcast.send": {"tcode": "T1417", "tactic": "Execution"},
    "shell.exec": {"tcode": "T1407", "tactic": "Execution"},
    "app.provider.insert": {"tcode": "T1409", "tactic": "Collection"},
    "exploit": {"tcode": "T1404", "tactic": "Privilege Escalation"},
}


def get_risk(fqmn: str, name: str = "", overrides: dict = None) -> str:
    """Return the Morgana operational risk for a module."""
    if overrides:
        if fqmn in overrides:
            return overrides[fqmn]
        if name in overrides:
            return overrides[name]
    # exact fqmn match first
    for prefix, risk in FQMN_RISK.items():
        if fqmn.startswith(prefix):
            return risk
    namespace = fqmn.split(".")[0] if fqmn else ""
    return NAMESPACE_RISK.get(namespace, "interact")


def get_attck(fqmn: str) -> dict:
    """Return the Mobile ATT&CK mapping for a module (empty if unmapped)."""
    best = {}
    for prefix, mapping in ATTCK_MAP.items():
        if fqmn.startswith(prefix):
            best = mapping
            break
    return best
