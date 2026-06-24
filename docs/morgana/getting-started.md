# Getting Started with Morgana

> **Morgana** is X3M.AI's advanced Red Team platform for adversary emulation, penetration testing, and Purple Team operations.  
> Built from the ground up — not a fork, not a wrapper. A first-class offensive security product.

---

## Access

Morgana is a **controlled-distribution** platform. Due to its advanced offensive capabilities and integrated AI features, access is managed directly by X3M.AI.

If you are interested in using Morgana for Purple Team exercises or Red Team operations in conjunction with Merlino, contact us:

**[Contact X3M.AI to access Morgana](https://x3m.ai/contact/)**

---

## What is Morgana?

Morgana is a professional-grade Red Team platform that delivers:

- **Adversary emulation** — Execute certified attack chains mapped to MITRE ATT&CK tactics, from Initial Access to Exfiltration
- **Penetration testing workflows** — Repeatable, evidence-based execution with full audit trails
- **Excalibur Packs** — Certified script libraries covering real-world attack scenarios
- **AI Test Review** — Automated AI analysis of each test execution: evasion assessment, execution quality, structured intelligence output
- **Campaign management** — Group tests into named campaigns, track results, generate evidence reports
- **Purple Team automation** — Merlino threat intelligence drives Morgana execution automatically

Morgana operates as a three-tier platform:

| Tier | Description |
|---|---|
| **Server** | Python/FastAPI C2 server — manages agents, chains, campaigns, and jobs |
| **Agent** | Lightweight OS service (Windows NT Service / Linux systemd) on target machines |
| **Excalibur Packs** | MITRE ATT&CK-mapped adversary emulation script libraries |

---

## Domain Model

Morgana uses its own terminology:

| Term | Meaning |
|---|---|
| **Script** | Atomic execution unit (PowerShell / cmd / bash / Python) |
| **Chain** | Ordered sequence of scripts forming a kill chain |
| **Test** | Single execution run, linked to a Merlino row |
| **Campaign** | Named exercise grouping multiple tests |
| **Agent** | OS service installed on the target machine |

---

## Integration with Merlino

**Merlino** is the intelligence layer — free and open to all. **Morgana** is the execution layer — access requires contacting X3M.AI.

Once you have Morgana running, the integration with Merlino is seamless:

1. In Merlino, go to **Settings** and enter your Morgana server URL and API key
2. Build your threat profile in Merlino (import MITRE ATT&CK data, select threat groups, run CrossPick analysis)
3. Click **Tests and Operations** > **Synchronise** to map your techniques to Morgana scripts
4. Morgana automatically creates adversary chains and campaigns based on your threat profile
5. Launch Red Team operations from Morgana — results flow back to Merlino in real time
6. The AI engine reviews each test and generates structured intelligence reports

For a complete walkthrough, see **[Lab 03: Red Team Testing with Morgana](../../laboratories/Merlino%20User%20Guide-Lab%2003--Red%20Team%20Testing%20with%20Morgana%20Arsenal.md)**.

---

## Installation

Installation instructions are available in the [Morgana Install Guide](../../morgana/Install/README.md) for users who have received authorised access.

**[Contact X3M.AI to access Morgana](https://x3m.ai/contact/)**
