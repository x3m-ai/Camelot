# Merlino — CTI in Excel

> **Free Microsoft Excel Add-in for Cyber Threat Intelligence and Purple Teaming**  
> Publisher: [X3M.AI](https://x3m.ai) | Portal: [x3m.ai/merlino](https://x3m.ai/merlino/)  
> No registration. No subscription. No data collection.

---

## What is Merlino?

Merlino transforms Microsoft Excel into a full-featured **Cyber Threat Intelligence workbench**. It brings MITRE ATT&CK, Red Team operations, CVE enrichment, MISP integration, and AI-powered analysis directly into your spreadsheet — with zero backend infrastructure required.

Everything runs locally. Your data never leaves Excel.

### Key capabilities

| Feature | Description |
|---------|-------------|
| **MITRE ATT&CK** | Import Enterprise, Mobile, ICS frameworks. Techniques, Groups, Software, Campaigns, Mitigations, Data Sources |
| **Threat Profiling** | Pick threat groups relevant to your org, build a Catalogue, generate a prioritized coverage heatmap |
| **CrossPick Analysis** | Proprietary algorithm identifying which techniques are shared across your threat profile |
| **Smart View** | Color-coded ATT&CK matrix (white → yellow → orange → red) based on TCode frequency |
| **Morgana Integration** | One-click sync: push threat profiles to Morgana, launch Red Team operations, pull results back |
| **CVE Enrichment** | NIST NVD v2.0 search + CISA KEV + CWE-to-MITRE technique mapping |
| **Exploit Database** | 46,000+ exploits indexed and mapped to MITRE ATT&CK |
| **MISP Integration** | Bidirectional: push analysis to MISP, pull IOCs and enriched intelligence back |
| **Microsoft Security** | Import Sentinel detection rules, Defender for Office 365 policies, Intune configurations |
| **AI Assistant** | Multi-agent AI: threat assessments, detection gap analysis, Red Team scenario generation |
| **Attack Knowledge Graph** | Force-directed interactive visualization of threat actor / technique relationships |
| **Adaptive Reports** | Self-contained HTML reports with ECharts visualizations, shareable with anyone |

---

## Installation

Merlino is available in the **Microsoft AppSource** marketplace — install it directly from inside Excel.

### Steps

1. Open **Microsoft Excel**
2. Go to the **Insert** tab → click **Add-ins** → **Get Add-ins**
3. In the Office Add-ins store, search for **Merlino**
4. Click **Add**

![Search for Merlino in the Office Add-ins store](merlino-installation-step01.fw.png)

Merlino appears in your Excel ribbon. Click it to open the taskpane sidebar.

### Requirements

| Component | Requirement |
|-----------|-------------|
| Excel | Microsoft 365, Excel 2021, or Excel Online |
| OS | Windows 10/11, macOS, or any browser (Excel Online) |
| Internet | Required for data imports and AI features |
| Backend | None — everything runs inside Excel |

---

## Quick Start

1. Click **Templates** in the Merlino ribbon → load the **Enterprise** template
2. Click **Sources** → import **Techniques**, **Groups**, **Software**, **Campaigns**
3. On the **Groups** sheet, set `Pick = TRUE` on threat groups relevant to your organization
4. Open **Runbooks** → run **Include Picks in Catalogue**
5. Run **Update Core** + **Smart View**
6. Open the **Main Coverage** sheet — your prioritized ATT&CK heatmap is ready

For a complete walkthrough, see [Lab 01: Create Organization Threat Profile](../laboratories/Merlino%20User%20Guide-Lab%2001--Create-Organization-Threat-Profile.md).

---

## Connecting to Morgana (Red Team)

Morgana is the X3M.AI Red Team execution platform that pairs with Merlino. Once connected, Merlino can automatically create adversary profiles and launch operations on Morgana based on your threat profile.

### Setup

1. Install Morgana — download the installer from [morgana/Install](../morgana/Install/)
2. Get the Morgana API key: open `https://YOUR_MORGANA_SERVER:8888/ui/` → **Admin** → **Generate API Key**
3. In Merlino, open **Settings** (taskpane)
4. Under **Caldera / Morgana**, fill in:
   - **URL:** `https://YOUR_MORGANA_SERVER:8888`
   - **API Key:** the key from step 2
5. Click **Save**

### Using the integration

| Taskpane | What it does |
|----------|-------------|
| **Tests & Operations** | View and manage Morgana operations, run chains, see real-time results |
| **Agents** | Monitor deployed Morgana agents, check status and last heartbeat |
| **Runbooks → Synchronize** | Push your Catalogue (picked techniques) to Morgana as scripts and chains in one click |

For a full walkthrough, see [Lab 03: Red Team Testing with Morgana](../laboratories/Merlino%20User%20Guide-Lab%2003--Red%20Team%20Testing%20with%20Morgana%20Arsenal.md).

---

## Connecting to MISP

MISP integration enables a bidirectional IOC pipeline: push your ATT&CK analysis to MISP as events, and pull enriched intelligence (IOCs, threat actor correlations) back into Merlino.

### Setup

1. Open Merlino → **Settings**
2. Under **MISP**, fill in:
   - **URL:** `https://YOUR_MISP_INSTANCE`
   - **API Key:** your MISP automation key (Profile → Auth keys)
3. Click **Save**

### Using the integration

Open the **IOC** taskpane in Merlino to:
- Browse and search MISP events
- Pull IOCs into the IOC sheet for analysis
- Push technique-tagged events back to MISP
- Visualize IOC clusters in the interactive graph

---

## AI Configuration

Merlino includes a multi-agent AI assistant that can generate threat assessments, detect coverage gaps, suggest Red Team scenarios, and answer questions about your ATT&CK data.

### Supported providers

| Provider | What you need | Notes |
|----------|---------------|-------|
| **GitHub Copilot** | GitHub Copilot subscription | No extra API key — uses your existing Copilot account |
| **OpenAI** | OpenAI API key | GPT-4o, GPT-4.1 and other models |
| **Mistral** | Mistral API key | Mistral Large, Codestral |
| **Ollama** | Ollama running locally | Zero data egress — fully offline |
| **Anthropic** | Anthropic API key | Claude 3.5 Sonnet, Claude 3 Opus |
| **AWS Bedrock** | AWS credentials | Claude, Llama, Titan models via AWS |

### Setup

1. Open Merlino → **Settings**
2. Scroll to the **AI** section
3. Select your provider and enter the required credentials
4. Click **Save**
5. Open the **AI Assistant** taskpane — the assistant is ready

### How it works

The AI assistant reads the data from your active Excel sheets (techniques, groups, catalogue, coverage) and uses a multi-agent architecture:

- **Orchestrator Agent** — decomposes your question into tasks, coordinates specialist agents
- **Excel Agent** — reads and writes data in your workbook
- **MITRE Agent** — validates and maps technique IDs

You can also configure AI-driven automation by setting up rows in the dedicated **AI** sheet inside your Merlino workbook.

---

## Folder Contents

| Path | Contents |
|------|----------|
| [`agents/`](agents/) | Morgana agent binaries for deployment on target machines |
| [`templates/`](templates/) | Standard Merlino Excel templates (.xlsx) |

---

## Documentation and Labs

| Guide | Description |
|-------|-------------|
| [Getting Started](../docs/merlino/getting-started.md) | Up and running in 5 minutes |
| [Lab 01: Threat Profile](../laboratories/Merlino%20User%20Guide-Lab%2001--Create-Organization-Threat-Profile.md) | Build a threat profile from six APT groups |
| [Lab 02: Sentinel Coverage](../laboratories/Merlino%20User%20Guide-Lab%2002--Microsoft%20Sentinel%20Detection%20Coverage.md) | Map Sentinel rules to your threat profile |
| [Lab 03: Red Team with Morgana](../laboratories/Merlino%20User%20Guide-Lab%2003--Red%20Team%20Testing%20with%20Morgana%20Arsenal.md) | Connect Merlino to Morgana and run adversary emulations |

---

## Support

- **Portal:** [x3m.ai/merlino](https://x3m.ai/merlino/)
- **Community:** [github.com/x3m-ai/Camelot/discussions](https://github.com/x3m-ai/Camelot/discussions)
- **Issues / Questions:** open a thread in [Discussions](https://github.com/x3m-ai/Camelot/discussions/categories/q-a)

---

> Merlino is developed by [X3M.AI Ltd](https://x3m.ai) (UK).  
> Free to use. No registration, no telemetry, no data collection.
