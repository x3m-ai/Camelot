# Merlino User Guide -- Complete Walkthrough -- Create Organization Threat Profile

**Product:** Merlino v1.4.0  
**Publisher:** X3M.AI Ltd  
**Date:** March 2026  
**Audience:** End users, security analysts, and Microsoft Marketplace reviewers

---

## Table of Contents

1. [Introduction](#1-introduction)
2. [Getting Started -- Settings Configuration](#2-getting-started----settings-configuration)
3. [Step 1 -- Load a Template](#3-step-1----load-a-template)
4. [Step 2 -- Import Data Sources](#4-step-2----import-data-sources)
5. [Step 3 -- Run "Update Core" Runbook](#5-step-3----run-update-core-runbook)
6. [Step 4 -- Select Threat Groups (Pick = TRUE)](#6-step-4----select-threat-groups-pick--true)
7. [Step 5 -- Run "Include Picks in Catalogue"](#7-step-5----run-include-picks-in-catalogue)
8. [Step 6 -- Run "Update Core" and "Smart View"](#8-step-6----run-update-core-and-smart-view)
9. [Step 7 -- Explore the Main Coverage View](#9-step-7----explore-the-main-coverage-view)
10. [Step 8 -- Use Insights on a Technique](#10-step-8----use-insights-on-a-technique)
11. [Step 9 -- Generate an Adaptive Report](#11-step-9----generate-an-adaptive-report)
12. [Step 10 -- Explore Attack Knowledge Graph](#12-step-10----explore-attack-knowledge-graph)
13. [Step 11 -- Analyze CrossPick Coverage Across Sheets](#13-step-11----analyze-crosspick-coverage-across-sheets)
14. [Step 12 -- CVE Enrichment](#14-step-12----cve-enrichment)
15. [Step 13 -- Tests & Operations (Caldera/Morgana)](#15-step-13----tests--operations-calderamorgana)
16. [Step 14 -- IOC Management and MISP Integration](#16-step-14----ioc-management-and-misp-integration)
17. [Step 15 -- AI-Powered Analysis](#17-step-15----ai-powered-analysis)
18. [Anacleto -- Contextual Documentation Assistant](#18-anacleto----contextual-documentation-assistant)
19. [Logs Taskpane](#19-logs-taskpane)
20. [Summary of Ribbon Layout](#20-summary-of-ribbon-layout)

---

## 1. Introduction

**Merlino** is a Microsoft Excel add-in designed for Cyber Threat Intelligence (CTI) professionals. It integrates MITRE ATT&CK, public vulnerability databases, AI analysis, Red Team emulation tools, and threat intelligence platforms directly into your Excel workflow.

This guide walks you through a complete end-to-end workflow: from loading a blank template to producing a fully analyzed threat coverage matrix with AI-enriched insights.

### Why Excel -- The Most Powerful Platform in the World

Merlino is built on Microsoft Excel for a reason. Excel is the most widely used professional tool on the planet, and by running inside it, Merlino inherits the **entire extensibility of the Excel ecosystem**:

- **Native data integration** -- Excel connects natively to virtually any data source: SQL databases, REST APIs, SharePoint, Power Query, CSV, JSON, XML, ODBC, and hundreds more. Any data your organization already has can flow directly into your Merlino workbook without intermediate tools or custom connectors.
- **Custom formulas and calculations** -- You can apply your own Excel formulas alongside Merlino's automation. Build custom scoring models, weighted risk calculations, conditional formatting rules, or any analytical logic you need -- Excel's formula engine is yours to use.
- **Python in Excel** -- Microsoft's integrated Python support means you can run Python scripts directly inside your spreadsheet. Run statistical analysis, machine learning models, or custom data transformations without leaving Excel.
- **AI-powered Excel (Copilot in Excel)** -- Microsoft's AI agent mode in Excel can analyze, summarize, and reason about your Merlino workbook data using natural language. Ask questions about your threat profile and get immediate AI-driven answers.
- **The spreadsheet principle** -- A spreadsheet provides a dimensional visibility that no other reporting system can match. You see all your data at once, navigate across sheets, compare columns side by side, filter on the fly, and drill into any cell. Dashboards and PDF reports are static snapshots; a spreadsheet is a living, interactive analytical surface.
- **The workbook IS the report** -- The Merlino workbook itself is a comprehensive report. It contains all your data, all your analysis, all your coverage matrices, and all your insights in a single portable file. You can share it, archive it, version it, and reopen it months later with full fidelity.
- **Zero learning curve** -- Everyone knows Excel. CTI analysts, SOC operators, CISOs, board members, compliance officers -- they all use it daily. Merlino requires no special training beyond knowing what you already know about Excel.
- **The executive's preferred tool** -- Excel is the number-one tool for debriefing high-level stakeholders and decision-makers. When a CISO presents to the board, when a security architect presents risk assessments, when a threat intelligence lead presents coverage gaps -- more often than not, the data lives in Excel. Merlino puts your entire CTI analysis exactly where decisions are made.
- **Your existing sheets, integrated** -- Cybersecurity professionals already maintain extensive Excel workbooks with their own data, trackers, and analysis. With Merlino, you can integrate those existing sheets directly into the analytical engine. Your data becomes part of the Catalogue, the coverage analysis, and the reporting -- no migration required.

This combination makes Merlino an extraordinarily versatile instrument. It is not a closed tool with a fixed interface -- it is an **open platform** that grows with your data, your formulas, your Python scripts, your AI queries, and your analytical creativity.

As Satya Nadella, CEO of Microsoft, has said: *"You can do anything with Excel."*

[![Satya Nadella on Excel](https://img.youtube.com/vi/KSqYSKwyLpM/maxresdefault.jpg)](https://www.youtube.com/watch?v=KSqYSKwyLpM "Satya Nadella: You can do anything with Excel")

*Click the image above to watch Satya Nadella talk about the power of Excel.*

### Merlino Is a Methodology, Not Just a Product

Merlino is not a conventional security tool with a fixed workflow. It is a **methodology** -- a flexible, open-ended framework that adapts to how **you** think about threats.

At the heart of Merlino sits the **Catalogue**: a single unified table where you collect the entities you want to analyze. What makes the Catalogue so powerful is that it accepts **any combination of data sources**: threat groups, software, campaigns, Microsoft Sentinel detection rules, Darktrace rules, Intune policies, Red Team test results, or any other entity that carries ATT&CK technique codes. Merlino treats all of these inputs uniformly and produces a single, coherent **Techniques Coverage** analysis on the Main Coverage matrix.

This means there is **no single "right" way** to use Merlino. You might build a Catalogue that contains only threat groups targeting your industry. Another analyst might mix Sentinel detection rules with Red Team test results to measure detection coverage against adversary emulation. A third user might combine groups, campaigns, and software to map the full TTP landscape of a specific threat actor. Every combination is valid, and every combination produces a meaningful, actionable analysis.

**There is no universal way to use Merlino -- there is YOUR way.** Your approach can be completely different from someone else's, and both are equally valid. This creative freedom is what makes Merlino an extremely powerful and unique instrument: it bends to your analytical thinking, not the other way around.

### Build Your Own Templates and Integrate Your Own Data

Merlino ships with ready-made templates (Enterprise, Mobile, ICS, Azure), but you are not limited to them. You can **create your own custom Merlino template** or **integrate your existing Excel sheets** -- complete with your own data, formulas, and domain-specific information -- directly into Merlino's analytical engine.

All you need to do is follow a few simple structural rules (standard column conventions such as **Pick**, **CrossPick**, and **TCodes**), and Merlino will seamlessly incorporate your sheets into all of its logics: coverage analysis, Smart View heatmaps, Catalogue inclusion, CrossPick calculations, Insights, Reports, and everything else.

This means you can build a fully personalized Merlino workbook tailored to your organization, your data, and your analytical needs -- and still leverage the entire power of Merlino's automation, visualization, and AI capabilities on top of it. The possibilities are limited only by your creativity. A dedicated laboratory will walk you through the process step by step.

### How Merlino Works -- The Pick System

Merlino's core interaction model is based on the **Pick system**:

- Data is imported into Excel tables (Threat Groups, Techniques, Software, Campaigns, etc.)
- You mark rows with **Pick = TRUE** to select the entities you care about
- Merlino filters, correlates, and visualizes only the selected data
- The **CrossPick** percentage column shows how strongly each technique is associated with your selections

This pattern repeats across all tables and features in Merlino.

![Merlino Ribbon Overview](img/01-merlino-ribbon-overview.png)

*The Merlino ribbon in Excel showing the three tab groups (Operations, Logics, Help) with all available buttons.*

---

## 2. Getting Started -- Settings Configuration

Before using Merlino's features, review the Settings taskpane to configure integrations and preferences.

**How to open:** Click **Settings** in the **Help** group on the Merlino ribbon.

![Settings Taskpane Overview](img/02-settings-taskpane-overview.png)

*The Settings taskpane fully open, showing the version badge at the top and all configuration sections listed below.*

### 2.1 Local Backup (Export / Import Settings)

At the top of Settings you will find **Export Settings** and **Import Settings** buttons. These allow you to:

- **Export Settings** -- Save all your current configurations (AI providers, Morgana URL, MISP settings, theme, preferences) to a JSON file on your computer.
- **Import Settings** -- Restore all configurations from a previously exported JSON file.

This is critical because clearing the Office WebView2 cache (for troubleshooting) deletes all localStorage data. Always export your settings before clearing the cache.

![Settings Local Backup](img/03-settings-local-backup.png)

*The Local Backup section showing the Export and Import buttons side by side.*

### 2.2 AI Provider Configuration

This section lets you configure one or more AI providers for use with the AI Assistant taskpane.

Each provider entry requires:

| Field | Description |
|---|---|
| **Provider** | The AI service (OpenAI, Mistral, AWS Bedrock, etc.) |
| **Model Version** | The specific model (e.g., gpt-4o, mistral-large-latest) |
| **API Key** | Your personal API key from the provider |
| **Secret Key (AWS)** | Only for AWS Bedrock |
| **Region (AWS)** | Only for AWS Bedrock |
| **Endpoint (Optional)** | Custom endpoint URL if using a self-hosted model |
| **Default** | Mark one provider as the default for AI operations |

Click **Add Provider** to add a new row, fill in the fields, then click **Save AI Configs**.

![Settings AI Configuration](img/04-settings-ai-config.png)

*The AI Provider Configuration table with providers configured, showing API key fields and the default selection.*

### 2.3 Morgana Arsenal Configuration (Caldera Red Team)

If you have a Caldera/Morgana Red Team server, enter its HTTPS URL here.

- **Morgana Arsenal Server URL** -- e.g., `https://192.168.124.133`
- Click **Check Morgana** to test the connection
- Click **Save Morgana** to persist the URL

This is required for the Agents, Tests & Operations, and Red Team features.

![Settings Morgana Configuration](img/05-settings-morgana.png)

*The Morgana Arsenal Configuration section with a URL entered and connection status.*

### 2.4 MISP Configuration

If you have a MISP threat intelligence server, configure it here:

- **MISP Server URL** -- e.g., `https://misp.local`
- **MISP API Key** -- Your MISP automation key
- Click **Check MISP** to test the connection
- Click **Save MISP** to persist

This is required for the IOC taskpane's MISP integration features.

![Settings MISP Configuration](img/06-settings-misp.png)

*The MISP Configuration section with URL and API key fields.*

### 2.5 Backup & Restore

This section provides additional backup functionality:

- **Export All Settings** -- Downloads a comprehensive JSON backup of all configs
- **Import Settings** -- Restore from a backup file
- **Restore from Auto-Backup** -- Merlino automatically saves a backup to OfficeRuntime.storage every time you save settings. If your cache is cleared, Merlino will try to auto-restore on next load. You can also manually trigger this restore.

![Settings Backup & Restore](img/07-settings-backup-restore.png)

*The Backup & Restore section showing the three buttons and the last backup timestamp info.*

### 2.6 UI Preferences

Customize notification behavior:

- **Info Messages Duration** -- How long success/info toast messages stay visible (default: 12 seconds)
- **Error Messages Duration** -- How long error toast messages stay visible (default: 20 seconds)

![Settings UI Preferences](img/08-settings-ui-preferences.png)

*The UI Preferences section with the two duration input fields.*

### 2.7 Theme Customization

Merlino supports full theme customization with seven configurable colors:

| Color | Purpose |
|---|---|
| Background Taskpanes | Main body background |
| Background Panels | Panels and card backgrounds |
| Background Tables | Data table backgrounds |
| Text Color | Primary text |
| Accent Color | Highlights, buttons, interactive elements |
| Border Color | Borders and dividers |
| Secondary Text | Hints and descriptions |

Each color has a color picker and a hex input. Click **Save Theme** to apply. Changes take effect immediately in the current taskpane and in other taskpanes when they are reopened.

![Settings Theme Customization](img/09-settings-theme.png)

*The Theme Customization section showing all seven color rows with color pickers.*

### 2.8 Troubleshooting

If Merlino is not loading correctly or taskpanes appear blank, use the **Download Cache Clear Script** button. This downloads a batch file that:

1. Closes all Office applications
2. Clears the Office add-in cache folders
3. Relaunches Excel

**Important:** Save all your work and export your settings before running this tool.

![Settings Troubleshooting](img/10-settings-troubleshooting.png)

*The Troubleshooting section with the "Download Cache Clear Script" button and the warning text.*

---

## 3. Step 1 -- Load a Template

The first step in any Merlino workflow is loading a template that creates the required Excel sheets and tables.

**How to open:** Click **Templates** in the **Operations** group on the Merlino ribbon.

### Available Templates

| Template | Description |
|---|---|
| **Enterprise** | MITRE ATT&CK Enterprise matrix -- the most commonly used template for general threat analysis |
| **Mobile** | MITRE ATT&CK Mobile matrix |
| **ICS** | MITRE ATT&CK Industrial Control Systems matrix |
| **Azure** | Azure-specific template for cloud threat analysis |

### How to Load

1. Open the Templates taskpane
2. Click **Load Template** on the desired template (e.g., **Enterprise**)
3. Merlino creates multiple sheets in the workbook:
   - **Techniques** -- All MITRE ATT&CK techniques
   - **Groups** -- Threat groups / actors
   - **Software** -- Malware and tools
   - **Campaigns** -- Known campaigns
   - **Data Sources** -- Detection data sources
   - **Catalogue** -- Your curated selection of entities
   - **Tests** -- Red Team test abilities
   - **Adversaries** -- Red Team adversary profiles
   - **Operations** -- Red Team operation plans
   - **Main Coverage** -- The ATT&CK technique coverage heatmap
   - **AI** -- AI analysis prompts and results
   - Additional supporting sheets

Each sheet contains a structured Excel table with standardized columns including **Pick** (Boolean), **CrossPick** (percentage), and **TCodes** (technique codes).

![Templates Taskpane](img/11-templates-taskpane.png)

*The Templates taskpane showing the available template cards with their Load Template buttons.*

![Template Loaded Sheets](img/12-template-loaded-sheets.png)

*Excel with multiple sheet tabs visible at the bottom after loading the Enterprise template.*

---

## 4. Step 2 -- Import Data Sources

After loading a template, populate the tables with real threat intelligence data.

**How to open:** Click **Sources** in the **Operations** group on the Merlino ribbon.

> **About this laboratory:** In this guide we will build a threat profile based on **threat groups** that are known to attack organisations in a specific industry sector. This is one of Merlino's core use cases: understanding which ATT&CK techniques your organisation is most exposed to, based on the adversaries that target your vertical. In a subsequent laboratory we will take this further by importing **Microsoft Sentinel detection rules** and comparing your detection coverage against the same threat profile -- see *Merlino User Guide-Lab 02--Microsoft Sentinel Detection Coverage.md*.

### 4.1 Download the STIX Database

Before importing any MITRE data, you must first download the ATT&CK STIX database that Merlino will use as its data source.

In the **ATT&CK STIX Data** section at the top of the Sources taskpane:

1. Select **Enterprise** from the **Domain** dropdown (other options available: Mobile, ICS)
2. Select the **Version** (e.g., 18.1)
3. Click **Download** to fetch the STIX database from the public MITRE GitHub CDN
4. Wait for the **Local Cache Status** to show **Ready**

This downloads and caches the STIX JSON file locally so that all subsequent imports are fast and work offline.

![Sources STIX Data](img/13-sources-stix-data.png)

*The ATT&CK STIX Data section showing the Domain dropdown (Enterprise, Mobile, ICS) and Version selector.*

### 4.2 Import MITRE ATT&CK Data

Once the STIX database is downloaded and ready, use the **Data Type** dropdown to select and import each type of MITRE data individually. Select a data type and click **Import** for each one:

| Data Type | Description |
|---|---|
| **Techniques** | All ATT&CK techniques and sub-techniques with tactic mappings |
| **Groups** | Threat groups / actors with their associated techniques |
| **Campaigns** | Known campaigns with linked techniques and groups |
| **Software** | Malware and tools mapped to techniques |
| **Mitigations** | Security controls and mitigations for techniques |
| **Data Components** | Data sources and components for detection engineering |
| **Detection Strategies** | Detection strategies mapped to techniques |

Import each data type in sequence by selecting it from the dropdown and clicking **Import**. Merlino parses the cached STIX data and populates the corresponding Excel sheet. No credentials are required -- these are public datasets.

![Sources Data Type Import](img/14-sources-data-type-import.png)

*The Data Type dropdown showing all available MITRE data types to import: Techniques, Groups, Campaigns, Software, Mitigations, Data Components, Detection Strategies.*

### 4.3 Import Microsoft Security Sources

In addition to MITRE ATT&CK data, Merlino can import data from Microsoft security products. In this first laboratory we will focus exclusively on building a threat profile from threat groups; in a subsequent laboratory (*Merlino User Guide-Lab 02--Microsoft Sentinel Detection Coverage.md*) we will import Microsoft Sentinel rules to evaluate detection coverage against that same threat profile.

Merlino supports importing data from Microsoft security products such as:

- **Microsoft Sentinel Rules** -- Detection rules mapped to ATT&CK techniques
- **Microsoft Defender for Office (MDO) Policies** -- Security policies mapped to ATT&CK
- **Microsoft Intune Policies** -- Device management policies mapped to techniques

**Important -- Security by Design:** Merlino does **not** integrate directly with Microsoft Graph API or connect to your Microsoft tenant. This is a deliberate strategic security choice: we do not want an Excel add-in to have direct access to your security infrastructure.

Instead, Merlino provides **fully transparent PowerShell scripts** that you download and run independently on your own machine. These scripts:

1. Connect to the Microsoft source (e.g., Sentinel, Defender, Intune) using your own credentials under your full control
2. Export the data in a **catalogue-ready format** that Merlino can import
3. Are plain-text `.ps1` files that you can inspect, audit, and approve before running

This approach gives you:

- **Full transparency** -- you can read every line of the script before executing it
- **No credential exposure** -- Merlino never sees or stores your Microsoft tenant credentials
- **Complete control** -- you decide when and where to run the script, on which machine, and with which permissions
- **Auditability** -- your security team can review and approve the scripts as part of your change management process

To use this workflow:

1. Open the **Sources** taskpane and select the Microsoft source you want to import (e.g., Sentinel, MDO, Intune)
2. Click **Import** -- Merlino automatically downloads the corresponding PowerShell script to your machine
3. Review the script contents to satisfy your security requirements -- it is a plain `.ps1` file you can open in any text editor
4. Run the script in PowerShell -- it will authenticate to the Microsoft service using your credentials and export a catalogue-ready JSON file
5. Back in Merlino, the import process picks up the exported data and loads it into the appropriate Excel sheet, already formatted for Merlino's catalogue structure

![Microsoft Security Sources](img/15-sources-microsoft.png)

*The list of available Microsoft security sources in the Sources taskpane.*

### 4.4 Import CVEs (Last Week)

The Sources taskpane includes a **CVE import** option that queries the public **NIST NVD API** for recently published CVEs (typically the last 7 days).

This populates CVE data that can later be enriched in the CVE Enrichment taskpane.

![Sources CVE Import](img/16-sources-cve-import.png)

*The CVE import option in the Sources taskpane, showing the success notification with the number of CVEs imported.*

### 4.5 Verify the Imported Data

After importing, navigate to the sheet tabs at the bottom of Excel:

- Click the **Threat Groups** tab and verify it contains rows of threat groups (APT28, APT29, Lazarus Group, etc.)
- Click the **Techniques** tab and verify it contains hundreds of ATT&CK techniques
- Each row has **Pick = FALSE** by default and a **TCodes** column with the technique codes

![Groups Sheet Populated](img/17-groups-sheet-populated.png)

*The Groups sheet showing rows of imported threat groups with columns: Pick, CrossPick, TCodes, Name, Description. All Pick values are FALSE.*

---

## 5. Step 3 -- Run "Update Core" Runbook

After importing data, run the **Update Core** runbook to build the initial technique coverage matrix.

**How to open:** Click **Runbooks** in the **Logics** group on the Merlino ribbon.

### What is a Runbook?

Runbooks are automated multi-step workflows that process and correlate data across Merlino's Excel tables. They perform complex operations that would take many manual steps.

### Available Runbooks

| Runbook | Description |
|---|---|
| **Update Core** | Updates core components: cross-references techniques, tests, data sources, and the catalogue. Rebuilds the Main Coverage matrix. |
| **Smart View** | Analyzes Pick column selections across all tables and colors techniques based on TCode frequency analysis. Produces the visual heatmap. |
| **Set All Picks False** | Resets all Pick columns to FALSE across all tables, then runs Smart View to clear the heatmap. |
| **Include Picks in Catalogue** | Copies all rows with Pick = TRUE from Groups, Software, Campaigns, Tests, etc. into the Catalogue -- the central table that drives the entire Techniques Coverage analysis. |
| **Export Analytic Reports** | Generates a self-contained HTML report from the current analysis that can be shared and viewed without Excel or Merlino. |

### Running Update Core

1. Open the Runbooks taskpane
2. Select (check) **Update Core**
3. Click **Execute Selected Runbooks**
4. Wait for the execution to complete -- Merlino processes all imported data and builds the Main Coverage matrix

After completion, navigate to the **Main Coverage** sheet. You will see the ATT&CK technique matrix with columns for each tactic and rows of techniques. At this point, the matrix is empty (no colors) because no threat groups have been selected yet.

![Runbooks Taskpane](img/18-runbooks-taskpane.png)

*The Runbooks taskpane showing all available runbooks with checkboxes. "Update Core" is checked and the "Execute Selected Runbooks" button is visible at the bottom.*

![Main Coverage Empty](img/19-main-coverage-empty.png)

*The Main Coverage sheet after running Update Core for the first time. The ATT&CK matrix structure is visible (tactics as columns, techniques as rows) but no cells are colored yet.*

---

## 6. Step 4 -- Select Threat Groups (Pick = TRUE)

Now select the threat groups you want to analyze. This is the core of the Pick system.

### How to Select Groups

1. Navigate to the **Threat Groups** sheet tab
2. Sort the table by the **Name** column in alphabetical order (A to Z) to make it easier to locate specific groups
3. Find the **Pick** column (first column in the table)
4. Set **Pick = TRUE** for the following groups:
   - **APT28**
   - **APT29**
   - **APT33**
   - **APT39**
   - **APT42**
   - **MuddyWater**

You can find groups quickly by using Excel's built-in filter or Ctrl+F search on the **Name** column.

These six groups represent well-known advanced persistent threat actors with diverse TTPs -- a realistic scenario for an organization assessing its exposure to sophisticated threats.

![Groups Pick TRUE](img/20-groups-pick-true.png)

*The Groups sheet with Pick = TRUE set on the six listed APT groups. Surrounding rows show Pick = FALSE for contrast.*

---

## 7. Step 5 -- Run "Include Picks in Catalogue"

After selecting your threat groups, bring them into the Catalogue for analysis. This step is where the real power of Merlino becomes visible.

### The Catalogue -- The Heart of Merlino

The **Catalogue** is the central engine of every analysis in Merlino. It is a single unified table that feeds the **Techniques Coverage** column on the Main Coverage matrix. Everything that ends up in the Catalogue directly shapes the coverage heatmap you will explore in the next steps.

What makes the Catalogue uniquely powerful is that it is **source-agnostic**. You can import into it:

- **Threat groups** (as we are doing in this laboratory)
- **Microsoft Sentinel detection rules**
- **Microsoft Defender for Office (MDO) policies**
- **Microsoft Intune policies**
- **Darktrace or other third-party detection rules**
- **Campaigns**
- **Software / malware**
- **Red Team test results** from Caldera/Morgana
- **Any combination of the above, mixed together**

Merlino treats every entry in the Catalogue in exactly the same way: it reads the ATT&CK technique codes (TCodes) carried by each row and builds a unified coverage picture. It does not matter whether a technique code comes from a threat group, a Sentinel rule, or a Red Team test -- they are all equal citizens in the analysis.

This is one of Merlino's greatest strengths and the reason we call it a **methodology**, not just a security product. There is no single predetermined workflow. In this laboratory we are building a threat profile from six APT groups, but another analyst might combine Sentinel rules with threat groups to compare detection coverage against adversary capabilities. A third user might mix campaigns, software, and Intune policies to evaluate a completely different dimension of security posture. Every combination produces a valid, meaningful result.

**The Catalogue is your canvas. What you put on it is entirely your choice.**

### How to Run

1. Open the **Runbooks** taskpane
2. Select (check) **Include Picks in Catalogue**
3. Click **Execute Selected Runbooks**

Merlino scans the tables configured in **CrossPickTables** (Groups, Software, Campaigns, Tests, Adversaries, Operations) for any row where Pick = TRUE, and inserts those rows into the Catalogue table.

After execution:

- Navigate to the **Catalogue** sheet
- You will see all six selected threat groups listed
- Each row carries its **TCodes** -- the MITRE ATT&CK technique codes associated with that group

![Catalogue Populated](img/21-catalogue-populated.png)

*The Catalogue sheet showing the six APT groups that were picked. The TCodes column shows comma-separated technique codes.*

---

## 8. Step 6 -- Run "Update Core" and "Smart View"

Now run both **Update Core** and **Smart View** together to build the full coverage analysis.

### How to Run

1. Open the **Runbooks** taskpane
2. Select (check) **Update Core** AND **Smart View**
3. Click **Execute Selected Runbooks**
4. Merlino executes them in sequence:
   - **Update Core** recalculates all cross-references between the Catalogue entries and the technique tables
   - **Smart View** analyzes the frequency of each technique code across all picked entities and applies color coding to the Main Coverage matrix

### What Happens Behind the Scenes

Merlino performs **advanced statistical analysis** across the entire MITRE ATT&CK dataset, correlating your selected entities with thousands of technique mappings, relationships, and threat intelligence data points. The result is a prioritized, color-coded coverage matrix:

- **Darker/more intense colors** = higher-risk techniques that demand immediate attention
- **Lighter colors** = lower-priority techniques with less exposure
- **No color** = techniques not relevant to your current threat profile

![Runbooks Update Core and Smart View](img/22-runbooks-update-core-smartview.png)

*The Runbooks taskpane with both "Update Core" and "Smart View" checked, ready to execute.*

![Main Coverage Colored](img/23-main-coverage-colored.png)

*The Main Coverage sheet after Smart View execution. The ATT&CK matrix shows colored cells with different intensities reflecting CrossPick percentages. Tactic columns (Initial Access, Execution, Persistence, etc.) are visible as headers.*

---

## 9. Step 7 -- Explore the Main Coverage View

The **Main Coverage** sheet is the centerpiece of Merlino's analysis. It presents the MITRE ATT&CK matrix as a visual heatmap -- but before diving into the matrix itself, it is essential to understand the **four summary columns** that run across the top of the sheet. These columns are the executive dashboard of your entire security posture.

### The Four Coverage Columns

At the top of the Main Coverage sheet, each tactic column header is accompanied by four key metrics. Together, they tell you the full story of your organization's threat exposure, detection readiness, and testing maturity.

#### 1. Technique Coverage

The **Technique Coverage** column shows the **percentage of ATT&CK techniques that are present in your current threat profile**. In this laboratory, since we built a Catalogue from six APT groups, Technique Coverage reflects which techniques those threat actors are known to use.

In practical terms: this column answers the question **"Which attack techniques should my organization worry about?"** A technique that appears in your coverage means that at least one of your selected threat actors has been observed using it in real-world operations, according to MITRE ATT&CK intelligence.

At this stage of the laboratory, the Technique Coverage column is displaying the full attack surface that your organization needs to address -- every technique flagged here is a potential attack vector that adversaries targeting your sector have used before.

#### 2. CrossPick

The **CrossPick** column is where Merlino goes beyond simple presence/absence and adds **prioritization intelligence**. CrossPick shows a **percentage value that represents how important and relevant each technique is within your specific threat profile**.

The CrossPick percentage is calculated based on how many of your selected Catalogue entities share that technique. A higher CrossPick value means that multiple threat actors in your profile use the same technique -- which makes it significantly more likely to be encountered in a real attack against your organization.

**How to interpret CrossPick values:**

- **80-100%** -- Critical priority. Almost all of your profiled threat actors use this technique. This is virtually guaranteed to appear in an attack chain targeting your organization. Invest heavily in detection and mitigation.
- **60-80%** -- High priority. A strong majority of your threat actors share this technique. For example, a technique like **Exploitation for Client Execution (T1203)** with a CrossPick above 60% tells you that this attack method is a common denominator across your adversaries -- it **will almost certainly be part of the kill chain** in a real-world intrusion targeting your organization.
- **30-60%** -- Medium priority. Several actors use this technique. Worth addressing but not the most urgent.
- **Below 30%** -- Lower priority in the context of your current profile, though still worth monitoring.

**What Merlino is telling you:** The combination of Technique Coverage and CrossPick means that Merlino is not just showing you **which** techniques your organization should care about -- it is also telling you **which ones matter the most**. This is the difference between a flat list of threats and an actionable, prioritized defense roadmap. The highest CrossPick techniques are where your detection engineering, security controls, and incident response playbooks should focus first.

#### 3. Data Components Coverage

The **Data Components Coverage** column addresses a fundamental question in detection engineering: **"Do we have the right log sources and telemetry to actually detect these techniques?"**

MITRE ATT&CK maps each technique to one or more **Data Components** -- the specific types of telemetry or log data that are needed to detect that technique. For example, detecting T1059 (Command and Scripting Interpreter) requires data components such as Process Creation events, Command Execution logs, and Script Execution telemetry.

The Data Components Coverage percentage shows **how many of the required data components you have mapped in your environment**. This column helps you identify critical visibility gaps: if a technique has a high CrossPick (meaning it is very likely to be used against you) but a low Data Components Coverage (meaning you lack the log sources to detect it), you have found a **blind spot** that needs immediate remediation.

In practice, this column drives your **log source strategy**: which SIEM data sources to onboard, which endpoint telemetry to enable, and which network monitoring capabilities to deploy.

#### 4. Tests Coverage

The **Tests Coverage** column tracks the **percentage of completion and success of Red Team attack tests and adversary emulation exercises** conducted through **Morgana Arsenal** (Merlino's integrated Caldera fork).

When Merlino is connected to a Morgana Arsenal server, it synchronizes in real time with the Red Team testing infrastructure. Every time an attack ability is executed against your environment -- whether it is a single technique test or a full adversary emulation campaign -- Morgana reports the results back, and Merlino updates the Tests Coverage column accordingly.

This column answers the question: **"Are we actually testing our defenses against these techniques, and are our tests succeeding?"** A low Tests Coverage percentage for a high-CrossPick technique means you have a dangerous gap: a technique that your adversaries are very likely to use, but that you have never validated your defenses against through Red Team testing.

The combination of all four columns creates a powerful decision matrix:

| Scenario | Meaning | Action Required |
|---|---|---|
| High CrossPick + High Data Components + High Tests | Well-defended technique | Maintain and monitor |
| High CrossPick + High Data Components + Low Tests | Detection exists but untested | Schedule Red Team validation |
| High CrossPick + Low Data Components + Any Tests | Likely attack vector with blind spot | Onboard log sources urgently |
| Low CrossPick + Any coverage | Lower priority in current profile | Address after higher priorities |

Merlino can be **directly integrated with Morgana Arsenal (Caldera)** and updates attack test and simulation data in real time. The Tests Coverage column reflects the live status of your adversary emulation program. This gives you a continuous, quantitative measure of how thoroughly your organization is actually testing its threat detection capabilities -- not just theoretically, but through actual attack simulation. A dedicated laboratory covers this integration in detail: see *Merlino User Guide-Lab 03--Red Team Testing with Morgana Arsenal.md*.

### How to Read the Matrix

- **Columns** represent ATT&CK **Tactics** (the "why" -- Initial Access, Execution, Persistence, Privilege Escalation, Defense Evasion, Credential Access, Discovery, Lateral Movement, Collection, Command and Control, Exfiltration, Impact)
- **Rows** under each tactic contain **Techniques** (the "how" -- specific methods attackers use)
- **Colored cells** indicate techniques that are used by one or more of your selected threat groups
- **Color intensity** reflects the CrossPick percentage -- how many of your selected entities share that technique:
  - High intensity = many groups use this technique (high priority for defense)
  - Low intensity = fewer groups use it
  - No color = not relevant to your current selection

### What to Look For

- **Dense columns** -- Tactics with many colored techniques indicate areas where your selected threat actors are most active
- **High-intensity cells** -- These are the techniques you should prioritize for detection and defense
- **Empty areas** -- Tactics with few or no colored techniques may represent gaps in your threat model or areas where your selected actors are less active
- **High CrossPick values** -- Techniques where multiple threat actors converge. These are the most probable attack vectors and should be at the top of your defense backlog
- **Data Components gaps** -- Techniques with high CrossPick but low Data Components Coverage reveal blind spots in your monitoring infrastructure
- **Tests Coverage gaps** -- High-priority techniques that have never been Red Team tested represent unvalidated assumptions about your defenses

![Main Coverage Detail](img/24-main-coverage-detail.png)

*Close-up of the Main Coverage matrix showing the four coverage columns (Technique Coverage, Data Components Coverage, Tests Coverage, CrossPick) at the top, followed by tactic columns with colored technique cells at varying intensities.*

---

## 10. Step 8 -- Use Insights on a Technique

Click on any colored technique cell in the Main Coverage matrix to get detailed intelligence. But pay special attention to cells that are colored **orange** -- these indicate a **warning** that Merlino has detected something worth investigating.

**How to open:** Click **Insights** in the **Logics** group on the Merlino ribbon (or it may already be visible as a side panel).

### How to Use

1. Navigate to the **Main Coverage** sheet
2. Click on a **colored cell** containing a technique (e.g., a cell showing T1566 -- Phishing)
3. Open the **Insights** taskpane
4. Merlino displays detailed information about the selected technique:
   - **Technique name and ID** (e.g., T1566 -- Phishing)
   - **Tactic mapping** (which tactic(s) this technique belongs to)
   - **Description** from MITRE ATT&CK
   - **Which of your selected groups** use this technique
   - **CrossPick percentage** showing coverage intensity
   - **Detection guidance** and data sources
   - **Warnings** -- if Merlino detects data quality issues, an orange warning banner appears with an explanation
   - **Clickable link to the MITRE ATT&CK portal** -- opens the technique page on attack.mitre.org where you can read the full official documentation, real-world examples, and mitigation guidance

### Understanding Orange Warnings -- Data Quality Matters

In the Main Coverage matrix, you will notice that some cells are colored **orange** instead of the standard heatmap colors. Orange is Merlino's way of flagging a **data quality warning** -- something that is technically present in the coverage but deserves closer scrutiny.

Let us look at a concrete example. Click on the orange cell for **Remote Access Tools (T1219)** in the Main Coverage matrix, then open the Insights taskpane. Merlino displays a warning banner:

> **Warning**  
> Parent technique T1219 shows coverage, but all sub-techniques are at 0%. This may indicate an inconsistency in coverage reporting.

What does this mean? In this case, one of the Catalogue entries (a threat group) has the parent technique code T1219 listed in its TCodes. However, T1219 -- Remote Access Tools has multiple **sub-techniques** (specific variations of the attack method), and none of those sub-techniques have any coverage. The parent technique shows up as "covered," but the actual granular detail is missing.

This is a critical signal. It means that the threat intelligence data source listed the technique at a **coarse, imprecise level**. It said "this actor uses Remote Access Tools" without specifying **which** remote access technique -- which tool, which method, which variation. The information is not wrong, but it is **incomplete and imprecise**.

### Why Sub-Technique Accuracy Is Fundamental

In threat detection engineering, the difference between a parent technique and its sub-techniques is not academic -- it is **operationally decisive**:

- A parent technique like T1219 (Remote Access Tools) is a broad category. "The adversary uses remote access tools" tells you very little about what to actually detect.
- A sub-technique like T1219.001 or a specific variation tells you exactly **which tool, which protocol, which behavior** to look for in your logs and detection rules.

When your Catalogue entries specify only parent techniques without sub-technique detail, several problems arise:

1. **Detection rules cannot be precise** -- You cannot write an effective SIEM rule for "remote access tools in general." You need to know whether the adversary uses TeamViewer, AnyDesk, RDP tunneling, or a custom RAT.
2. **Coverage reporting is inflated** -- The Main Coverage matrix shows the technique as covered, but in reality your understanding of the threat is superficial.
3. **Prioritization becomes unreliable** -- CrossPick percentages lose meaning when the underlying data mixes precise sub-technique mappings with vague parent-level ones.
4. **Red Team tests are unfocused** -- If your Tests Coverage is built on imprecise technique mappings, your adversary emulation exercises may not target the right attack variations.

Merlino surfaces these inconsistencies visually (orange cells) and textually (the warning message in Insights) so that you can **immediately identify where your threat intelligence data needs refinement**. This is one of Merlino's most valuable capabilities: it does not just display data -- it **validates the quality** of your data and alerts you to gaps.

### The Broader Impact on Threat Detection

This concept becomes enormously important when you move beyond threat group profiling and start importing **detection rules** (e.g., Microsoft Sentinel rules) into the Catalogue. If your Sentinel rules are mapped to parent techniques only, Merlino will flag the same kind of inconsistency -- showing you that your detection coverage is broader than it is deep. You might believe you are covered against T1219, but in practice your SIEM rules may only detect one specific variation while missing others entirely.

The Sentinel detection coverage laboratory (*Merlino User Guide-Lab 02--Microsoft Sentinel Detection Coverage.md*) explores this concept in depth, showing how to use Merlino's warnings to identify and close detection gaps by aligning your SIEM rules with precise sub-technique mappings.

**The takeaway:** Always pay attention to orange cells. They are Merlino's way of telling you that something in your data needs a closer look -- and in threat detection, precision at the sub-technique level can make the difference between detecting an intrusion and missing it entirely.

### MITRE ATT&CK Portal Link

In the Insights panel, each technique includes a direct hyperlink to the official MITRE ATT&CK page (e.g., `https://attack.mitre.org/techniques/T1219/`). Clicking this link opens your browser to the MITRE portal where you can find:

- Full technique description and sub-techniques
- Procedure examples (real-world usage by threat groups)
- Mitigations
- Detection recommendations

This is especially useful when you encounter an orange warning: you can immediately open the MITRE page to see the full list of sub-techniques and understand exactly which variations your data should be specifying.

![Insights Technique Detail](img/25-insights-technique-detail.png)

*The Insights taskpane showing details for a selected technique: name, ID, description, associated groups, the orange warning banner about sub-technique inconsistency, and the clickable MITRE link.*

![MITRE Portal Link](img/26-mitre-portal-link.png)

*The MITRE ATT&CK portal page for T1219 opened in the browser, showing the full list of sub-techniques and official documentation.*

---

## 11. Step 9 -- Generate an Adaptive Report

Merlino can generate a self-contained HTML report from your current analysis that can be shared with anyone -- no Excel or Merlino required to view it.

### How to Generate

1. Open the **Runbooks** taskpane
2. Select (check) **Export Analytic Reports**
3. Click **Execute Selected Runbooks**

### What the Report Contains

The HTML report includes:

- Full ATT&CK coverage matrix visualization
- Technique details and coverage statistics
- Selected entity information (which groups/software/campaigns were picked)
- Visual representation of the analysis
- Self-contained -- all styles embedded, no external dependencies

The report is downloaded as an `.html` file that can be opened in any browser and shared via email, SharePoint, or any file-sharing platform.

![Report Generation](img/27-report-generation.png)

*The Runbooks taskpane with "Export Analytic Reports" checked, or the Reports taskpane showing report options.*

![HTML Report Preview](img/28-html-report-preview.png)

*The generated HTML report opened in a web browser, showing the ATT&CK matrix visualization, coverage statistics, and selected threat group information.*

---

## 12. Step 10 -- Explore Attack Knowledge Graph

The Attack Knowledge taskpane provides a **force-directed graph visualization** of the relationships between your selected entities and ATT&CK techniques. This is not a simple diagram -- it is an interactive analytical instrument that reveals hidden patterns, shared attack behaviors, and potential strategic alliances between threat actors.

**How to open:** Click **Attack Knowledge** in the **Logics** group on the Merlino ribbon.

### What It Shows

- **Green nodes** represent **threat groups** (the entities from your Catalogue). Larger green nodes indicate groups with more technique connections.
- **Purple/blue nodes** represent **ATT&CK techniques and sub-techniques**. Larger technique nodes indicate techniques shared by multiple groups.
- **Edges** (connecting lines) represent relationships between groups and techniques -- a line from APT28 to T1566.001 means APT28 is known to use Spearphishing Attachment.
- **Interactive** -- you can drag nodes to rearrange the layout, zoom in/out, and hover over any node to see its details and connections.

### The Two Key Controls: Depth and Rel. Strength

At the top of the Attack Knowledge taskpane you will find two sliders that fundamentally change what the graph reveals:

#### Depth

The **Depth** slider controls **how deep Merlino goes into the data** when building the graph. At lower depth values, the graph shows only the most direct relationships between your picked entities and their techniques. As you increase depth, Merlino expands the analysis to include additional layers of data -- campaigns linked to your groups, software used by those campaigns, techniques associated with that software, and so on.

In practice, increasing depth means you are asking Merlino to follow the chain of relationships further and further into the MITRE ATT&CK knowledge base. This can reveal indirect but important connections that would not be visible at a shallow level -- for example, two groups that do not share any direct techniques but both use the same malware, which in turn maps to a common set of sub-techniques.

#### Rel. Strength (Relationship Strength)

The **Rel. Strength** slider controls the **minimum strength of the relationships** displayed in the graph. Merlino calculates relationship strength by considering multiple factors present in the MITRE ATT&CK data: technique co-occurrence, shared campaigns, common software usage, overlapping tactics, and other intelligence data points.

At lower Rel. Strength values, the graph shows all relationships, including weak or indirect ones. As you increase the value, the graph filters out weaker connections and shows only the strongest, most significant relationships. This is extremely useful for cutting through noise and focusing on the most operationally relevant patterns.

**By combining Depth and Rel. Strength** you can perform layered investigation: start with a shallow, high-strength view to see the most obvious patterns, then gradually increase depth and decrease strength to discover subtler connections and indirect relationships.

### Reading the Graph -- A Practical Example

Looking at the force-directed graph generated from our six APT groups, several important patterns become immediately visible:

**APT28 is the dominant central node.** It sits at the center of the graph with the most connections radiating outward. This tells us that APT28 covers a very large number of techniques and shares significant overlap with multiple other groups. In strategic terms, APT28 emerges as a **reference point** -- an adversary whose TTP repertoire is so broad that defending against APT28 effectively means covering a large portion of the techniques used by the other groups as well. If you need to prioritize your defense investments, focusing on APT28's techniques gives you the widest coverage.

**MuddyWater and APT33 are strongly connected.** The graph shows that these two groups share multiple techniques, with **T1566.001 (Spearphishing Attachment)** being a prominent shared technique between them. This pattern of shared techniques between MuddyWater and APT33 is not coincidental -- it can indicate:

- **Common tooling** -- both groups may use similar or shared attack frameworks and infrastructure
- **Operational collaboration** -- threat intelligence research suggests that groups operating in the same geopolitical sphere often share tools, techniques, and even operational infrastructure
- **Strategic alliance patterns** -- when multiple groups converge on the same techniques, it may reflect coordinated or at least aligned operational objectives

These insights are valuable for threat intelligence analysts: they reveal not just individual group capabilities but the **relationships and potential coordination between threat actors** targeting your organization.

**Technique nodes with many connections** (like T1566.001 -- Spearphishing Attachment, T1059.001 -- PowerShell, T1003.003 -- NTDS) represent shared attack methods that multiple groups rely on. These are the techniques where your defensive investment yields the highest return -- blocking or detecting one well-connected technique degrades the capabilities of multiple adversaries simultaneously.

### Using Rel. Strength to Reveal Operational Clusters

By increasing the **Rel. Strength** slider (for example to 2), the graph filters out weaker connections and reveals only the strongest relationships between groups. This produces a dramatically clearer picture of how your threat actors actually cluster together operationally.

In our laboratory, adjusting Rel. Strength reveals three distinct patterns:

- **APT33 and MuddyWater** form a tightly connected pair -- they share strong technique overlap and appear closely linked in the graph, confirming a significant operational affinity between these two groups.
- **APT42, APT28, and APT39** form a second cluster -- these three groups are connected to each other through strong shared technique relationships, suggesting a broader operational ecosystem with overlapping capabilities and potential resource sharing.
- **APT29 operates in relative isolation** -- with higher Rel. Strength filtering, APT29 appears disconnected from the other groups. This tells us that APT29's TTP repertoire is largely independent: it uses a distinct set of techniques that do not strongly overlap with the other five groups in our profile.

This is a powerful intelligence insight. APT29's isolation means that defending against the other five groups does **not** automatically cover APT29's attack methods -- it requires its own dedicated detection and defense strategy. Conversely, the clustering of APT33/MuddyWater and APT42/APT28/APT39 means that investments in detecting shared techniques within each cluster yield compound returns across multiple adversaries.

### How to Use

1. Open the Attack Knowledge taskpane
2. The graph renders automatically based on your current Catalogue and Pick selections
3. Start with the default **Depth** and **Rel. Strength** values to see the overall picture
4. Drag nodes to rearrange the layout and untangle overlapping connections
5. Hover over a node to see its name, type, and connections
6. **Increase Depth** to pull in additional data domains -- campaigns, software, mitigations -- and discover indirect relationships that enrich your understanding of the threat landscape
7. **Adjust Rel. Strength** to filter the graph: increase it to focus on the strongest, most significant connections; decrease it to explore weaker or more speculative relationships
8. Look for **central nodes** (high connectivity = high priority for defense), **clusters** (groups sharing many techniques = possible collaboration), and **bridge techniques** (techniques connecting otherwise separate groups = critical chokepoints)

The Attack Knowledge graph transforms flat spreadsheet data into a visual intelligence map. By experimenting with Depth and Rel. Strength, you can investigate your threat landscape from multiple angles and uncover patterns that would be invisible in tabular data alone.

![Attack Knowledge Graph](img/29-attack-knowledge-graph.png)

*The Attack Knowledge force-directed graph showing threat groups (green nodes: APT28, APT29, APT33, APT39, APT42, MuddyWater) connected to shared ATT&CK technique nodes (purple). APT28 sits at the center with the most connections. MuddyWater and APT33 share techniques like T1566.001. The Depth and Rel. Strength sliders at the top control the analysis scope and filtering.*

![Attack Knowledge Rel Strength Clusters](img/30-attack-knowledge-rel-strength.png)

*The Attack Knowledge graph with Rel. Strength increased to 2, showing the three operational clusters: APT33/MuddyWater linked together, APT42/APT28/APT39 forming a second cluster, and APT29 isolated with no strong connections to the other groups.*

---

## 13. Step 11 -- Analyze CrossPick Coverage Across Sheets

After running Smart View, every data table in Merlino has updated **CrossPick** percentages. This is one of the most powerful analytical steps in the entire workflow: by sorting each sheet from largest to smallest CrossPick, you can analyze your threat profile from **every possible angle** -- techniques, log sources, campaigns, offensive tools, detection strategies, vulnerabilities, and threat group overlap.

### How to Explore

For each sheet listed below, navigate to the sheet tab and **sort the table by the CrossPick column (largest to smallest)**:

1. Click on the **CrossPick** column header
2. Click **Sort Largest to Smallest** (or use Data > Sort)
3. The rows at the top are the most relevant to your threat profile -- they are the items that overlap most strongly with your selected Catalogue entities

Repeat this for every sheet. Each one reveals a different dimension of intelligence about the same threat profile.

### Techniques Sheet

Sort the **Techniques** sheet by CrossPick descending. The techniques at the top of the list are the **most critical attack methods** that your organization must address in its security runbooks and threat detection systems.

These are the techniques that multiple threat groups in your Catalogue share. A technique with CrossPick = 100% means that **every single selected group** uses this attack method -- it is virtually guaranteed to appear in an intrusion targeting your organization.

This is your **prioritized threat detection checklist**. For each high-CrossPick technique, verify that you have:

- **Detection rules** in your SIEM (Sentinel, Splunk, etc.) that cover this technique
- **Incident response playbooks** that address this attack method
- **Security controls** (endpoint protection, network segmentation, access policies) that mitigate it
- **Monitoring dashboards** that provide visibility into indicators of this technique

The techniques at the top of this list should be the first items your SOC team reviews and validates. If any high-CrossPick technique lacks a corresponding detection rule or response playbook, you have identified a critical gap that needs immediate attention.

![Techniques Sorted by CrossPick](img/31-techniques-sorted-crosspick.png)

*The Techniques sheet sorted by CrossPick descending. Top rows show the highest-priority techniques -- the attack methods most commonly shared across your selected threat groups. These are the techniques your detection engineering and incident response should address first.*

### Data Components Sheet

Sort the **Data Components** sheet by CrossPick descending. This sheet answers a question that is often overlooked in threat intelligence work: **"Do we have the right log sources and telemetry to detect the techniques that matter most?"**

MITRE ATT&CK maps each technique to specific **Data Components** -- the types of log data and telemetry required to detect that technique. For example, detecting credential dumping (T1003) requires data components like Process Access events, OS API Execution logs, and Command Execution monitoring.

When you sort Data Components by CrossPick, the items at the top are the **log sources you absolutely must have** in your SIEM and monitoring infrastructure. If a data component has a high CrossPick but your organization does not collect that type of telemetry, you have found a **critical visibility blind spot** -- an area where attacks could occur undetected because you simply do not have the logs to see them.

Use this view to build and validate your **log source onboarding roadmap**: which data sources to prioritize in your SIEM, which endpoint telemetry to enable, and which network monitoring capabilities need to be deployed. This is where threat intelligence directly drives infrastructure decisions.

![Data Components Sorted by CrossPick](img/32-datacomponents-sorted-crosspick.png)

*The Data Components sheet sorted by CrossPick descending, showing the most critical log sources and telemetry types required to detect the techniques in your threat profile. High-CrossPick data components represent log sources that your SIEM must collect.*

### Campaigns Sheet

Sort the **Campaigns** sheet by CrossPick descending. This reveals which **known attack campaigns** are most closely related to the threat groups in your Catalogue.

Campaigns in MITRE ATT&CK represent specific documented attack operations -- coordinated intrusion activities attributed to one or more threat groups over a defined time period. When a campaign has a high CrossPick, it means the techniques used in that campaign strongly overlap with the techniques used by your selected threat actors.

This is valuable intelligence for several reasons:

- **Threat briefings** -- You can brief your leadership and SOC team on the specific campaigns most likely to target your organization, including timelines, targets, and impacts documented by MITRE
- **Historical analysis** -- Understanding past campaigns helps predict future adversary behavior, since threat actors tend to reuse successful TTPs
- **Detection validation** -- If a campaign is highly relevant to your profile, you can validate your detections against the specific techniques used in that campaign as a focused test scenario

![Campaigns Sorted by CrossPick](img/33-campaigns-sorted-crosspick.png)

*The Campaigns sheet sorted by CrossPick descending, showing the most relevant known attack campaigns associated with your threat profile. High-CrossPick campaigns share the most technique overlap with your selected groups.*

### Software Sheet

Sort the **Software** sheet by CrossPick descending. This shows which **offensive tools, malware, and attack frameworks** are most commonly used across the threat groups in your Catalogue.

Software in MITRE ATT&CK includes both **malware** (custom-built malicious software) and **tools** (legitimate or open-source utilities repurposed for offensive use). When multiple threat groups in your profile share the same software, it reveals the common attack infrastructure your adversaries rely on.

High-CrossPick software entries are the tools and malware that your security controls should be specifically configured to detect and block:

- **Endpoint Detection and Response (EDR)** -- Ensure your EDR solution has signatures and behavioral detections for these tools
- **Network security** -- Configure IDS/IPS rules and network monitoring for command-and-control traffic patterns associated with these tools
- **Application whitelisting** -- Block execution of known offensive tools where possible
- **Threat hunting** -- Use the IOCs and behavioral patterns of these tools as starting points for proactive threat hunting in your environment

![Software Sorted by CrossPick](img/34-software-sorted-crosspick.png)

*The Software sheet sorted by CrossPick descending, showing the most commonly used offensive tools and malware among your selected threat groups. These are the attack tools your EDR, network security, and threat hunting should prioritize.*

### Detection Strategies Sheet

Sort the **Detection Strategies** sheet by CrossPick descending. This sheet provides a direct bridge between threat intelligence and **practical detection implementation**.

Detection strategies in MITRE ATT&CK describe specific approaches for identifying the presence of a technique in your environment -- they go beyond listing data sources and describe **how** to combine and analyze telemetry to reliably detect an attack. This includes detection logic, analysis approaches, and the types of correlations needed.

When sorted by CrossPick, the top entries represent the **detection strategies that address the most critical techniques in your threat profile**. These are the strategies your detection engineering team should implement first:

- **SIEM correlation rules** -- Build or validate rules that implement these detection strategies
- **Alert tuning** -- Ensure that your existing alerts align with these high-priority strategies and are not generating excessive false positives that might cause alert fatigue
- **Detection coverage mapping** -- Map each high-CrossPick detection strategy to your existing rules to identify gaps where no detection exists
- **Continuous improvement** -- Use these strategies as a baseline for iterating and improving your detection capabilities over time

![Detection Strategies Sorted by CrossPick](img/35-detection-strategies-sorted-crosspick.png)

*The Detection Strategies sheet sorted by CrossPick descending, showing the most important detection approaches for your threat profile. These are the detection methods your SIEM rules and monitoring should implement first.*

### Mitigations Sheet

Sort the **Mitigations** sheet by CrossPick descending. This sheet maps directly from threat intelligence to **actionable security controls** -- it tells you which MITRE-recommended mitigations are most relevant to the techniques your profiled threat actors use.

Mitigations in MITRE ATT&CK are specific security measures that reduce or eliminate the effectiveness of a technique. They range from broad architectural controls (network segmentation, multi-factor authentication) to targeted technical measures (restrict registry permissions, disable or remove feature or program). Each mitigation is mapped to the techniques it addresses.

When sorted by CrossPick, the top mitigations are the **security controls that provide the broadest protection** against your specific threat profile:

- **Security architecture validation** -- Verify that the high-CrossPick mitigations are actually implemented in your environment. A mitigation with CrossPick = 85% that is not deployed means a single missing control leaves you exposed to the majority of your adversaries' techniques
- **Investment prioritization** -- Use this ranking to justify security budget allocation. A mitigation that addresses techniques shared by 5 out of 6 threat groups delivers more risk reduction than one that addresses a technique used by only 1 group
- **Gap analysis** -- Compare the top mitigations against your current security controls inventory. Any high-CrossPick mitigation that is absent or partially implemented is a prioritized remediation item
- **Compliance mapping** -- Many MITRE mitigations align with controls from frameworks like NIST CSF, ISO 27001, and CIS Controls. This view helps you demonstrate that your security investments are driven by real threat data, not just checkbox compliance

This is also valuable for **executive reporting**: instead of presenting a generic list of security recommendations, you can show leadership exactly which controls matter most based on the threat actors that target your sector.

![Mitigations Sorted by CrossPick](img/36-mitigations-sorted-crosspick.png)

*The Mitigations sheet sorted by CrossPick descending, showing the security controls most relevant to your threat profile. High-CrossPick mitigations protect against techniques shared by multiple threat groups in your Catalogue.*

### CVE Sheet

Sort the **CVE** sheet by CrossPick descending. This sheet shows the **most recently published vulnerabilities** (from the last week's NIST NVD import) that are most relevant to the techniques used by your threat groups.

When Merlino imports recent CVEs and then runs CrossPick analysis, it correlates vulnerability data with your threat profile. A high-CrossPick CVE means that the vulnerability maps to techniques that your profiled threat actors are known to exploit. This is an extremely powerful signal: it tells you that a newly disclosed vulnerability is not just theoretically dangerous -- it is **directly relevant to the adversaries targeting your organization**.

Use this view to:

- **Prioritize patching** -- High-CrossPick CVEs should go to the top of your vulnerability management queue, ahead of lower-relevance vulnerabilities regardless of their CVSS score alone
- **Threat-informed vulnerability management** -- Combine CVSS severity with CrossPick relevance to make patching decisions that reflect your actual threat landscape, not just generic severity ratings
- **Zero-day response** -- When a new CVE is published and appears with a high CrossPick, your incident response team should treat it with elevated urgency because your known adversaries are likely to weaponize it
- **Risk communication** -- Report to management not just "we have X critical CVEs" but "we have X critical CVEs that are directly relevant to the threat actors targeting our sector"

![CVEs Sorted by CrossPick](img/37-cves-sorted-crosspick.png)

*The CVE sheet sorted by CrossPick descending, showing the most recently published vulnerabilities that are most relevant to your threat profile. High-CrossPick CVEs represent vulnerabilities that your specific threat actors are likely to exploit.*

### Threat Groups Sheet

Sort the **Threat Groups** sheet by CrossPick descending. This view reveals something particularly interesting: the **technique overlap between your selected groups and all other known threat groups** in the MITRE ATT&CK database.

Your six selected groups (APT28, APT29, APT33, APT39, APT42, MuddyWater) will naturally appear at the top with high CrossPick values. But look at the groups **just below them** -- these are threat actors that you did **not** explicitly select, but whose technique repertoire significantly overlaps with yours.

This is critical intelligence:

- **Emerging threats** -- A group you did not originally include in your profile may have a high CrossPick, meaning it uses many of the same techniques as your selected adversaries. This group could represent an **additional threat** that you should add to your Catalogue
- **Expanding your profile** -- If a previously unknown or lower-priority group shows strong overlap, consider adding it to your analysis to get a more complete picture
- **Alliance and ecosystem mapping** -- Groups that share high technique overlap may be part of the same operational ecosystem, share tooling or infrastructure, or operate under similar strategic directives
- **Validation** -- If the top groups in the sorted list are exactly the ones you selected, it confirms that your Catalogue is internally consistent and your threat profile is well-defined

![Threat Groups Sorted by CrossPick](img/38-threat-groups-sorted-crosspick.png)

*The Threat Groups sheet sorted by CrossPick descending. Your six selected groups appear at the top. Groups just below them represent additional threat actors with significant technique overlap -- potential additions to your threat profile.*

---

## 14. Step 12 -- Tests & Operations (Caldera/Morgana)

The Tests & Operations taskpane lets you interact with a Caldera/Morgana Red Team server to synchronize attack capabilities and plan adversary emulation operations.

**How to open:** Click **Tests & Operations** in the **Operations** group on the Merlino ribbon.

**Prerequisite:** You must have a Caldera/Morgana server configured in Settings. If you do not have one, this section can be skipped during testing.

### 14.1 Synchronize Catalogue

Click the **Synchronize Catalogue** button to:

- Read the current Catalogue entries in your workbook
- Match them against the Caldera abilities (test procedures) available on your Morgana server
- Update the **Tests** sheet with all matching abilities
- This maps your threat intelligence selections (Catalogue) to actual Red Team test procedures that can be executed

After synchronization, the Tests sheet will contain rows for each available Caldera ability that matches your selected techniques, along with:
- Ability name and description
- Linked ATT&CK technique codes (TCodes)
- Executor type (PowerShell, cmd, bash, etc.)
- Platform information

![Tests & Operations Taskpane](img/39-tests-operations-taskpane.png)

*The Tests & Operations taskpane showing the Synchronize Catalogue and Synchronize Morgana buttons.*

### 14.2 Synchronize Morgana

Click the **Synchronize Morgana** button to perform one of Merlino's most powerful automation steps. This single click triggers a fully automated process that:

- **Creates all adversary profiles** on your Morgana/Caldera server -- Merlino reads the Catalogue and Tests sheet, organizes the matching abilities into coherent adversary profiles with complete attack chains, and pushes them to Morgana. Each adversary profile is structured with the correct sequence of techniques, organized by tactic phase (Initial Access through Impact)
- **Creates all operations** ready to be launched -- Merlino automatically generates operations on the Morgana/Caldera server, pre-configured with the correct adversary profiles, target agents, and execution parameters. These operations are immediately ready to execute with a single click in the Morgana interface
- **Populates the Excel sheets** (Agents, Tests, Adversaries, Operations) with the synchronized data, giving you complete visibility into your Red Team infrastructure from within Excel

This automation is transformative. What would normally take a Red Team operator **days of manual work** -- reviewing technique lists, selecting matching abilities, organizing them into adversary profiles with logical attack chains, configuring operations with the right parameters -- Merlino accomplishes in seconds. The entire pipeline from threat intelligence analysis (your Catalogue) to ready-to-launch Red Team operations is fully automated.

After synchronization, you can:
- See all deployed agents and their status in the Agents sheet
- Review the automatically created adversary profiles in the Adversaries sheet
- Verify the generated operations in the Operations sheet
- Open Morgana/Caldera and launch any operation immediately -- everything is pre-configured and ready to go

![Tests Synchronized](img/40-tests-synchronized.png)

*The Tests sheet after synchronization, showing rows of Caldera abilities with columns for Pick, TCodes, Name, Description, Executor, Platform.*

![Morgana Operations Ready](img/41-morgana-operations-ready.png)

*The Morgana/Caldera interface showing the operations automatically created by Merlino. Each operation is pre-configured with the correct adversary profile, attack chain, and target agents -- ready to be launched with a single click.*

---

## 15. Step 13 -- IOC Management and MISP Integration

The IOC (Indicator of Compromise) taskpane connects Merlino to **MISP** (Malware Information Sharing Platform) -- one of the most powerful open-source threat intelligence platforms in the world.

**MISP** is a collaborative platform used by thousands of organizations, CERTs, ISACs, and government agencies worldwide. It aggregates threat intelligence from an enormous global network of contributors: national cybersecurity centers, private sector security teams, law enforcement agencies, and independent researchers all feed data into MISP instances. The platform automatically correlates this data, identifies patterns across different sources, and enriches indicators with contextual intelligence -- including ATT&CK technique mappings, threat actor attributions, campaign associations, and relationships between indicators that no single organization could discover alone.

Merlino's integration with MISP creates a **bidirectional intelligence pipeline**: you push your curated analysis to MISP, and MISP enriches it with global intelligence before you pull it back. This turns your local threat profile into a globally informed intelligence product.

**How to open:** Click **IOC** in the ribbon.

**Prerequisite:** MISP server must be configured in Settings for MISP integration features.

### 15.1 Catalogue to MISP -- Push Your Analysis

Click the **Catalogue to MISP** button to export your entire Merlino analysis to MISP. This operation:

- Reads your current Catalogue entries -- the threat groups, techniques, software, campaigns, and all entities you selected during your analysis
- Packages them into a structured **MISP event** with proper ATT&CK technique tags, threat actor attributions, and relationship mappings
- Pushes the event to your MISP server where it becomes part of the shared intelligence ecosystem

Once your data arrives in MISP, the platform's **correlation engine** goes to work. MISP automatically cross-references your indicators against everything in its database -- intelligence feeds from other organizations, historical events, known malware samples, network indicators, and much more. If any of the techniques, threat actors, or indicators in your Merlino analysis match information from other sources, MISP creates correlation links that connect your data to the broader global intelligence picture.

This sharing is valuable in multiple directions:

- **Your SOC team** can immediately access the structured threat intelligence in MISP's interface, with all the correlations and enrichments
- **Partner organizations** in your MISP sharing community receive your analysis and can incorporate it into their own defenses
- **MISP feeds** from other contributors may already contain related intelligence that MISP will automatically link to your event, enriching your analysis with context you did not have before

![IOC Catalogue to MISP](img/42-ioc-catalogue-to-misp.png)

*The IOC taskpane showing the "Catalogue to MISP" button and a success notification after pushing data to MISP.*

### 15.2 Import from MISP -- Pull Enriched Intelligence Back

Click the **Import from MISP** button to pull intelligence from your MISP instance back into Merlino. This is where the bidirectional pipeline delivers its full value.

When you import from MISP, Merlino retrieves:

- **IOCs** (Indicators of Compromise) -- IP addresses, domains, file hashes, URLs, email addresses, and other technical indicators associated with the threats in your profile
- **Enriched attributes** -- MISP may have added additional context to your original data: new technique mappings discovered through correlation, related indicators contributed by other organizations, threat actor details from external feeds, and timeline information from campaign tracking
- **Correlated intelligence** -- If other MISP contributors have reported similar threats, their indicators and analysis are now available to you. A threat group you profiled in Merlino may have been observed by another organization using infrastructure (IP addresses, domains, C2 servers) that MISP has correlated together
- **ATT&CK technique mappings** -- Where possible, Merlino maps imported indicators back to ATT&CK techniques so they integrate seamlessly with your existing coverage analysis

The power of this workflow is cumulative. You start with a local threat profile built from MITRE ATT&CK data in Merlino. You push it to MISP, where it is enriched with global intelligence from potentially hundreds of contributing organizations. You pull that enriched data back into Merlino, where it adds depth and actionable detail to your analysis -- IOCs you can feed into your SIEM, network indicators you can block at your firewall, and correlated intelligence that reveals connections your original analysis alone could not have identified.

**The intelligence cycle in practice:** Merlino creates the structured analysis. MISP enriches it with the world's intelligence. Merlino imports the enriched results back for operational use. This is how modern threat intelligence programs operate -- local analysis amplified by global collaboration.

![IOC Import from MISP](img/43-ioc-import-from-misp.png)

*The IOC taskpane showing the "Import from MISP" button and imported IOC data enriched with indicators from the MISP platform's global intelligence network.*

---

## 16. Step 14 -- AI-Powered Analysis

Merlino integrates AI capabilities for automated threat analysis, technique review, and Red Team planning.

**Prerequisite:** At least one AI provider (OpenAI, Mistral, etc.) must be configured in Settings with a valid API key.

### How to Use

1. Navigate to the **AI** sheet tab in your workbook. This sheet contains **pre-built analysis prompts** designed for cyber threat intelligence workflows -- prompt templates for technique analysis, gap analysis, detection recommendations, and more, along with result columns where AI responses are written. Review and optionally customize the prompts to match your analysis needs.
2. Click **AI** in the **Logics** group on the Merlino ribbon to open the AI Assistant taskpane.
3. In the taskpane, select your AI provider and click **AI Review** (or the appropriate analysis button).
4. Merlino sends the prompt together with relevant context from your workbook -- selected techniques, coverage data, CrossPick percentages, and detection gaps -- to your configured AI provider.
5. The AI response is written back to the AI sheet result columns.

### What AI Analysis Provides

- **Threat assessment summaries** -- Automated narrative analysis of your threat profile, highlighting the most critical attack vectors and adversary capabilities
- **Detection gap analysis** -- AI identifies techniques where your detection coverage is weak or missing, cross-referencing CrossPick priority with Data Components and Tests Coverage
- **Technique prioritization recommendations** -- AI-generated rankings of which techniques to address first, based on the combined weight of threat intelligence, detection readiness, and testing maturity
- **Mitigation suggestions** -- Specific security control recommendations aligned with MITRE mitigations for your highest-priority techniques
- **Red Team scenario planning** -- AI-generated adversary emulation scenarios based on your threat profile, useful for briefing Red Team operators before Morgana/Caldera exercises

The AI sheet retains all responses, building a structured record of AI-assisted analysis that can be referenced, exported, or included in reports.

A practical example of AI-powered analysis applied to detection coverage -- including how to use AI Review to identify gaps in Sentinel rule mappings and generate prioritized remediation recommendations -- is covered in the dedicated laboratory: *Merlino User Guide-Lab 02--Microsoft Sentinel Detection Coverage.md*.

![AI-Powered Analysis](img/44-ai-analysis.png)

*The AI sheet and AI Assistant taskpane. The sheet contains pre-built prompt templates with result columns where AI responses are written. The taskpane provides provider selection and the AI Review button that triggers analysis using your workbook's threat intelligence context.*

---

## 17. Anacleto -- Contextual Documentation Assistant

**Anacleto** is Merlino's built-in contextual documentation assistant. It appears as a collapsible panel within most taskpanes.

### How It Works

- Anacleto provides **context-sensitive help** -- the documentation shown changes based on which section of the taskpane you are interacting with
- Look for the **Anacleto panel** at the bottom or side of taskpanes (it may have a toggle button to show/hide)
- When you hover over or interact with a specific setting, button, or section, Anacleto displays relevant documentation and guidance
- This eliminates the need to switch to an external help document while working

### Key Features

- **In-place documentation** -- no need to leave the taskpane
- **Context-aware** -- shows different help text depending on what you are doing
- **Collapsible** -- can be hidden when not needed to save screen space
- **Covers all taskpanes** -- available throughout Merlino's interface

![Anacleto Panel](img/45-anacleto-panel.png)

*A taskpane showing the Anacleto documentation panel open at the bottom, displaying context-relevant help text with the toggle button visible.*

---

## 18. Logs Taskpane

The Logs taskpane provides direct access to Merlino's operational log files for troubleshooting and audit purposes.

**How to open:** Click **Logs** in the **Help** group on the Merlino ribbon.

### What It Shows

- Lists all log files stored in `C:\Temp\MerlinoLogs\`
- Log files are named `Merlino_YYYY-MM-DD_HH-MM-SS.log`
- Each session creates a new log file (sessions are limited to approximately 8 hours)
- You can view log contents directly in the taskpane
- Logs contain operational information: actions performed, errors encountered, performance metrics, API call results

### What Logs Do NOT Contain

- No personally identifiable information (PII)
- No email addresses or usernames
- No API key values
- No sensitive document content

Logs are useful for:
- Troubleshooting errors ("why did this import fail?")
- Verifying operations completed successfully
- Understanding the sequence of events during analysis
- Providing diagnostic information to X3M.AI support if needed

![Logs Taskpane](img/46-logs-taskpane.png)

*The Logs taskpane showing a list of log files with timestamps, and the contents of one selected log file with correlation IDs and operation descriptions.*

---

## 19. Summary of Ribbon Layout

Merlino's features are organized into five ribbon groups:

### Operations Group
| Button | Function |
|---|---|
| **Templates** | Load Excel templates (Enterprise, Mobile, ICS, Azure) |
| **Sources** | Import MITRE ATT&CK data, Microsoft sources, CVEs |
| **Runbooks** | Automated multi-step workflows |

### Intelligence Group
| Button | Function |
|---|---|
| **Attack Knowledge** | Force-directed relationship graph |
| **Insights** | Technique details and entity analysis |
| **Adaptive Report** | Generate self-contained HTML reports |

### Data Group
| Button | Function |
|---|---|
| **CVE** | CVE enrichment via NIST NVD |
| **Exploit Database** | Import 46,000+ exploits mapped to MITRE |
| **AI** | AI-powered threat analysis |

### Morgana Arsenal Group
| Button | Function |
|---|---|
| **IOC** | Indicator of Compromise management and MISP integration |
| **Agents** | Manage Caldera/Morgana agents |
| **Tests and Operations** | Caldera abilities, adversaries, operations |

### Help Group
| Button | Function |
|---|---|
| **Logs** | View application logs |
| **Settings** | Configure all integrations and preferences |
| **Anacleto** | Contextual documentation assistant |

![Ribbon Full Annotated](img/47-ribbon-full-annotated.png)

*The full Merlino ribbon with annotations labeling each button and its group (Operations, Logics, Help).*

---

## Quick Reference -- Complete Workflow Summary

| Step | Action | Taskpane |
|---|---|---|
| 1 | Configure Settings (AI, Morgana, MISP, Theme) | Settings |
| 2 | Load Enterprise template | Templates |
| 3 | Import Techniques, Groups, Software, Campaigns, Data Sources, CVEs | Sources |
| 4 | Run **Update Core** runbook | Runbooks |
| 5 | Set Pick = TRUE on target threat groups | Groups sheet (manual) |
| 6 | Run **Include Picks in Catalogue** | Runbooks |
| 7 | Run **Update Core** + **Smart View** | Runbooks |
| 8 | Explore Main Coverage heatmap | Main Coverage sheet |
| 9 | Click a colored technique, open Insights | Insights |
| 10 | Generate Adaptive Report | Runbooks / Reports |
| 11 | Explore Attack Knowledge graph | Attack Knowledge |
| 12 | Sort sheets by CrossPick for prioritization | All sheets |
| 13 | Synchronize with Caldera/Morgana | Tests & Operations |
| 14 | Push to MISP / Import from MISP | IOC |
| 15 | Run AI Review on analysis | AI |

---

**End of User Guide**

*For additional help, use Anacleto within any taskpane or contact support@x3m.ai.*
