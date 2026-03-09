<div align="center">

# Camelot

### The Kingdom of Cyber Threat Intelligence

<table width="100%" border="0" cellspacing="0" cellpadding="8">
<tr>
<td align="left" width="20%">

[![Merlino](https://img.shields.io/badge/Merlino-CTI%20Add--in-667eea?style=for-the-badge&logo=microsoft-excel&logoColor=white)](https://merlino.x3m.ai)

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

> ### 💜 Merlino is free. If it helps you, consider buying Nino a coffee.
> *One tool. One developer. Zero subscription fees. Your support keeps it alive.*
>
> [![Sponsor on GitHub](https://img.shields.io/badge/♥_Sponsor-GitHub%20Sponsors-ea4aaa?style=for-the-badge&logo=github-sponsors&logoColor=white)](https://github.com/sponsors/x3m-ai) &nbsp; [![Ko-fi](https://img.shields.io/badge/☕_Buy%20a%20Coffee-Ko--fi-ff5e5b?style=for-the-badge&logo=ko-fi&logoColor=white)](https://ko-fi.com/x3mai)

</div>

---

## What Is Camelot?

**Camelot** is the community hub for the X3M.AI cybersecurity ecosystem. It brings together two powerful tools under one roof:

| Tool | What It Does | Where It Lives |
|---|---|---|
| **Merlino** | [Excel Add-in for Cyber Threat Intelligence -- MITRE ATT&CK analysis, coverage heatmaps, AI-powered threat review, CVE enrichment, MISP integration](https://merlino.x3m.ai) | [Install free](https://merlino.x3m.ai) |
| **Morgana Arsenal** | Caldera-based Red Team platform for adversary emulation -- attack simulation, agent management, operation automation | [GitHub repo](https://github.com/x3m-ai/Morgana-Arsenal) |

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

Merlino is a free Microsoft Excel Add-in. Install it directly from Cloudflare Pages:

**[Install Merlino](https://merlino.x3m.ai)**

Requirements:
- Microsoft Excel (Desktop or Web)
- Windows, macOS, or Excel Online

### Documentation

| Guide | Description |
|---|---|
| [Getting Started](docs/merlino/getting-started.md) | Quick start guide for first-time users |
| User Guide -- Lab 01: Create Organization Threat Profile | Complete walkthrough building a threat profile from six APT groups |
| User Guide -- Lab 02: Microsoft Sentinel Detection Coverage | Analyze your Sentinel rules against your threat profile |
| User Guide -- Lab 03: Red Team Testing with Morgana Arsenal | Connect Merlino to Morgana and run adversary emulations |

---

## Morgana Arsenal -- Red Team Platform

Morgana Arsenal is X3M.AI's fork of MITRE Caldera, enhanced for seamless integration with Merlino. It provides:

- Adversary emulation and Red Team operations
- Agent deployment and management
- Attack ability execution across the ATT&CK framework
- Automated operation creation from Merlino's threat profiles

**[Morgana Arsenal Repository](https://github.com/x3m-ai/Morgana-Arsenal)**

### The Merlino + Morgana Pipeline

The real power of the X3M.AI ecosystem is the automated pipeline between intelligence and offense:

1. **Analyze** -- Build your threat profile in Merlino using MITRE ATT&CK data
2. **Prioritize** -- CrossPick analysis identifies which techniques matter most
3. **Synchronize** -- One click in Merlino automatically creates adversary profiles and operations on Morgana
4. **Execute** -- Launch Red Team operations directly from Morgana with pre-configured attack chains
5. **Validate** -- Results flow back to Merlino, updating your Tests Coverage in real time

What normally takes a Red Team operator days of manual work -- building adversary profiles, selecting abilities, configuring operations -- Merlino accomplishes in seconds.

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
| **Python Developer** | Contribute to Morgana Arsenal (Caldera plugins, agents, abilities) |
| **CTI Analyst** | Create threat profiles, write use cases, validate ATT&CK mappings |
| **Red Team Operator** | Test Morgana operations, build adversary profiles, write attack chains |
| **Detection Engineer** | Map Sentinel/Defender rules to ATT&CK, improve detection coverage analysis |
| **Technical Writer** | Improve documentation, write tutorials, translate guides |
| **UX / Designer** | Improve taskpane layouts, icons, dark theme, user experience |

Interested? Introduce yourself in [Discussions](https://github.com/x3m-ai/Camelot/discussions) or check the [Contributing Guide](CONTRIBUTING.md).

### Support the Project

---

<div align="center">

## ❤️ Support Merlino & Morgana

**Merlino is free. Forever. Built by one person, with passion.**

If it saves you time, helps your team, or makes you a better threat hunter --
please consider supporting its development. Every contribution keeps the project alive.

<br>

[![Sponsor on GitHub](https://img.shields.io/badge/Sponsor-GitHub%20Sponsors-ea4aaa?style=for-the-badge&logo=github-sponsors&logoColor=white)](https://github.com/sponsors/x3m-ai)
&nbsp;&nbsp;
[![Ko-fi](https://img.shields.io/badge/Buy%20a%20Coffee-Ko--fi-ff5e5b?style=for-the-badge&logo=ko-fi&logoColor=white)](https://ko-fi.com/x3mai)

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

- **Merlino Add-in** is free, distributed under its own EULA
- **Morgana Arsenal** is open source under the Apache 2.0 License (inherited from Caldera)

---

<div align="center">

*Camelot -- Where Intelligence Meets Offense*

**[X3M.AI](https://x3m.ai)** | **[Merlino](https://merlino.x3m.ai)** | **[Morgana Arsenal](https://github.com/x3m-ai/Morgana-Arsenal)** | **[Discussions](https://github.com/x3m-ai/Camelot/discussions)**

</div>
