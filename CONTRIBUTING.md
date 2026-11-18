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
- **Python** -- community content, parsers, and approved Morgana-facing utilities (product code is handled in the product repositories)
- **CTI Analysis** -- Threat profiles, MITRE ATT&CK mappings, use case documentation
- **Red Team / Purple Team** -- Adversary emulation testing, operation design, attack chain validation
- **Detection Engineering** -- Sentinel rules, Defender policies, detection gap analysis
- **Technical Writing** -- User guides, tutorials, translations (especially non-English)
- **UX and Design** -- Taskpane layouts, icons, accessibility, dark theme improvements

**How to get started:**

1. Introduce yourself in [Discussions](https://github.com/x3m-ai/Camelot/discussions) -- tell us what you are interested in
2. Browse existing discussions and issues to find something that excites you
3. For documentation, templates, labs, and curated content, submit PRs directly to this repo
4. For Morgana server/agent or Merlino product code, do not submit PRs to Camelot; contact the maintainers to discuss the appropriate product repository

## Repository Boundaries

| Repository | What it contains |
|---|---|
| **Camelot** | Public documentation, labs, templates, community data, curated Excalibur content |
| **Merlino** | Merlino product source (private) |
| **Morgana** | Morgana server/agent product source; not the Camelot documentation repo |
| **Morgana Arsenal** | Separate content/community project; not the Morgana server or agent source |

Do not treat these repositories as interchangeable, and do not move product source into Camelot to satisfy a documentation link.

## What This Repo Does NOT Accept

- Source code contributions for Merlino (source is private -- but we welcome collaboration via the contributor program above)
- Malware samples or live exploit code
- Content that violates responsible disclosure principles
