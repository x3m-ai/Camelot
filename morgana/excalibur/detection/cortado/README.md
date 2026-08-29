# Elastic Cortado — Red Team Automations (RTA)

**Provider:** Elastic Cortado  
**Source:** [elastic/cortado](https://github.com/elastic/cortado)  
**Release:** `dev-release-0.1.0+f1dd8bc1` | **Commit:** `f1dd8bc`  
**License:** Elastic License 2.0  
**Scripts:** 698 | **Packages:** 13 | **Chains:** 0  

---

## What is Cortado?

Elastic Cortado is the centralized repository for Elastic **Red Team Automations (RTAs)**.
Its purpose is to generate controlled suspicious behaviors that validate:
- Elastic Endpoint behavioral detection rules
- Elastic Security SIEM detection rules
- MITRE ATT&CK technique coverage

Each RTA is a small Python script designed to trigger specific Elastic security detections.
Cortado includes expected rule mappings — Endpoint and SIEM rule names/IDs — that tell you
exactly which detection rule should fire for each behavior.

---

## RTA types

| Type | Scripts | Description |
|---|---|---|
| **CodeRTA** | 618 | Executable Python behaviors. Run via the official Cortado wheel. |
| **HashRTA** | 80 | Sample-backed records. Reference external binary sample hashes. Not directly executable. |

---

## Packages

| Package | ATT&CK Tactic | Scripts |
|---|---|---|
| `cortado-defense-evasion-v1` | Defense Evasion | 210 |
| `cortado-unmapped-v1` | Unmapped / Detection-specific | 124 |
| `cortado-persistence-v1` | Persistence | 61 |
| `cortado-command-and-control-v1` | Command and Control | 59 |
| `cortado-execution-v1` | Execution | 55 |
| `cortado-credential-access-v1` | Credential Access | 41 |
| `cortado-initial-access-v1` | Initial Access | 25 |
| `cortado-lateral-movement-v1` | Lateral Movement | 16 |
| `cortado-discovery-v1` | Discovery | 13 |
| `cortado-impact-v1` | Impact | 11 |
| `cortado-exfiltration-v1` | Exfiltration | 2 |
| `cortado-collection-v1` | Collection | 1 |
| `cortado-sample-backed-v1` | Sample-backed RTAs | 80 |

---

## Prerequisites

- **Python 3.12+** on the Morgana Agent
- Elastic Cortado wheel extracted to Agent runtime path (configurable via `cortado_runtime_path` Tag)
- Authorized isolated test endpoint (Windows, Linux, or macOS)

**No manual `pip install cortado` required.** The wheel is managed as a Morgana verified asset.

---

## Execution model

```
Morgana Script (CodeRTA)
    ↓
morgana_cortado_runner.py
    ↓
Extracted Cortado wheel (elastic_cortado_wheel asset)
    ↓
Official RTA code_func()
    ↓
Endpoint / SIEM telemetry
    ↓
MORGANA_RESULT_METADATA (expected rule metadata for Detection Fabric)
```

---

## Sample-backed RTAs

HashRTA records are preserved as manual Scripts. They reference external sample hashes but
**cannot be automatically executed from Cortado**. The `cortado-sample-backed-v1` package
contains these records with their Elastic rule mappings and ATT&CK metadata intact.

**Referenced samples may be malicious. Never acquire samples from untrusted sources.**

---

## Detection metadata

Every Script carries expected Elastic detection metadata:
- `expected_endpoint_rules` — Elastic Endpoint behavioral rule name + UUID
- `expected_siem_rules` — Elastic SIEM rule name + UUID

These can be used by Detection Fabric to correlate test execution with expected alerts.

---

See [LICENSE-NOTICE.md](LICENSE-NOTICE.md) for attribution and license information.
