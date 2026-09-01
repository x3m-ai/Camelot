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
- **Industrial Lab** — Deploy, manage, reset, and observe industrial mock devices / simulators on Agents
- **Mobile Lab** — Provision and manage Android and iOS security test environments (emulators, simulators, physical devices) on Agents- **Drozer / MEDUSA / Frida Mobile** â€” Mobile security providers bound to Mobile Lab targets for Android application-model assessment (Drozer) and runtime instrumentation (MEDUSA, Frida Mobile)- **AI Test Review** — Automated AI analysis of each test execution: evasion assessment, execution quality, structured intelligence output
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
| **Lab Host** | A Morgana Agent enabled to run Industrial Lab services (mock devices / simulators) |
| **Lab Service** | One deployed mock/simulator instance (e.g. a Modbus PLC) |
| **Lab** | A composition of one or more Lab Services from a template |
| **Mobile Lab** | Morgana subsystem for provisioning and managing mobile test devices and mobile test applications |
| **Mobile Lab Host** | A Morgana Agent enabled to run Mobile Lab tooling (Android SDK, Apple simctl, ADB, Frida) |
| **Mobile Device** | A mobile runtime target (AVD, simulator, physical device, external virtual device) |

---

## Industrial Lab

Morgana includes a provider-agnostic **Industrial Lab** subsystem for deploying
and managing industrial mock devices and simulators on Agents acting as Lab
Hosts. The first provider is **IndustriConnect** (BACnet, DNP3, EtherCAT,
EtherNet/IP, Modbus, MQTT/Sparkplug B, OPC UA, PROFIBUS, PROFINET, Siemens S7).

1. **Hosts** tab — check and enable an Agent as a Lab Host.
2. **Services** tab — install and start a mock device.
3. **Run Compatible Scripts** — point the matching IndustriConnect Scripts at the running mock.
4. **Reset / Stop** the Lab when done.

Mocks are simulators, not hardware emulators. See the [Industrial Lab guide](../../morgana/industrial-lab/README.md).

---

## Mobile Lab

Morgana includes a provider-agnostic **Mobile Lab** subsystem for provisioning
and managing mobile security test environments on Agents acting as Mobile Lab
Hosts. Initial providers: **Android Emulator**, **Apple Simulator**, physical
Android/iOS devices, and an extensible external virtual-device architecture
(Corellium).

1. **Hosts** tab — check and enable an Agent as a Mobile Lab Host.
2. **Templates** tab — deploy a lab (e.g. "Android Security Lab — Clean AVD").
3. **Devices** tab — start the device and wait for `READY`.
4. **Apps** tab — register and install a test app.
5. **Run Compatible Scripts** â€” bind MEDUSA / Frida Mobile / Drozer procedures to the target.

Apple Simulator is available only on compatible macOS/Xcode Hosts (no false
Windows/Linux support). Physical devices are non-destructive by default. See
the [Mobile Lab guide](../../morgana/mobile-lab/README.md).

---

## OWASP MASTG + Hacking Playground

Morgana integrates the **OWASP Mobile Application Security Testing Guide
(MASTG)** and the **OWASP MASTG Hacking Playground** as a mobile security test
library layered on Mobile Lab:

1. **Mobile Lab → MASTG Tests** — browse the MASTG test library (292 tests with
   MASVS mappings, automation classification, deprecation status) or open tests
   compatible with a device via the device's **MASTG** action.
2. **Run Compatible Scripts** — jump from a MASTG test to the matching OWASP
   MASTG / Drozer / MEDUSA / Frida Mobile Scripts.
3. **Hacking Playground apps** — appear in the Mobile Lab **Apps** tab as
   intentionally-vulnerable App Assets (Android Java/Kotlin, iOS JWT); deploy
   `android-mastg-playground-lab` or `ios-mastg-playground-lab` templates.

MASTG Tests are procedure cards (manual/semi/auto), not fake automation. Only
real Frida demos are published as executable Scripts. The Hacking Playground
does not cover every MASTG test, and Morgana does not claim it does. See
`Morgana/docs/OWASP_MASTG_INTEGRATION.md`.

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
