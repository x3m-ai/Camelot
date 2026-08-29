# Excalibur Packages

Excalibur is the certified adversary emulation script library for the **Morgana Advanced Red Team Platform**.

Excalibur packages are professionally crafted attack script collections covering real-world MITRE ATT&CK tactics and techniques. Each package targets a specific platform, identity domain, or detection surface and is designed for authorised Purple Team and Red Team exercises — including adversary emulation, kill chain execution, and detection validation against enterprise security controls (Microsoft Sentinel, Defender for Endpoint, and others).

> **Full package reference:** See **[PACKAGES.md](PACKAGES.md)** for the complete catalog — all 224 packages, scripts, chains, prerequisites, ATT&CK coverage, and source references.

> **Access notice:** Excalibur packages run inside Morgana, which is a controlled-distribution platform. To use Excalibur packs for Red Team or Purple Team operations, you must have authorised access to Morgana. [Contact X3M.AI](https://x3m.ai/contact/) to request access.

---

## Available Packages

| Provider | Packages | Scripts | Chains |
|---|---|---|---|
| X3M.AI Excalibur | 2 | 26 | 24 |
| [Red Canary — Atomic Red Team](art/) | 13 | 1 603 | 1 616 |
| [MITRE CALDERA Stockpile](stockpile/) | 11 | 221 | 231 |
| [MITRE CTID](ctid/) | 24 | 398 | 27 |
| [LOLBAS & GTFOBins](lotl/) | 49 | 4 057 | 0 |
| [LOLDrivers](loldrivers/) | 58 | 18 766 | 0 |
| [Frida Mobile](mobile/frida/) | 40 | 830 | 0 |
| [MITRE CALDERA OT](ot/) | 15 | 223 | 223 |
| [ICS-SCADA-Fuzzer](ot/fuzzing/ics-scada-fuzzer/) | 5 | 120 | 0 |
| [ANSSI FuzzySully](ot/fuzzing/fuzzysully/) | 7 | 79 | 0 |
| [Stratus Red Team](cloud/stratus/) | 30 | 93 | 0 |
| [Elastic Cortado](detection/cortado/) | 13 | 698 | 0 |
| [LOLRMM](lotl/lolrmm/) | 3 | 320 | 0 |
| [ControlThings Suite](ot/controlthings/) | 5 | 33 | 0 |
| **Total** | **275** | **27 467** | **2 121** |

Morgana downloads the current [catalog](catalog.json) when the operator selects **Scripts > Excalibur Packs > Refresh catalog**. After support for a category is deployed once, future package additions and updates are published through Camelot without requiring a new Morgana release.

---

## How to Import into Morgana

1. Open Morgana web UI: `https://<your-morgana-host>:8888/ui/`.
2. Open **Scripts > Excalibur Packs**.
3. Select **Refresh catalog**.
4. Review source, tactic, platform, prerequisites, Script count, and Chain count.
5. Select **Install**, **Import Selected**, or **Install All**.
6. Verify the importer result before executing any content.

Community-source packs are normalized into the same generic package schema. CALDERA and Atomic Red Team are not runtime dependencies.

---

## How to Load into Merlino

Once the package is imported in Morgana, open Merlino in Excel:

1. Go to **Sources** taskpane
2. Scroll to **Excalibur Attack Simulations**
3. The combo shows packages already installed in Morgana — select the one you want
4. Click **Import** to load the simulations into your Catalogue sheet

---

## Excalibur - Entra ID Emulation Pack v2.0.0

**Author:** X3M.AI  
**Domain:** MITRE ATT&CK Enterprise  
**Contents:** 23 scripts + 22 chains  
**Target:** Microsoft Entra ID detection validation (Microsoft Sentinel analytics rules)

### Prerequisites

- `Microsoft.Graph` PowerShell module: `Install-Module Microsoft.Graph -Scope CurrentUser`
- Connected to Microsoft Graph with scopes:  
  `Group.ReadWrite.All`, `User.ReadWrite.All`, `RoleManagement.ReadWrite.Directory`,  
  `Policy.ReadWrite.AuthenticationMethod`, `AuditLog.Read.All`
- **Test environment only** — never run against production identity infrastructure
- Global Administrator or equivalent test role required

### Detection Coverage

All 22 chains map 1:1 to Microsoft Sentinel Entra ID analytics rules. Chains are named with the `Excalibur-EntraID-*` prefix to match their corresponding detection rule names.
