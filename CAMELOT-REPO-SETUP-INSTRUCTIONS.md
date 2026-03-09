# Camelot Repository -- Complete Setup Instructions

> **Purpose:** This document is a complete instruction set for an AI agent to create and configure the `x3m-ai/Camelot` GitHub repository from scratch. Feed this entire document to the agent in a new VS Code workspace.

---

## CONTEXT

**X3M.AI Ltd** builds cybersecurity tools. The two main products are:

- **Merlino** -- A Microsoft Excel Add-in for Cyber Threat Intelligence (CTI). It integrates MITRE ATT&CK, Red Team operations, AI analysis, CVE enrichment, MISP intelligence sharing, and more into a unified Excel workbench. Merlino is **free** and distributed via Cloudflare Pages at `https://merlino-addin.pages.dev`. The source code is in a **private** repo (`x3m-ai/Merlino`).

- **Morgana Arsenal** -- A fork of MITRE Caldera for Red Team adversary emulation. It is already a **public** repo at `x3m-ai/Morgana-Arsenal`.

**Camelot** is a new **public** repository that serves as the community hub, documentation home, and support channel for the entire X3M.AI ecosystem. It does NOT contain source code -- only documentation, guides, templates, and community infrastructure.

The Arthurian theme is intentional:
- **Merlino** (Merlin) = intelligence, analysis, wisdom
- **Morgana** (Morgan le Fay) = dark arts, offensive operations, Red Team
- **Camelot** = the kingdom that unites them both

### Key URLs

- **Merlino Add-in:** `https://merlino-addin.pages.dev`
- **Merlino Website:** `https://merlino.x3m.ai`
- **X3M.AI Website:** `https://x3m.ai`
- **Morgana Arsenal repo:** `https://github.com/x3m-ai/Morgana-Arsenal`
- **GitHub org:** `x3m-ai`

### Company Info

- **Company:** X3M.AI Ltd
- **Founder:** Nino Crudele
- **Contact (paying customers only):** support@x3m.ai
- **License for Merlino:** Free, distributed under EULA (End User License Agreement)

---

## STEP 1: Create the Repository

Create a new **public** repository on GitHub:

- **Organization:** `x3m-ai`
- **Repository name:** `Camelot`
- **Description:** `Community hub for Merlino CTI Add-in and Morgana Arsenal Red Team platform -- documentation, guides, and support`
- **Visibility:** Public
- **Initialize with:** README.md
- **License:** MIT
- **Add .gitignore:** None needed

After creation, clone it locally:

```powershell
cd C:\Users\ninoc\repos
git clone https://github.com/x3m-ai/Camelot.git
cd Camelot
```

---

## STEP 2: Create Directory Structure

```
Camelot/
├── README.md
├── LICENSE
├── CONTRIBUTING.md
├── CODE_OF_CONDUCT.md
├── CHANGELOG.md
├── .github/
│   ├── FUNDING.yml
│   ├── ISSUE_TEMPLATE/
│   │   ├── bug_report.md
│   │   ├── feature_request.md
│   │   └── question.md
│   └── DISCUSSION_TEMPLATE/
│       ├── announcements.yml
│       ├── q-and-a.yml
│       ├── ideas.yml
│       └── show-and-tell.yml
├── docs/
│   ├── merlino/
│   │   ├── img/
│   │   ├── getting-started.md
│   │   └── (user guides will be copied here later)
│   └── morgana/
│       └── getting-started.md
└── assets/
    ├── camelot-banner.png (placeholder)
    └── merlino-logo.png (placeholder)
```

---

## STEP 3: Enable GitHub Discussions

After the repo is created, enable Discussions:

1. Go to `https://github.com/x3m-ai/Camelot/settings`
2. Scroll to "Features"
3. Check **Discussions**
4. Create the following categories:
   - **Announcements** (maintainers only) -- Release notes, updates
   - **Q&A** (question/answer format) -- User questions about Merlino and Morgana
   - **Ideas** (open discussion) -- Feature requests, suggestions
   - **Show and Tell** (open discussion) -- Users share their use cases, dashboards, reports
   - **Troubleshooting** (question/answer format) -- Bug reports, technical issues

---

## STEP 4: Create All Files

### 4.1 README.md (Repository Homepage)

This is the most important file. It IS the homepage of the repo.

```markdown
<div align="center">

# Camelot

### The Kingdom of Cyber Threat Intelligence

**Merlino** (Intelligence) + **Morgana** (Offense) = **Camelot** (Unified CTI Platform)

[![Merlino Add-in](https://img.shields.io/badge/Merlino-Excel%20Add--in-667eea?style=for-the-badge&logo=microsoft-excel&logoColor=white)](https://merlino-addin.pages.dev)
[![Morgana Arsenal](https://img.shields.io/badge/Morgana%20Arsenal-Red%20Team-dc3545?style=for-the-badge&logo=github&logoColor=white)](https://github.com/x3m-ai/Morgana-Arsenal)
[![Community](https://img.shields.io/badge/Community-Discussions-28a745?style=for-the-badge&logo=github&logoColor=white)](https://github.com/x3m-ai/Camelot/discussions)

---

*Built by [X3M.AI](https://x3m.ai) -- Threat Intelligence, Reimagined*

</div>

---

## What Is Camelot?

**Camelot** is the community hub for the X3M.AI cybersecurity ecosystem. It brings together two powerful tools under one roof:

| Tool | What It Does | Where It Lives |
|---|---|---|
| **Merlino** | Excel Add-in for Cyber Threat Intelligence -- MITRE ATT&CK analysis, coverage heatmaps, AI-powered threat review, CVE enrichment, MISP integration | [Install free](https://merlino-addin.pages.dev) |
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

**[Install Merlino](https://merlino-addin.pages.dev)**

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

Merlino is free and built with passion. If it saves you time, consider supporting its development:

[![Sponsor on GitHub](https://img.shields.io/badge/Sponsor-GitHub%20Sponsors-ea4aaa?style=for-the-badge&logo=github-sponsors&logoColor=white)](https://github.com/sponsors/x3m-ai)
[![Ko-fi](https://img.shields.io/badge/Buy%20a%20Coffee-Ko--fi-ff5e5b?style=for-the-badge&logo=ko-fi&logoColor=white)](https://ko-fi.com/x3mai)

Your support helps fund development, infrastructure, and threat intelligence data updates.

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

**[X3M.AI](https://x3m.ai)** | **[Merlino](https://merlino-addin.pages.dev)** | **[Morgana Arsenal](https://github.com/x3m-ai/Morgana-Arsenal)** | **[Discussions](https://github.com/x3m-ai/Camelot/discussions)**

</div>
```

---

### 4.2 CONTRIBUTING.md

```markdown
# Contributing to Camelot

Thank you for your interest in contributing to the X3M.AI Camelot community!

## How to Contribute

### Documentation Improvements

If you find errors, unclear instructions, or missing information in the documentation:

1. Open a [Discussion](https://github.com/x3m-ai/Camelot/discussions) describing the issue
2. Or submit a Pull Request with the fix

### Share Your Work

We love seeing how the community uses Merlino and Morgana:

- Post in [Show and Tell](https://github.com/x3m-ai/Camelot/discussions/categories/show-and-tell)
- Share your threat profiles, reports, dashboards, or custom templates
- Describe your workflow and what worked well

### Feature Ideas

Have an idea for Merlino or Morgana? Post it in [Ideas](https://github.com/x3m-ai/Camelot/discussions/categories/ideas) with:

- A clear description of the feature
- The problem it solves
- How you envision it working

### Bug Reports

Found a bug? Post in [Troubleshooting](https://github.com/x3m-ai/Camelot/discussions/categories/troubleshooting) with:

- Steps to reproduce
- Expected vs actual behavior
- Your environment (Excel version, OS, browser)
- Screenshots if applicable

## Code of Conduct

All participants are expected to follow our [Code of Conduct](CODE_OF_CONDUCT.md). Be respectful, constructive, and professional.

## Become a Contributor

We are actively looking for people who want to help build the future of open CTI tooling. You do not need to be a senior developer -- enthusiasm and willingness to learn are what matter most.

**Areas where we need help:**

- **TypeScript / React** -- Merlino taskpanes, UI components, Excel API integrations
- **Python** -- Morgana Arsenal plugins, Caldera agents and abilities
- **CTI Analysis** -- Threat profiles, MITRE ATT&CK mappings, use case documentation
- **Red Team / Purple Team** -- Adversary emulation testing, operation design, attack chain validation
- **Detection Engineering** -- Sentinel rules, Defender policies, detection gap analysis
- **Technical Writing** -- User guides, tutorials, translations (especially non-English)
- **UX and Design** -- Taskpane layouts, icons, accessibility, dark theme improvements

**How to get started:**

1. Introduce yourself in [Discussions](https://github.com/x3m-ai/Camelot/discussions) -- tell us what you are interested in
2. Browse existing discussions and issues to find something that excites you
3. For Morgana code contributions, submit PRs to [Morgana Arsenal](https://github.com/x3m-ai/Morgana-Arsenal)
4. For documentation, templates, and guides, submit PRs directly to this repo

## What This Repo Does NOT Accept

- Source code contributions for Merlino (source is private -- but we welcome collaboration via the contributor program above)
- Malware samples or live exploit code
- Content that violates responsible disclosure principles
```

---

### 4.3 CODE_OF_CONDUCT.md

```markdown
# Code of Conduct

## Our Pledge

We are committed to providing a welcoming and professional environment for everyone interested in cyber threat intelligence and security operations.

## Our Standards

**Expected behavior:**

- Be respectful and constructive in all interactions
- Focus on technical merit and practical value
- Share knowledge generously -- we are all here to learn
- Respect responsible disclosure principles
- Use professional language appropriate for a security community

**Unacceptable behavior:**

- Harassment, discrimination, or personal attacks
- Sharing malware, active exploits, or attack tools intended for malicious use
- Violating responsible disclosure (posting zero-days, active campaign IOCs without coordination)
- Spam, self-promotion unrelated to CTI/security, or commercial solicitation
- Publishing sensitive information (credentials, PII, classified data)

## Enforcement

Violations may result in content removal, temporary suspension, or permanent ban from the community at the maintainers' discretion.

## Contact

For Code of Conduct issues, contact the maintainers via [GitHub Discussions](https://github.com/x3m-ai/Camelot/discussions) or email support@x3m.ai.

---

*This Code of Conduct is adapted from the [Contributor Covenant](https://www.contributor-covenant.org/), version 2.1.*
```

---

### 4.4 CHANGELOG.md

```markdown
# Changelog

All notable releases and updates for the X3M.AI ecosystem are documented here.

## Merlino v1.4.0 (February 2026)

### Added
- Cloudflare Pages deployment
- Cloudflare Worker licensing system
- License activation flow (OTP via email)
- Cloud sync for settings
- STIX/Intune large file CDN optimization
- Settings UI redesign (Cloud sync section)

### Integrations
- MITRE ATT&CK Enterprise, Mobile, ICS, Azure
- Microsoft Sentinel, Defender for Office 365, Intune
- Caldera/Morgana Arsenal (Red Team)
- MISP (IOC management)
- OpenAI, Mistral (AI analysis)
- NIST NVD (CVE enrichment)
- Exploit-DB (46,000+ exploits)

---

*For detailed release history, see individual product repositories.*
```

---

### 4.5 .github/FUNDING.yml

This file enables the **Sponsor** button on the GitHub repo page. GitHub reads it automatically.

```yaml
# Funding platforms for Camelot / Merlino / Morgana Arsenal
# GitHub Sponsors -- 0% fee, recommended
github: [x3m-ai]

# Ko-fi -- 0% fee on donations
ko_fi: x3mai

# Other platforms (uncomment if needed later)
# patreon:
# open_collective:
# buy_me_a_coffee:
# custom: ["https://merlino.x3m.ai/donate"]
```

**What this does:**
- Adds a "Sponsor" button (heart icon) at the top of the Camelot repo page
- When clicked, shows a popup with links to GitHub Sponsors and Ko-fi
- Zero configuration needed beyond creating this file

**Prerequisites the owner must complete manually:**
1. **GitHub Sponsors:** Go to `https://github.com/sponsors/x3m-ai` and complete the enrollment (requires Stripe Connect, payout bank account, tax info). Until enrollment is complete, the GitHub Sponsors link will show a "not yet enrolled" page.
2. **Ko-fi:** Create an account at `https://ko-fi.com` with username `x3mai`. Connect PayPal or Stripe for payouts.

---

### 4.6 .github/ISSUE_TEMPLATE/bug_report.md

```markdown
---
name: Bug Report
about: Report a problem with Merlino or Morgana
title: "[BUG] "
labels: bug
assignees: ''
---

**Product:**
- [ ] Merlino (Excel Add-in)
- [ ] Morgana Arsenal (Red Team)

**Describe the bug:**
A clear description of what the problem is.

**Steps to reproduce:**
1. Go to '...'
2. Click on '...'
3. See error

**Expected behavior:**
What you expected to happen.

**Screenshots:**
If applicable, add screenshots.

**Environment:**
- OS: [e.g., Windows 11, macOS 14]
- Excel version: [e.g., Microsoft 365, Excel 2021, Excel Online]
- Merlino version: [e.g., 1.4.0]
- Browser (if Excel Online): [e.g., Chrome 120]
```

---

### 4.7 .github/ISSUE_TEMPLATE/feature_request.md

```markdown
---
name: Feature Request
about: Suggest a new feature or improvement
title: "[FEATURE] "
labels: enhancement
assignees: ''
---

**Product:**
- [ ] Merlino (Excel Add-in)
- [ ] Morgana Arsenal (Red Team)
- [ ] Both / Ecosystem

**Describe the feature:**
A clear description of what you would like.

**Problem it solves:**
What problem or limitation does this address?

**Proposed solution:**
How do you envision this working?

**Alternatives considered:**
Any alternative approaches you have thought about.
```

---

### 4.8 .github/ISSUE_TEMPLATE/question.md

```markdown
---
name: Question
about: Ask a question about Merlino or Morgana
title: "[QUESTION] "
labels: question
assignees: ''
---

**Note:** For faster community responses, consider posting in [Discussions Q&A](https://github.com/x3m-ai/Camelot/discussions/categories/q-a) instead.

**Product:**
- [ ] Merlino (Excel Add-in)
- [ ] Morgana Arsenal (Red Team)

**Your question:**
Describe your question clearly.

**What you have tried:**
Any steps you have already taken.

**Environment:**
- OS: [e.g., Windows 11]
- Excel version: [e.g., Microsoft 365]
- Merlino version: [e.g., 1.4.0]
```

---

### 4.9 .github/DISCUSSION_TEMPLATE/announcements.yml

```yaml
title: "[Announcement] "
labels: []
body:
  - type: markdown
    attributes:
      value: |
        Official announcements from the X3M.AI team about Merlino, Morgana Arsenal, and the Camelot community.
```

---

### 4.10 .github/DISCUSSION_TEMPLATE/q-and-a.yml

```yaml
title: "[Q&A] "
labels: []
body:
  - type: dropdown
    id: product
    attributes:
      label: Product
      description: Which product is this question about?
      options:
        - Merlino (Excel Add-in)
        - Morgana Arsenal (Red Team)
        - Both / General
    validations:
      required: true
  - type: textarea
    id: question
    attributes:
      label: Your Question
      description: Describe your question clearly. Include steps you have already tried.
      placeholder: I am trying to... but...
    validations:
      required: true
  - type: textarea
    id: environment
    attributes:
      label: Environment
      description: Your setup details (optional but helpful)
      placeholder: |
        OS: Windows 11
        Excel: Microsoft 365
        Merlino: v1.4.0
    validations:
      required: false
```

---

### 4.11 .github/DISCUSSION_TEMPLATE/ideas.yml

```yaml
title: "[Idea] "
labels: []
body:
  - type: dropdown
    id: product
    attributes:
      label: Product
      description: Which product is this idea for?
      options:
        - Merlino (Excel Add-in)
        - Morgana Arsenal (Red Team)
        - Both / Ecosystem
    validations:
      required: true
  - type: textarea
    id: idea
    attributes:
      label: Your Idea
      description: Describe the feature or improvement you would like to see.
    validations:
      required: true
  - type: textarea
    id: problem
    attributes:
      label: Problem It Solves
      description: What problem or limitation does this address?
    validations:
      required: false
```

---

### 4.12 .github/DISCUSSION_TEMPLATE/show-and-tell.yml

```yaml
title: "[Show] "
labels: []
body:
  - type: textarea
    id: showcase
    attributes:
      label: What are you sharing?
      description: Tell us about your use case, dashboard, report, threat profile, or workflow. Screenshots welcome!
    validations:
      required: true
  - type: dropdown
    id: product
    attributes:
      label: Products Used
      description: Which tools did you use?
      multiple: true
      options:
        - Merlino (Excel Add-in)
        - Morgana Arsenal (Red Team)
        - MISP
        - Microsoft Sentinel
        - AI Provider (OpenAI, Mistral, etc.)
    validations:
      required: false
```

---

### 4.13 docs/merlino/getting-started.md

```markdown
# Getting Started with Merlino

Merlino is a free Microsoft Excel Add-in for Cyber Threat Intelligence professionals. This guide gets you up and running in 5 minutes.

## Installation

1. Open Microsoft Excel (Desktop or Web)
2. Go to **Insert** > **Add-ins** > **Get Add-ins**
3. Search for **Merlino** or install directly from: **[merlino-addin.pages.dev](https://merlino-addin.pages.dev)**
4. The Merlino ribbon tab appears in Excel

## First Steps

1. Click **Templates** in the Merlino ribbon and load the **Enterprise** template
2. Click **Sources** and import **Techniques**, **Groups**, **Software**, and **Campaigns**
3. Go to the **Groups** sheet and set `Pick = TRUE` on the threat groups relevant to your organization
4. Open **Runbooks** and run **Include Picks in Catalogue**
5. Run **Update Core** + **Smart View** to generate your coverage heatmap
6. Explore the **Main Coverage** sheet -- your prioritized ATT&CK matrix

## Learn More

For a complete walkthrough with six APT groups (APT28, APT29, APT33, APT39, APT42, MuddyWater), see the full User Guide -- Lab 01.

## Get Help

- **[Community Discussions](https://github.com/x3m-ai/Camelot/discussions)** -- Ask questions, get answers
- **[Troubleshooting](https://github.com/x3m-ai/Camelot/discussions/categories/troubleshooting)** -- Report issues

## Requirements

- Microsoft Excel (Microsoft 365, Excel 2021, or Excel Online)
- Windows 10/11 or macOS (for Desktop)
- Any modern browser (for Excel Online)
- Internet connection (for data imports and AI features)
```

---

### 4.14 docs/morgana/getting-started.md

```markdown
# Getting Started with Morgana Arsenal

Morgana Arsenal is X3M.AI's fork of MITRE Caldera, enhanced for integration with Merlino.

## Installation

See the [Morgana Arsenal repository](https://github.com/x3m-ai/Morgana-Arsenal) for installation and setup instructions.

## Integration with Merlino

Once Morgana is running:

1. In Merlino, go to **Settings** and enter your Morgana server URL and API key
2. Build your threat profile in Merlino (import data, select groups, run analysis)
3. Click **Tests and Operations** > **Synchronize Catalogue** to map techniques to Caldera abilities
4. Click **Synchronize Morgana** to automatically create adversary profiles and operations on your Morgana server
5. Open Morgana and launch operations -- everything is pre-configured

For a complete walkthrough, see User Guide -- Lab 03: Red Team Testing with Morgana Arsenal.
```

---

## STEP 5: Repository Settings

After creating all files, configure these GitHub settings:

### Topics (Tags)

Add these topics to the repo for discoverability:

```
mitre-attack, cyber-threat-intelligence, cti, red-team, caldera, excel-addin, 
threat-profiling, adversary-emulation, misp, siem, sentinel, detection-engineering,
attack-framework, security-operations, soc
```

### About Section

- **Description:** `Community hub for Merlino CTI Add-in and Morgana Arsenal Red Team platform -- documentation, guides, and support`
- **Website:** `https://merlino.x3m.ai`
- Check: Releases, Packages = unchecked
- Check: Discussions = checked

### Branch Protection

- Default branch: `main`
- No protection rules needed (it is a docs repo)

---

## STEP 6: Update the Merlino User Guide Footer

Once Camelot is live, the footer of the Merlino User Guide should be updated from:

```
*For additional help, use Anacleto within any taskpane or contact support@x3m.ai.*
```

To:

```
*For additional help, use Anacleto within any taskpane or visit the [Camelot community](https://github.com/x3m-ai/Camelot/discussions).*
```

This change needs to be made in the Merlino repo (private), NOT in this Camelot repo.

---

## STEP 7: First Announcement

After everything is set up, create the first Discussion post in the **Announcements** category:

**Title:** Welcome to Camelot -- The X3M.AI Community Hub

**Body:**

```markdown
Welcome to **Camelot** -- the official community hub for the X3M.AI cybersecurity ecosystem!

## What is this place?

Camelot brings together the community around two tools:

- **Merlino** -- Free Excel Add-in for Cyber Threat Intelligence ([install here](https://merlino-addin.pages.dev))
- **Morgana Arsenal** -- Red Team adversary emulation platform ([repo here](https://github.com/x3m-ai/Morgana-Arsenal))

## How to use Discussions

- **Q&A** -- Ask questions about Merlino or Morgana. The community and maintainers will answer.
- **Ideas** -- Suggest features, improvements, or integrations you would like to see.
- **Show and Tell** -- Share your threat profiles, dashboards, reports, and workflows!
- **Troubleshooting** -- Report bugs or technical issues.

## Getting Started

If you are new to Merlino, start with the [Getting Started guide](https://github.com/x3m-ai/Camelot/blob/main/docs/merlino/getting-started.md).

We are excited to build this community together. Welcome aboard!

-- The X3M.AI Team
```

---

## SUMMARY CHECKLIST

- [ ] Create `x3m-ai/Camelot` repo on GitHub (public, MIT license)
- [ ] Clone locally
- [ ] Create directory structure
- [ ] Create README.md (homepage with badges, product descriptions, links)
- [ ] Create CONTRIBUTING.md
- [ ] Create CODE_OF_CONDUCT.md
- [ ] Create CHANGELOG.md
- [ ] Create .github/FUNDING.yml (enables Sponsor button on repo)
- [ ] Create .github/ISSUE_TEMPLATE/bug_report.md
- [ ] Create .github/ISSUE_TEMPLATE/feature_request.md
- [ ] Create .github/ISSUE_TEMPLATE/question.md
- [ ] Create .github/DISCUSSION_TEMPLATE/announcements.yml
- [ ] Create .github/DISCUSSION_TEMPLATE/q-and-a.yml
- [ ] Create .github/DISCUSSION_TEMPLATE/ideas.yml
- [ ] Create .github/DISCUSSION_TEMPLATE/show-and-tell.yml
- [ ] Create docs/merlino/getting-started.md
- [ ] Create docs/morgana/getting-started.md
- [ ] Enable GitHub Discussions in repo settings
- [ ] Add topics/tags for discoverability
- [ ] Set repo description and website URL
- [ ] Commit and push all files
- [ ] Post first Announcement discussion
- [ ] (Later, in Merlino repo) Update user guide footer
- [ ] (Manual) Enroll `x3m-ai` org in GitHub Sponsors (requires Stripe Connect + tax info)
- [ ] (Manual) Create Ko-fi account `x3mai` and connect PayPal or Stripe

---

**END OF INSTRUCTIONS**
