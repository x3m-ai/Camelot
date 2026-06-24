<div align="center">

# Camelot

### The Kingdom of Cyber Threat Intelligence

<table width="100%" border="0" cellspacing="0" cellpadding="8">
<tr>
<td align="left" width="20%">

[![Merlino](https://img.shields.io/badge/Merlino-CTI%20Add--in-667eea?style=for-the-badge&logo=microsoft-excel&logoColor=white)](https://x3m.ai/merlino/)

</td>
<td align="center">

![CTI](https://img.shields.io/badge/CTI-Cyber%20Threat%20Intelligence-0d6efd?style=for-the-badge)
![Red Team](https://img.shields.io/badge/Red%20Team-Adversary%20Emulation-dc3545?style=for-the-badge)
![Blue Team](https://img.shields.io/badge/Blue%20Team-Detection%20%26%20Defense-0dcaf0?style=for-the-badge)
![Purple Team](https://img.shields.io/badge/Purple%20Team-State%20of%20the%20Art-6f42c1?style=for-the-badge)

</td>
<td align="right" width="20%">

[![Community](https://img.shields.io/badge/Community-Discussions-28a745?style=for-the-badge&logo=github&logoColor=white)](https://github.com/x3m-ai/Camelot/discussions)

</td>
</tr>
</table>

---

*Built by [X3M.AI](https://x3m.ai) -- Threat Intelligence, Reimagined*

---

> ### Merlino and Morgana are free. If they help you, consider sponsoring the project.
> *Two tools. One developer. Zero subscription fees. Your support keeps them alive.*
>
> [![Sponsor on GitHub](https://img.shields.io/badge/♥_Sponsor-GitHub%20Sponsors-ea4aaa?style=for-the-badge&logo=github-sponsors&logoColor=white)](https://github.com/sponsors/x3m-ai)

</div>

---

## What Is Camelot?

**Camelot** is the community hub for the X3M.AI cybersecurity ecosystem. It brings together two powerful tools under one roof:

| Tool | What It Does | Install |
|---|---|---|
| **Merlino** | Free Excel Add-in for Cyber Threat Intelligence -- MITRE ATT&CK analysis, coverage heatmaps, AI-powered threat review, CVE enrichment, MISP integration | [Install free](https://x3m.ai/merlino/) |
| **Morgana** | Advanced Red Team platform for adversary emulation and penetration testing — AI-powered test review, Excalibur certified attack packs, Purple Team automation. Controlled distribution: contact X3M.AI for access | [Contact X3M.AI](https://x3m.ai/contact/) |

Together, they form a complete **threat intelligence and adversary emulation pipeline**: analyze threats in Merlino, then automatically generate and execute Red Team operations on Morgana.

---

## Merlino -- CTI in Excel

Merlino transforms Microsoft Excel into a full-featured Cyber Threat Intelligence workbench. No servers, no databases, no complex deployments -- just install the add-in and start analyzing.

### Key Capabilities

- **MITRE ATT&CK Integration** -- Import and analyze the complete ATT&CK framework (Enterprise, Mobile, ICS, Azure). Techniques, Groups, Software, Campaigns, Data Components, Mitigations, Detection Strategies
- **Threat Profiling** -- Select threat groups relevant to your organization, build a Catalogue, and generate a prioritized coverage heatmap showing exactly which techniques matter most
- **CrossPick Analysis** -- Merlino's proprietary algorithm calculates which techniques are shared across your threat profile, producing a risk-ranked priority matrix
- **AI-Powered Analysis** -- Connect OpenAI, Mistral, or other AI providers to generate automated threat assessments, detection gap analysis, and Red Team scenario planning
- **CVE Enrichment** -- Import recent vulnerabilities from NIST NVD and correlate them with your threat profile to prioritize patching
- **Exploit Database** -- 46,000+ exploits mapped to MITRE ATT&CK techniques
- **MISP Integration** -- Bidirectional pipeline: push your analysis to MISP, pull enriched intelligence back
- **Microsoft Security** -- Import Sentinel detection rules, Defender for Office 365 policies, and Intune configurations
- **Adaptive Reports** -- Generate self-contained HTML reports shareable with anyone
- **Attack Knowledge Graph** -- Interactive force-directed visualization of relationships between threat actors and techniques

### Install Merlino

Merlino is a free Microsoft Excel Add-in available in the Microsoft AppSource marketplace.

**[Merlino Portal](https://x3m.ai/merlino/)**

Requirements:
- Microsoft Excel Desktop (Windows or macOS) or Excel Online
- No installation on the server side -- everything runs in Excel

#### Installation steps

1. Open **Microsoft Excel**
2. Go to **Insert** tab → **Add-ins** → **Get Add-ins**
3. Search for **Merlino** in the Office Add-ins store
4. Click **Add**

![Search for Merlino in the Office Add-ins store](merlino/merlino-installation-step01.fw.png)

Merlino will appear in your Excel ribbon under **Add-ins**. Click it to open the taskpane and get started.

### Documentation

| Guide | Description |
|---|---|
| [Getting Started](docs/merlino/getting-started.md) | Quick start guide for first-time users |
| [Lab 01: Create Organization Threat Profile](laboratories/Merlino%20User%20Guide-Lab%2001--Create-Organization-Threat-Profile.md) | Complete walkthrough building a threat profile from six APT groups |
| [Lab 02: Microsoft Sentinel Detection Coverage](laboratories/Merlino%20User%20Guide-Lab%2002--Microsoft%20Sentinel%20Detection%20Coverage.md) | Analyze your Sentinel rules against your threat profile |
| [Lab 03: Red Team Testing with Morgana](laboratories/Merlino%20User%20Guide-Lab%2003--Red%20Team%20Testing%20with%20Morgana%20Arsenal.md) | Connect Merlino to Morgana and run adversary emulations |

---

## Morgana — Advanced Red Team Platform

**Morgana** is X3M.AI's advanced Red Team platform for adversary emulation, penetration testing, and Purple Team operations. It is a professional-grade, first-class product — not a plugin, not a wrapper — built from the ground up to deliver state-of-the-art offensive security capabilities in a controlled, repeatable, and intelligence-driven manner.

Morgana operates as a three-tier execution platform:

| Tier | Role |
|---|---|
| **Server** | Python-based C2 server managing campaigns, agents, chains, and test execution |
| **Agent** | Lightweight OS service (Windows NT Service / Linux systemd) deployed on target machines |
| **Excalibur Packs** | Certified adversary emulation script libraries mapped to MITRE ATT&CK tactics |

### Advanced AI Capabilities in Red Teaming

Morgana integrates cutting-edge AI directly into the Red Team workflow:

- **AI Test Review** — After each test execution, an AI engine automatically analyses the output, evaluates detection evasion, assesses execution quality, and generates structured intelligence reports
- **Multi-provider AI** — Supports GitHub Models, OpenAI, Anthropic, Azure OpenAI, Ollama, and AWS Bedrock as AI backends
- **AI-driven scenario planning** — Combined with Merlino's AI Assistant, teams can generate full Red Team operation plans based on threat intelligence and MITRE ATT&CK coverage gaps
- **Automated campaign analysis** — AI correlates test outcomes across campaigns to identify systemic detection weaknesses

### Why Distribution is Controlled

Morgana is a **genuinely offensive tool**. Its capabilities — persistent agent deployment, PowerShell/cmd/bash/Python execution on target machines, automated kill chain orchestration, AI-enhanced evasion analysis — are powerful enough to cause serious harm if misused.

For this reason, **X3M.AI controls the distribution of Morgana**. Access is granted only to security teams, organisations, and professionals who:

- Are conducting **authorised** Purple Team or Red Team operations
- Have **explicit written approval** to test the environments they are targeting
- Accept and operate under the X3M.AI responsible use terms

> **Morgana must never be used for unauthorised access, offensive operations against systems without explicit written permission, or any activity that violates applicable laws.**

### Access Morgana for Purple Teaming and Red Operations

If you are interested in using Morgana for Purple Team exercises or Red Team operations — especially in conjunction with **Merlino** (which is free and open to all) — contact X3M.AI directly. Our team will review your use case and guide you through the access process.

**[Contact X3M.AI to access Morgana](https://x3m.ai/contact/)**

> **Merlino** is free for everyone, with no registration required.  
> **Morgana** requires contacting X3M.AI for authorised access.

### What Morgana Delivers

- **Adversary emulation** — Execute certified attack chains mapped to MITRE ATT&CK tactics, from Initial Access to Exfiltration
- **Penetration testing workflows** — Repeatable, evidence-based test execution with full audit trails and AI-generated analysis
- **Purple Team automation** — Merlino threat intelligence drives Morgana execution: one click synchronises your threat profile into a complete adversary emulation campaign
- **Excalibur Packs** — Certified script libraries covering real-world attack scenarios: Entra ID, Execution, Lateral Movement, Persistence, and more
- **Campaign management** — Group multiple tests into named campaigns, track results, and generate evidence reports
- **Kill chain automation** — Script chains model multi-stage attack sequences from reconnaissance to impact

### The Merlino + Morgana Pipeline

The real power of the X3M.AI ecosystem is the automated pipeline between intelligence and execution:

1. **Analyse** — Build your threat profile in Merlino using MITRE ATT&CK data
2. **Prioritise** — CrossPick analysis identifies which techniques matter most for your organisation
3. **Synchronise** — One click in Merlino automatically creates adversary profiles and operation chains on Morgana
4. **Execute** — Launch controlled Red Team operations from Morgana with pre-configured attack chains
5. **Review** — AI engine automatically analyses each test result and generates structured intelligence
6. **Validate** — Results flow back to Merlino, updating your detection coverage evidence in real time

**[Contact X3M.AI to access Morgana](https://x3m.ai/contact/)**

---

## Community and Support

### Get Help

- **[Community Discussions](https://github.com/x3m-ai/Camelot/discussions)** -- Ask questions, share ideas, report issues, show your work
- **[Q&A](https://github.com/x3m-ai/Camelot/discussions/categories/q-a)** -- Get answers from the community and maintainers
- **[Troubleshooting](https://github.com/x3m-ai/Camelot/discussions/categories/troubleshooting)** -- Technical issues and bug reports

### Contribute

- **[Ideas](https://github.com/x3m-ai/Camelot/discussions/categories/ideas)** -- Suggest features, improvements, integrations
- **[Show and Tell](https://github.com/x3m-ai/Camelot/discussions/categories/show-and-tell)** -- Share your dashboards, reports, threat profiles, and use cases
- **[Contributing Guide](CONTRIBUTING.md)** -- How to contribute to documentation and the community

### Join the Project

Merlino and Morgana are growing fast and we are looking for passionate people who want to contribute. Whether you write code, documentation, or just love breaking things -- there is a place for you:

| Role | What You Would Do |
|---|---|
| **TypeScript / React Developer** | Build new taskpanes, improve UI, extend Excel integrations |
| **Python Developer** | Contribute to Morgana (server, agents, routers, execution engine) |
| **CTI Analyst** | Create threat profiles, write use cases, validate ATT&CK mappings |
| **Red Team Operator** | Test Morgana operations, build adversary profiles, write attack chains |
| **Detection Engineer** | Map Sentinel/Defender rules to ATT&CK, improve detection coverage analysis |
| **Technical Writer** | Improve documentation, write tutorials, translate guides |
| **UX / Designer** | Improve taskpane layouts, icons, dark theme, user experience |

Interested? Introduce yourself in [Discussions](https://github.com/x3m-ai/Camelot/discussions) or check the [Contributing Guide](CONTRIBUTING.md).

### Contributing to Merlino

We are absolutely thrilled to welcome any kind of contribution to Merlino. No contribution is too small or too niche -- everything is valuable and appreciated. Here are some ideas to get you started:

| What You Can Contribute | Where It Lives |
|---|---|
| **PowerShell export scripts** -- New scripts to export data, build catalogues, or automate Merlino workflows | [`powershell-export-scripts/`](powershell-export-scripts/) |
| **Templates** -- New or alternative Excel templates for Merlino threat profiles, heatmaps, or reports | [`standard-templates/`](standard-templates/) |
| **Labs** -- Step-by-step guides, use cases, walkthroughs, and practical exercises | [`laboratories/`](laboratories/) |
| **Anything else** -- CVE maps, ATT&CK mappings, detection rules, threat profiles, ideas... | Open a [Discussion](https://github.com/x3m-ai/Camelot/discussions) or a Pull Request |

If you have built something with Merlino -- a useful script, a creative template, a new lab, a clever integration -- please share it. The community grows with your contributions.

### Support the Project

---

<div align="center">

### Merlino and Morgana are free. If they help you, consider sponsoring the project.

*Two tools. One developer. Zero subscription fees. Your support keeps them alive.*

<br>

[![Sponsor on GitHub](https://img.shields.io/badge/Sponsor-GitHub%20Sponsors-ea4aaa?style=for-the-badge&logo=github-sponsors&logoColor=white)](https://github.com/sponsors/x3m-ai)

<br>

| Your support funds | |
|---|---|
| 🔬 New features and integrations | MITRE ATT&CK updates, new data sources, AI models |
| ☁️ Infrastructure | Cloudflare, CDN, licensing system, hosting |
| 📖 Documentation | Guides, tutorials, user labs |
| 🛡️ Threat intelligence data | CVE, Exploit-DB, MISP feeds |

<br>

*No subscription. No paywall. Pay what you think it's worth.*

</div>

---

### Contact

For partnership inquiries or enterprise collaboration, contact us at **support@x3m.ai**.

---

## License

This repository (documentation and community content) is licensed under the [MIT License](LICENSE).

- **Merlino Add-in** is free, no registration, distributed under its own EULA
- **Morgana** is free, distributed as a binary installer from this repository

---

<div align="center">

*Camelot -- Where Intelligence Meets Offense*

**[X3M.AI](https://x3m.ai)** | **[Merlino](https://x3m.ai/merlino/)** | **[Discussions](https://github.com/x3m-ai/Camelot/discussions)**

</div>
