#!/usr/bin/env python3
"""cortado_risk.py — Risk classification for Cortado RTAs."""
from __future__ import annotations

import json
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent

# Tactic → default risk
TACTIC_RISK = {
    "initial-access":       "interact",
    "execution":            "modify",
    "persistence":          "modify",
    "privilege-escalation": "modify",
    "defense-evasion":      "modify",
    "credential-access":    "modify",
    "discovery":            "interact",
    "lateral-movement":     "modify",
    "collection":           "modify",
    "command-and-control":  "interact",
    "exfiltration":         "disrupt",
    "impact":               "disrupt",
    "resource-development": "interact",
    "reconnaissance":       "interact",
}

# ATT&CK technique→tactic mapping (subset covering common Cortado techniques)
# This is a compact local lookup — not a full MITRE download
TECHNIQUE_TACTIC: dict[str, list[str]] = {
    # Execution
    "T1059": ["execution"], "T1059.001": ["execution"], "T1059.003": ["execution"],
    "T1059.004": ["execution"], "T1059.005": ["execution"], "T1059.006": ["execution"],
    "T1059.007": ["execution"], "T1106": ["execution"], "T1129": ["execution"],
    "T1204": ["execution"], "T1204.001": ["execution"], "T1204.002": ["execution"],
    # Persistence
    "T1546": ["privilege-escalation", "persistence"],
    "T1547": ["persistence", "privilege-escalation"],
    "T1547.001": ["persistence", "privilege-escalation"],
    "T1547.004": ["persistence", "privilege-escalation"],
    "T1547.009": ["persistence", "privilege-escalation"],
    "T1543": ["persistence", "privilege-escalation"],
    "T1543.003": ["persistence", "privilege-escalation"],
    "T1574": ["persistence", "privilege-escalation", "defense-evasion"],
    "T1574.001": ["persistence", "privilege-escalation", "defense-evasion"],
    "T1574.002": ["persistence", "privilege-escalation", "defense-evasion"],
    "T1197": ["defense-evasion", "persistence"], "T1037": ["persistence", "privilege-escalation"],
    "T1037.001": ["persistence", "privilege-escalation"],
    "T1176": ["persistence"], "T1505": ["persistence"],
    "T1505.003": ["persistence"], "T1525": ["persistence"],
    # Privilege Escalation
    "T1134": ["privilege-escalation", "defense-evasion"],
    "T1134.001": ["privilege-escalation", "defense-evasion"],
    "T1548": ["privilege-escalation", "defense-evasion"],
    "T1548.002": ["privilege-escalation", "defense-evasion"],
    # Defense Evasion
    "T1027": ["defense-evasion"], "T1027.001": ["defense-evasion"],
    "T1036": ["defense-evasion"], "T1036.005": ["defense-evasion"],
    "T1055": ["defense-evasion", "privilege-escalation"],
    "T1055.001": ["defense-evasion", "privilege-escalation"],
    "T1070": ["defense-evasion"], "T1070.001": ["defense-evasion"],
    "T1140": ["defense-evasion"],
    "T1218": ["defense-evasion"], "T1218.005": ["defense-evasion"],
    "T1218.010": ["defense-evasion"], "T1218.011": ["defense-evasion"],
    "T1222": ["defense-evasion"], "T1484": ["defense-evasion", "privilege-escalation"],
    "T1548.001": ["defense-evasion", "privilege-escalation"],
    "T1553": ["defense-evasion"], "T1562": ["defense-evasion"],
    "T1562.001": ["defense-evasion"], "T1562.004": ["defense-evasion"],
    "T1564": ["defense-evasion"], "T1564.001": ["defense-evasion"],
    # Credential Access
    "T1003": ["credential-access"], "T1003.001": ["credential-access"],
    "T1539": ["credential-access"], "T1555": ["credential-access"],
    "T1552": ["credential-access"], "T1552.001": ["credential-access"],
    "T1558": ["credential-access"], "T1558.003": ["credential-access"],
    # Discovery
    "T1007": ["discovery"], "T1010": ["discovery"], "T1012": ["discovery"],
    "T1016": ["discovery"], "T1033": ["discovery"], "T1040": ["discovery"],
    "T1046": ["discovery"], "T1049": ["discovery"], "T1057": ["discovery"],
    "T1069": ["discovery"], "T1082": ["discovery"], "T1083": ["discovery"],
    "T1087": ["discovery"], "T1518": ["discovery"], "T1135": ["discovery"],
    # Lateral Movement
    "T1021": ["lateral-movement"], "T1021.001": ["lateral-movement"],
    "T1021.002": ["lateral-movement"], "T1021.006": ["lateral-movement"],
    "T1534": ["lateral-movement"],
    # Collection
    "T1005": ["collection"], "T1025": ["collection"], "T1039": ["collection"],
    "T1074": ["collection"], "T1113": ["collection"], "T1119": ["collection"],
    "T1123": ["collection"], "T1125": ["collection"],
    # Command and Control
    "T1071": ["command-and-control"], "T1071.001": ["command-and-control"],
    "T1071.004": ["command-and-control"], "T1095": ["command-and-control"],
    "T1105": ["command-and-control"], "T1132": ["command-and-control"],
    # Exfiltration
    "T1048": ["exfiltration"], "T1041": ["exfiltration"], "T1567": ["exfiltration"],
    # Impact
    "T1485": ["impact"], "T1486": ["impact"], "T1490": ["impact"],
    "T1491": ["impact"], "T1498": ["impact"], "T1531": ["impact"],
    "T1561": ["impact"],
    # Initial Access
    "T1190": ["initial-access"], "T1566": ["initial-access"],
    "T1078": ["initial-access", "persistence", "privilege-escalation", "defense-evasion"],
    "T1091": ["initial-access", "lateral-movement"],
    # Resource Development
    "T1583": ["resource-development"], "T1587": ["resource-development"],
}


def get_tactics(techniques: list[str]) -> list[str]:
    """Map technique IDs to ATT&CK tactics. Returns unique sorted list."""
    seen = set()
    result = []
    for t in techniques:
        t = t.upper()
        tactics = TECHNIQUE_TACTIC.get(t, TECHNIQUE_TACTIC.get(t.split(".")[0], []))
        for tac in tactics:
            if tac not in seen:
                seen.add(tac)
                result.append(tac)
    return sorted(result) if result else []


def get_primary_tactic(techniques: list[str]) -> str:
    """Get the first deterministic primary tactic."""
    tactics = get_tactics(techniques)
    return tactics[0] if tactics else "unmapped"


def get_risk(tactic: str, overrides: dict = None) -> str:
    if overrides:
        pass  # per-id overrides applied by caller
    return TACTIC_RISK.get(tactic, "interact")


def load_overrides(path: Path = None) -> dict:
    if path is None:
        path = TOOLS_DIR / "cortado_risk_overrides.json"
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    return data.get("overrides", {})
