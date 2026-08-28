"""Structured operator guidance shared by Excalibur content converters."""

from __future__ import annotations


TACTIC_PURPOSES = {
    "initial access": "initial foothold controls and telemetry produced by common entry techniques",
    "execution": "command and code execution controls across supported operating systems",
    "persistence": "mechanisms that retain access across logons, restarts, or configuration changes",
    "privilege escalation": "controls that detect or prevent attempts to obtain higher privileges",
    "defense evasion": "controls and telemetry for attempts to avoid, impair, or bypass defenses",
    "credential access": "credential theft, extraction, interception, and abuse detections",
    "discovery": "host, account, process, service, network, and environment discovery telemetry",
    "lateral movement": "remote access and movement controls between authorized systems",
    "collection": "data staging and collection behaviors before exfiltration",
    "command and control": "network and application-layer command-and-control detections",
    "exfiltration": "controls that identify or prevent data transfer from the environment",
    "impact": "high-consequence behaviors that can disrupt availability or integrity",
    "reconnaissance": "external information-gathering and active scanning detections",
    "inhibit response function": "behaviors intended to prevent operators or safeguards from responding",
    "impair process control": "behaviors that alter, degrade, or interfere with industrial process control",
}


def _purpose(tactic_name: str) -> str:
    return TACTIC_PURPOSES.get(
        tactic_name.lower(),
        f"controls and telemetry associated with the {tactic_name} tactic",
    )


def tactic_purpose(tactic_name: str) -> str:
    """Return a concise operator-facing purpose for a MITRE tactic."""
    return _purpose(tactic_name)


def art_guidance(tactic_name: str, script_count: int, technique_count: int) -> dict:
    purpose = _purpose(tactic_name)
    return {
        "capabilities": [
            f"Provides {script_count} focused Red Canary Atomic Red Team tests covering {technique_count} MITRE ATT&CK techniques for {tactic_name}.",
            f"Exercises {purpose} using small, independently selectable atomic tests.",
            "Includes one-step Chains for individual atomics and a full-tactic convenience Chain when multiple tests are available.",
        ],
        "use_cases": [
            f"Validate endpoint, identity, network, and SIEM detections mapped to ATT&CK {tactic_name}.",
            "Verify that preventive controls block expected behavior and that telemetry reaches defensive tooling.",
            "Select individual atomics to close specific ATT&CK coverage gaps during an authorized Purple Team exercise.",
        ],
        "safety_notes": [
            "Operational impact varies by atomic test; inspect each command, input, prerequisite, and cleanup action before execution.",
            "Full-tactic convenience Chains run many independent tests sequentially and are not a validated adversary campaign.",
            "Run only on explicitly authorized targets and verify cleanup results after each test.",
        ],
    }


def stockpile_guidance(tactic_name: str, script_count: int, technique_count: int) -> dict:
    purpose = _purpose(tactic_name)
    return {
        "capabilities": [
            f"Provides {script_count} MITRE CALDERA Stockpile command-based abilities covering {technique_count} ATT&CK techniques for {tactic_name}.",
            f"Exercises {purpose} through Morgana-native Scripts without requiring a CALDERA server.",
            "Includes individual one-step Chains and a full-tactic convenience Chain for orchestration and coverage exploration.",
        ],
        "use_cases": [
            f"Build authorized {tactic_name} test sequences from MITRE-maintained command behaviors.",
            "Validate ATT&CK-aligned telemetry, prevention, and detection coverage across Windows, Linux, or macOS where supported.",
            "Compare focused Stockpile behaviors with Atomic Red Team or custom Morgana content for the same technique.",
        ],
        "safety_notes": [
            "Review every Script and supply required CALDERA facts as Morgana Tag values before execution.",
            "Payload-dependent, build-only, unsupported, and unsafe runtime-dependent variants are excluded from these packs.",
            "Full-tactic convenience Chains are collections of abilities, not authentic MITRE CALDERA adversary profiles or validated operation sequences.",
        ],
    }


def ot_guidance(protocol_label: str, tactic_name: str, risks: list[str], asset_count: int) -> dict:
    purpose = _purpose(tactic_name)
    highest_risk = risks[-1] if risks else "unknown"
    return {
        "capabilities": [
            f"Provides official MITRE CALDERA for OT {protocol_label} behaviors for ATT&CK for ICS {tactic_name}.",
            f"Exercises {purpose} against an operator-supplied {protocol_label} simulator, lab, or approved target.",
            f"Uses verified package assets and protocol-specific parameters where required ({asset_count} unique assets in this pack).",
        ],
        "use_cases": [
            f"Validate {protocol_label} monitoring, industrial telemetry, and ATT&CK for ICS detection coverage.",
            f"Run focused {tactic_name} exercises in an isolated OT lab or cyber range.",
            "Assess whether defensive controls distinguish read-only protocol activity from process-changing behavior.",
        ],
        "safety_notes": [
            f"Highest operational risk in this pack: {highest_risk.upper()}. Review the risk badge on every Script before execution.",
            "No target values are supplied; configure only an explicitly authorized lab, simulation, or approved production exercise.",
            "Verified assets are downloaded only when a Script is explicitly executed; importing the pack never contacts an OT target.",
        ],
    }