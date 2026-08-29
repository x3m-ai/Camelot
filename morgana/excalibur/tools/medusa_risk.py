#!/usr/bin/env python3
"""medusa_risk.py — Risk and ATT&CK mapping for MEDUSA modules."""
from __future__ import annotations

import json
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent

# Category-level risk baseline
CATEGORY_RISK = {
    "helpers":             "observe",
    "fragments":           "observe",
    "base64":              "observe",
    "compression":         "observe",
    "db_queries":          "interact",
    "bluetooth":           "interact",
    "sockets":             "interact",
    "intents":             "interact",
    "content_providers":   "interact",
    "ipc":                 "interact",
    "firebase":            "interact",
    "webviews":            "interact",
    "file_system":         "interact",
    "runtime":             "interact",
    "services":            "interact",
    "playstore":           "interact",
    "risky_api_calls":     "interact",
    "system_server":       "interact",
    "memory_dump":         "modify",
    "http_communications": "modify",
    "encryption":          "modify",
    "code_loading":        "modify",
    "root_detection":      "modify",
    "JNICalls":            "modify",
    "react_native":        "modify",
    "cordova":             "modify",
    "exploits":            "modify",
    "backdoor":            "disrupt",
    "sms_fraud":           "disrupt",
    "spyware":             "disrupt",
    "clickers":            "disrupt",
    # iOS
    "ios":                 "modify",
    "snippets":            "interact",
    "uncategorized":       "interact",
}

# ATT&CK Mobile technique mapping by category
CATEGORY_ATTCK = {
    "http_communications": {"tcode": "T1521", "tactic": "Command and Control"},
    "root_detection":      {"tcode": "T1629", "tactic": "Defense Evasion"},
    "memory_dump":         {"tcode": "T1617", "tactic": "Collection"},
    "encryption":          {"tcode": "T1521", "tactic": "Collection"},
    "spyware":             {"tcode": "T1636", "tactic": "Collection"},
    "db_queries":          {"tcode": "T1636", "tactic": "Collection"},
    "file_system":         {"tcode": "T1636", "tactic": "Collection"},
    "sms_fraud":           {"tcode": "T1582", "tactic": "Impact"},
    "backdoor":            {"tcode": "T1577", "tactic": "Execution"},
    "code_loading":        {"tcode": "T1577", "tactic": "Execution"},
    "exploits":            {"tcode": "T1404", "tactic": "Privilege Escalation"},
    "ipc":                 {"tcode": "T1516", "tactic": "Defense Evasion"},
    "ios":                 {"tcode": "T1629", "tactic": "Defense Evasion"},
}


def get_risk(category: str, module_name: str = "", overrides: dict = None) -> str:
    if overrides:
        key = f"{category}/{module_name}"
        if key in overrides:
            return overrides[key]
        if module_name in overrides:
            return overrides[module_name]
    return CATEGORY_RISK.get(category, "interact")


def get_attck(category: str) -> dict:
    return CATEGORY_ATTCK.get(category, {})


def load_overrides(path: Path = None) -> dict:
    if path is None:
        path = TOOLS_DIR / "medusa_risk_overrides.json"
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    return data.get("overrides", {})
