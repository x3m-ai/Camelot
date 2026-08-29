# Excalibur Packages — Complete Reference

> **Full Morgana documentation:** [morgana/README.md](../README.md) — Section 10 covers Excalibur import, Tag configuration, update behavior, and authoring.

Excalibur is the certified adversary emulation and security validation script library for the **Morgana Advanced Red Team Platform**. This document covers every published Excalibur package, its provider, content, prerequisites, and usage guidance.

All packages are installed through the Morgana UI at **Scripts → Excalibur Packs → Refresh catalog → Install**. No runtime dependencies on the source repositories are required after installation.

> **Numbers as of 2026-08-29.** Run **Refresh catalog** to see the current version.

---

## Catalog summary

| Provider | Packages | Scripts | Chains | Domain |
|---|---|---|---|---|
| [X3M.AI](#1-x3mai-excalibur-packs) | 2 | 26 | 24 | Enterprise ATT&CK |
| [Red Canary — Atomic Red Team](#2-red-canary--atomic-red-team) | 13 | 1 603 | 1 616 | Enterprise ATT&CK |
| [MITRE CALDERA Stockpile](#3-mitre-caldera-stockpile) | 11 | 221 | 231 | Enterprise ATT&CK |
| [MITRE CTID](#4-mitre-ctid--adversary-emulation) | 24 | 398 | 27 | Enterprise ATT&CK |
| [LOLBAS Project](#5-lolbas--gtfobins) | 15 | 475 | 0 | Enterprise ATT&CK |
| [GTFOBins](#5-lolbas--gtfobins) | 34 | 3 582 | 0 | Enterprise ATT&CK |
| [LOLDrivers](#6-loldrivers) | 58 | 18 766 | 0 | Enterprise ATT&CK |
| [Frida Mobile](#7-frida-mobile) | 40 | 830 | 0 | Mobile ATT&CK |
| [MITRE CALDERA OT](#8-mitre-caldera-ot) | 15 | 223 | 223 | ICS ATT&CK |
| [ICS-SCADA-Fuzzer](#9-ics-scada-fuzzer) | 5 | 120 | 0 | ICS ATT&CK |
| [ANSSI FuzzySully](#10-anssi-fuzzysully) | 7 | 79 | 0 | ICS ATT&CK |
| [Stratus Red Team](#11-stratus-red-team) | 30 | 93 | 0 | Enterprise ATT&CK |
| **Total** | **254** | **26 416** | **2 121** | |

> Numbers reflect the catalog as of 2026-08-29. Run **Refresh catalog** to see the current version.

---

## How to use this reference

Each section below describes:

- **Package IDs** — the stable identifier used by Morgana when installing or referencing a pack
- **Contents** — Script and Chain counts
- **Prerequisites** — what must be in place before running Scripts
- **Platform / Target** — where Scripts execute (Execution Platform) and what they target (Target Environment)
- **ATT&CK coverage** — MITRE domain, tactic(s), and technique IDs where available
- **Source** — upstream repository and commit/version pinned

---

## 1. X3M.AI Excalibur Packs

Native Morgana adversary emulation packs authored by X3M.AI. These are the primary Excalibur-format packs and serve as the reference implementation for the Excalibur package schema.

### 1.1 Entra ID Emulation Pack

| | |
|---|---|
| **Package ID** | `excalibur-entraid-v1` |
| **Version** | 2.0.0 |
| **Scripts** | 23 |
| **Chains** | 22 |
| **ATT&CK Domain** | Enterprise ATT&CK |
| **Tactic** | Identity / Privilege |
| **Execution Platform** | Windows (PowerShell) |
| **Target Environment** | Microsoft Entra ID / Azure AD |

**Purpose:** Validate Microsoft Sentinel Entra ID analytics rules and Defender for Identity detections through controlled, authorised Purple Team execution. Each chain maps 1:1 to a named detection rule and is designed to trigger the rule reliably when the detection is correctly configured.

**Prerequisites:**

- `Microsoft.Graph` PowerShell module: `Install-Module Microsoft.Graph -Scope CurrentUser`
- Connected to Microsoft Graph with the following permission scopes:  
  `Group.ReadWrite.All`, `User.ReadWrite.All`, `RoleManagement.ReadWrite.Directory`,  
  `Policy.ReadWrite.AuthenticationMethod`, `AuditLog.Read.All`
- Global Administrator or equivalent role in a **test environment only**
- Never execute against production identity infrastructure

**Detection coverage:** 22 chains covering Entra ID analytics detections including MFA manipulation, PIM abuse, account creation/deletion patterns, credential additions to service principals, OAuth consent phishing, password spray, impossible travel, and guest account invite scenarios. Chain names follow the `Excalibur-EntraID-*` naming convention.

**Tags required:**
- `tenant_id` — Target Entra ID tenant ID
- `test_user_upn` — Test user UPN for execution context

---

### 1.2 General Utilities Pack

| | |
|---|---|
| **Package ID** | `excalibur-general-v1` |
| **Scripts** | 3 |
| **Chains** | 2 |
| **ATT&CK Domain** | Enterprise ATT&CK |
| **Execution Platform** | Windows |
| **Target Environment** | Windows endpoints |

**Purpose:** Utility and diagnostic scripts for validating Morgana Agent connectivity, timing, and baseline execution before running security content.

---

## 2. Red Canary — Atomic Red Team

Community conversion of the [Red Canary Atomic Red Team](https://github.com/redcanaryco/atomic-red-team) (ART) library into native Morgana pack JSON. One pack per MITRE ATT&CK tactic.

| Package ID | Tactic (TA) | Scripts |
|---|---|---|
| `art-initial_access-v1` | TA0001 Initial Access | 26 |
| `art-exec-v1` | TA0002 Execution | 139 |
| `art-persist-v1` | TA0003 Persistence | 197 |
| `art-privesc-v1` | TA0004 Privilege Escalation | 91 |
| `art-evasion-v1` | TA0005 Defense Evasion | 400 |
| `art-credaccess-v1` | TA0006 Credential Access | 206 |
| `art-discovery-v1` | TA0007 Discovery | 286 |
| `art-lateral-v1` | TA0008 Lateral Movement | 19 |
| `art-collection-v1` | TA0009 Collection | 54 |
| `art-exfil-v1` | TA0010 Exfiltration | 27 |
| `art-c2-v1` | TA0011 Command and Control | 90 |
| `art-impact-v1` | TA0040 Impact | 66 |
| `art-recon-v1` | TA0043 Reconnaissance | 2 |

**Source:** [redcanaryco/atomic-red-team](https://github.com/redcanaryco/atomic-red-team)  
**License:** MIT  
**Execution Platforms:** Windows, Linux, macOS  
**Script naming prefix:** `ART - `  

**Important:** ART scripts are converted from YAML to Morgana pack JSON. CALDERA and Atomic Red Team are not runtime dependencies. Scripts are categorised as **community content** and should be reviewed in an isolated lab before use.

**Prerequisites:** Vary per script. Inspect individual Script Tags and prerequisites before execution. Many scripts require specific tools, elevated privileges, or test-environment conditions.

---

## 3. MITRE CALDERA Stockpile

Community conversion of [MITRE CALDERA Stockpile](https://github.com/mitre/stockpile) abilities into native Morgana pack JSON. One pack per ATT&CK tactic.

| Package ID | Tactic | Scripts | Chains |
|---|---|---|---|
| `stockpile-collection-v1` | Collection | ~20 | ~20 |
| `stockpile-credential-access-v1` | Credential Access | ~20 | ~20 |
| `stockpile-defense-evasion-v1` | Defense Evasion | ~20 | ~20 |
| `stockpile-discovery-v1` | Discovery | ~30 | ~30 |
| `stockpile-execution-v1` | Execution | ~20 | ~20 |
| `stockpile-exfiltration-v1` | Exfiltration | ~10 | ~10 |
| `stockpile-impact-v1` | Impact | ~10 | ~10 |
| `stockpile-lateral-movement-v1` | Lateral Movement | ~20 | ~20 |
| `stockpile-persistence-v1` | Persistence | ~20 | ~20 |
| `stockpile-privilege-escalation-v1` | Privilege Escalation | ~20 | ~20 |
| `stockpile-initial-access-v1` | Initial Access | ~10 | ~10 |

**Source:** [mitre/stockpile](https://github.com/mitre/stockpile)  
**License:** Apache 2.0  
**Execution Platforms:** Windows, Linux, macOS  
**Script naming prefix:** `STOCKPILE - `  

**Important:** CALDERA and Stockpile are not runtime dependencies. Payload-dependent, build-only, and unsupported executor variants are skipped during conversion. Review the [conversion guide](stockpile/README.md) before installation.

---

## 4. MITRE CTID — Adversary Emulation

Conversion of [MITRE CTID adversary emulation plans](https://github.com/center-for-threat-informed-defense/adversary_emulation_library) into Morgana Chains. Covers both full and micro emulation plans.

| Package Type | Count | Description |
|---|---|---|
| Full Emulation | 5 | Complete multi-stage adversary campaigns |
| Micro Emulation | 19 | Focused single-technique or single-tactic coverage |

**Source:** [MITRE CTID Adversary Emulation Library](https://github.com/center-for-threat-informed-defense/adversary_emulation_library)  
**License:** Apache 2.0  
**Execution Platforms:** Windows, Linux  
**Coverage:** APT29, FIN6, Carbanak, and micro-plans for specific techniques  

**Important:** Full emulation plans require a properly configured multi-host lab. Review the [CTID README](ctid/README.md) and each plan's prerequisites before execution.

---

## 5. LOLBAS & GTFOBins

Living-off-the-land binary scripts converted from the LOLBAS and GTFOBins projects.

### LOLBAS

| | |
|---|---|
| **Packages** | 15 |
| **Scripts** | 475 |
| **Source** | [lolbas-project/LOLBAS](https://github.com/lolbas-project/LOLBAS) |
| **Execution Platform** | Windows |
| **Target** | Windows endpoints |
| **Technique scope** | Execute, Download, AWL bypass, Compile, Copy, Encode, Decode, Credentials, Reconnaissance, Lateral Movement |

### GTFOBins

| | |
|---|---|
| **Packages** | 34 |
| **Scripts** | 3 582 |
| **Source** | [GTFOBins/GTFOBins.github.io](https://github.com/GTFOBins/GTFOBins.github.io) |
| **Execution Platform** | Linux, macOS |
| **Target** | Linux/macOS endpoints |
| **Technique scope** | Shell, File read/write, SUID, Sudo, Capabilities, Cron, Bind/Reverse shell |

**Important:** LOLBAS and GTFOBins scripts execute built-in OS binaries in potentially dangerous ways. Always run in an authorised, isolated test environment. Review the [LOtL README](lotl/README.md) before use.

---

## 6. LOLDrivers

Security testing packages based on the [LOLDrivers](https://www.loldrivers.io/) project, covering vulnerable, malicious, and blocklist Windows kernel drivers.

| | |
|---|---|
| **Packages** | 58 |
| **Scripts** | 18 766 |
| **Source** | [magicsword-io/LOLDrivers](https://github.com/magicsword-io/LOLDrivers) |
| **Execution Platform** | Windows |
| **Target** | Windows endpoints |
| **Categories** | Vulnerable drivers, malicious drivers, blocklist entries, hunting signatures |
| **Purpose** | Driver-based detection validation, EDR/AV bypass testing, Windows kernel driver security |

**Important:** Driver-based techniques can cause system instability. Require kernel-mode execution environment. Review the [LOLDrivers README](loldrivers/README.md) and test in an isolated VM with a clean snapshot.

---

## 7. Frida Mobile

Mobile runtime instrumentation scripts based on the [Frida](https://frida.re/) dynamic instrumentation toolkit. Scripts target Android and iOS applications via Frida's JavaScript API.

### Android packages (12 packs, 369 scripts)

| Package ID | Category | Scripts |
|---|---|---|
| `frida-android-app-specific-v1` | App Specific Hooks | 206 |
| `frida-android-crypto-v1` | Cryptography | 25 |
| `frida-android-enumeration-v1` | Enumeration | 2 |
| `frida-android-ipc-v1` | IPC | 6 |
| `frida-android-native-v1` | Native | 1 |
| `frida-android-network-v1` | Network | 65 |
| `frida-android-other-v1` | Other | 3 |
| `frida-android-runtime-v1` | Runtime | 31 |
| `frida-android-security-controls-v1` | Security Controls | 16 |
| `frida-android-sensors-v1` | Sensors | 3 |
| `frida-android-storage-v1` | Storage | 8 |
| `frida-android-webview-v1` | WebView | 3 |

### iOS packages (12 packs, 175 scripts)

| Package ID | Category | Scripts |
|---|---|---|
| `frida-ios-app-specific-v1` | App Specific Hooks | 39 |
| `frida-ios-biometrics-v1` | Biometrics | 3 |
| `frida-ios-crypto-v1` | Cryptography | 15 |
| `frida-ios-enumeration-v1` | Enumeration | 11 |
| `frida-ios-native-v1` | Native | 6 |
| `frida-ios-network-v1` | Network | 67 |
| `frida-ios-other-v1` | Other | 1 |
| `frida-ios-runtime-v1` | Runtime | 1 |
| `frida-ios-security-controls-v1` | Security Controls | 20 |
| `frida-ios-sensors-v1` | Sensors | 3 |
| `frida-ios-storage-v1` | Storage | 9 |

### Cross-platform / framework packages (16 packs, 286 scripts)

Covers Flutter, React Native, Unity IL2CPP, Xamarin, and Universal hooks.

**Execution Platform:** Host Agent (PC/Mac running Frida + connected device)  
**Target Environment:** Android device/emulator, iOS device  
**License:** MIT  
**Source:** [frida/frida-scripts](https://github.com/frida/frida), community hooks  

**Prerequisites:**
- Frida Tools installed on the host: `pip install frida-tools`
- Target application installed on a test device or emulator
- For Android: `adb` access, Frida Server on device
- For iOS: jailbroken device or developer-mode enabled with Frida Gadget

Review the [Frida Mobile README](mobile/frida/README.md) before use.

---

## 8. MITRE CALDERA OT

OT/ICS attack scripts from the [MITRE CALDERA OT](https://github.com/mitre/caldera-ot) plugin, covering industrial protocols and automation systems. Targets industrial control systems using real OT protocol commands.

| Protocol | Packages | Scripts | Chains |
|---|---|---|---|
| Modbus | 3 | 36 | 36 |
| DNP3 | 3 | 88 | 88 |
| BACnet | 4 | 42 | 42 |
| GEMS / Generic ICS | 3 | 36 | 36 |
| PROFINET DCP | 2 | 21 | 21 |

**Source:** [mitre/caldera-ot](https://github.com/mitre/caldera-ot)  
**License:** Apache 2.0  
**ATT&CK Domain:** ICS ATT&CK  
**Execution Platform:** Linux (Morgana Agent on OT network segment)  
**Target Environment:** OT/ICS devices, PLCs, HMIs, industrial controllers  

**Important:** These scripts send real OT protocol commands and can affect physical processes. Execute only in an authorised, isolated OT test lab with change controls in place. Review the [OT README](ot/README.md).

---

## 9. ICS-SCADA-Fuzzer

Protocol-aware OT/ICS fuzzing profiles based on the [ridpath/ics-scada-fuzzer](https://github.com/ridpath/ics-scada-fuzzer) engine. Each script is a runtime-generating fuzz profile — a single script can produce thousands of mutated protocol test cases at execution time.

| Package ID | Protocol | Scripts | Default Port |
|---|---|---|---|
| `ics-scada-fuzzer-modbus-v1` | Modbus/TCP | 24 | 502 |
| `ics-scada-fuzzer-dnp3-v1` | DNP3 | 24 | 20000 |
| `ics-scada-fuzzer-s7-v1` | S7comm (Siemens) | 24 | 102 |
| `ics-scada-fuzzer-iec104-v1` | IEC 60870-5-104 | 24 | 2404 |
| `ics-scada-fuzzer-opcua-v1` | OPC-UA | 24 | 4840 |

**Per protocol:** 16 generated profiles (8 strategies × stateful + stateless) + 8 PCAP replay profiles = 24 scripts.

**Mutation strategies:** random, bitflip, overflow, dictionary, format, type, time, sequence.

**Source:** [ridpath/ics-scada-fuzzer](https://github.com/ridpath/ics-scada-fuzzer) @ `09c328fb`  
**License:** MIT  
**Binary:** Verified Linux ELF — `ics-fuzzer-linux-amd64` (SHA256: `db6a802ce7ee29e72c641d6247da0c7b2796fe6b9d2b1c74887b7b65f45e1bdc`)  
**ATT&CK Domain:** ICS ATT&CK  
**Execution Platform:** Linux (Morgana Agent)  
**Target Environment:** Authorized OT/ICS testbed  

**Runtime scale:** Configure `ot_fuzz_iterations` tag. A single script can generate 1,000–100,000+ protocol mutations. Use `ot_fuzz_timeout` to bound execution.

**Tags required:** `ot_fuzz_target`, `ot_fuzz_port`, `ot_fuzz_iterations`, `ot_fuzz_timeout`

**Important:** Never target production OT infrastructure. Fuzzing can disrupt physical processes and cause hardware faults. See [ICS-SCADA-Fuzzer README](ot/fuzzing/ics-scada-fuzzer/README.md).

---

## 10. ANSSI FuzzySully

Deep OPC UA protocol fuzzing engine based on [ANSSI-FR/fuzzysully](https://github.com/ANSSI-FR/fuzzysully). Targets OPC UA servers, Global Discovery Servers (GDS), and reverse-client connections with protocol-layer mutation.

| Package ID | Mode | Policy | Scripts |
|---|---|---|---|
| `fuzzysully-server-none-v1` | Server | None | 20 |
| `fuzzysully-server-basic256sha256-v1` | Server | Basic256Sha256 (Sign + SignEncrypt) | 34 |
| `fuzzysully-gds-v1` | GDS | Basic256Sha256 | 18 |
| `fuzzysully-reverse-v1` | Reverse Client | None | 1 |
| `fuzzysully-server-none-targeted-v1` | Server — targeted nodes | None | 4 |
| `fuzzysully-server-basic256sha256-targeted-v1` | Server — targeted nodes | Basic256Sha256 | 1 |
| `fuzzysully-reverse-targeted-v1` | Reverse — targeted nodes | None | 1 |

**Fuzz functions (server):** 20 OPC UA services including Hello, OpenSecureChannel, CreateSession, Browse, Read, HistoryRead, CreateSubscription, CreateMonitoredItems, AddNodes, and more.

**Fuzz functions (GDS):** 9 certificate lifecycle operations including GetTrustList, StartSigningRequest, StartNewKeyPairRequest, FinishRequest, RevokeCertificate.

**Source:** [ANSSI-FR/fuzzysully](https://github.com/ANSSI-FR/fuzzysully) @ `50a0631`  
**License:** GPL-2.0  
**ATT&CK Domain:** ICS ATT&CK — Impair Process Control  
**Execution Platform:** Linux (Morgana Agent with Python 3.10+)  
**Target Environment:** Authorized OPC UA server / GDS / OT testbed  

**Prerequisites:**
- Python 3.10+ on the Linux Agent
- FuzzySully installed: `pip install fuzzysully==0.1.1`
- For Basic256Sha256 profiles: client certificate and private key (PEM)
- For GDS profiles: running Global Discovery Server

**Tags required:** `opcua_target_host`, `opcua_target_port`, `fuzz_max_cases`, `fuzz_max_duration`

**Important:** OPC UA fuzzing can crash or hang real devices. Always use an isolated OT lab. GDS operations can invalidate PKI trust chains. See [ANSSI FuzzySully README](ot/fuzzing/fuzzysully/README.md).

---

## 11. Stratus Red Team

Cloud adversary-emulation techniques from [DataDog/stratus-red-team](https://github.com/DataDog/stratus-red-team). Stratus is effectively **Atomic Red Team for cloud environments** — each technique is a granular self-contained cloud API operation mapped to MITRE ATT&CK.

Morgana executes the official Stratus binary using an isolated `MORGANA_TEST_ID` correlation ID for Detection Fabric correlation. Stratus handles all prerequisite cloud infrastructure via Terraform warmup automatically.

| Platform | Packages | Scripts | Tactics |
|---|---|---|---|
| AWS | 10 | 44 | Persistence, Privilege Escalation, Defense Evasion, Credential Access, Discovery, Execution, Lateral Movement, Exfiltration, Impact, Initial Access |
| Azure | 6 | 15 | Persistence, Privilege Escalation, Credential Access, Execution, Exfiltration, Impact |
| GCP | 7 | 19 | Persistence, Privilege Escalation, Defense Evasion, Discovery, Execution, Exfiltration, Impact, Initial Access |
| Entra ID | 1 | 7 | Persistence |
| Kubernetes | 3 | 6 | Persistence, Privilege Escalation, Credential Access |
| Amazon EKS | 2 | 2 | Persistence, Lateral Movement |

**Source:** [DataDog/stratus-red-team](https://github.com/DataDog/stratus-red-team) @ v2.36.0 (`21c8fef`)  
**License:** Apache-2.0  
**ATT&CK Domain:** Enterprise ATT&CK  
**Execution Platforms:** Windows, Linux, macOS  
**Target Environments:** Cloud (AWS / Azure / GCP / Entra ID / Kubernetes / EKS)  

**Prerequisites (per platform):**
- **AWS:** AWS credentials (env vars, profile, or IAM instance profile)
- **Azure:** `az login` or Managed Identity
- **Entra ID:** `az login` with Entra ID permissions
- **GCP:** Application Default Credentials (`gcloud auth application-default login`)
- **Kubernetes:** kubectl kubeconfig with current context
- **EKS:** AWS credentials + `aws eks update-kubeconfig` for the cluster

**Lifecycle:** Each Script invokes `stratus detonate <technique-id>`. Cleanup via `cleanup_command` calls `stratus cleanup <technique-id>` using the same `MORGANA_TEST_ID` correlation ID.

**Important:**
- Always use an authorized sandbox/test cloud account — never target production workloads
- Some techniques create real cloud resources that incur cost — always run cleanup
- Warmup can take 1–5 minutes for Terraform-based infrastructure setup

See the [Stratus README](cloud/stratus/README.md) for full details.

---

## Package update workflow

When new packages or package versions are published to Camelot:

1. Open Morgana UI
2. Go to **Scripts → Excalibur Packs**
3. Select **Refresh catalog** — downloads the latest `catalog.json`
4. New/updated packages appear in the list automatically
5. Select **Install** on individual packages or **Install All**

No Morgana software update is required when Camelot publishes new packages.

---

## Authoring custom packages

The Excalibur package schema is documented in the [Morgana manual](../README.md#107-authoring-a-pack). To contribute community packages, follow the format used by existing providers and open a pull request to the [Camelot repository](https://github.com/x3m-ai/Camelot).

---

## Source references

| Source | Repository | License |
|---|---|---|
| Red Canary Atomic Red Team | [redcanaryco/atomic-red-team](https://github.com/redcanaryco/atomic-red-team) | MIT |
| MITRE CALDERA Stockpile | [mitre/stockpile](https://github.com/mitre/stockpile) | Apache 2.0 |
| MITRE CTID | [center-for-threat-informed-defense/adversary_emulation_library](https://github.com/center-for-threat-informed-defense/adversary_emulation_library) | Apache 2.0 |
| LOLBAS | [lolbas-project/LOLBAS](https://github.com/lolbas-project/LOLBAS) | CC-BY-4.0 |
| GTFOBins | [GTFOBins/GTFOBins.github.io](https://github.com/GTFOBins/GTFOBins.github.io) | MIT |
| LOLDrivers | [magicsword-io/LOLDrivers](https://github.com/magicsword-io/LOLDrivers) | CC-BY-4.0 |
| Frida | [frida/frida](https://github.com/frida/frida) | MIT |
| MITRE CALDERA OT | [mitre/caldera-ot](https://github.com/mitre/caldera-ot) | Apache 2.0 |
| ICS-SCADA-Fuzzer | [ridpath/ics-scada-fuzzer](https://github.com/ridpath/ics-scada-fuzzer) | MIT |
| ANSSI FuzzySully | [ANSSI-FR/fuzzysully](https://github.com/ANSSI-FR/fuzzysully) | GPL-2.0 |

All community content is converted to Morgana pack JSON format. Source repositories are not runtime dependencies.
