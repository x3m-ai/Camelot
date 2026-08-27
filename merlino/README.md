# Merlino User and Administrator Manual

> **Applies to:** Merlino implementation package 0.4.0; public Office manifest 1.5.0.0 (verified 27 August 2026)
> **Audience:** CTI analysts, Detection Engineers, Purple Teams, Red Teams, workbook owners, and Microsoft 365 administrators
> **Product status:** Free Excel Add-in distributed through the official Merlino web deployment and approved sideloading methods. It is not currently documented here as an AppSource product.

Merlino turns Microsoft Excel into a task-oriented Cyber Threat Intelligence and Purple Teaming workspace. It imports MITRE ATT&CK and security-control data, relates records through ATT&CK technique IDs, calculates coverage, synchronizes selected metadata and evidence with Morgana, and can send selected workbook content to an optional AI provider.

> [!CAUTION]
> **Always start in a new or fully backed-up workbook. Loading a Merlino template deletes every existing worksheet in the current workbook and replaces it with the template worksheets. Several source importers also delete and recreate their own destination sheet. Unsaved or unbacked-up content can be lost.**

This public manual intentionally contains no passwords, API keys, tokens, tenant identifiers, private hostnames, or environment-specific fallback values. Values such as `<MORGANA_URL>` and `<AI_API_KEY>` are placeholders.

## Table of Contents

1. [Product Overview](#1-product-overview)
2. [Current Feature Status](#2-current-feature-status)
3. [Architecture, Storage, and Network Flow](#3-architecture-storage-and-network-flow)
4. [Requirements](#4-requirements)
5. [Install Merlino](#5-install-merlino)
6. [First Run and Workbook Safety](#6-first-run-and-workbook-safety)
7. [Ribbon Map](#7-ribbon-map)
8. [Workbook Schema](#8-workbook-schema)
9. [Templates](#9-templates)
10. [Sources Overview](#10-sources-overview)
11. [MITRE ATT&CK Imports](#11-mitre-attck-imports)
12. [Microsoft and Third-Party Imports](#12-microsoft-and-third-party-imports)
13. [Data Components and Detection Strategies](#13-data-components-and-detection-strategies)
14. [TTP Attribution](#14-ttp-attribution)
15. [Excalibur Package Import](#15-excalibur-package-import)
16. [Pick, CrossPick, and Catalogue](#16-pick-crosspick-and-catalogue)
17. [Runbooks](#17-runbooks)
18. [Update Core](#18-update-core)
19. [Smart View](#19-smart-view)
20. [Main Coverage](#20-main-coverage)
21. [Data Insights](#21-data-insights)
22. [Attack Knowledge](#22-attack-knowledge)
23. [CVE Enrichment](#23-cve-enrichment)
24. [Exploit Database](#24-exploit-database)
25. [IOC and MISP](#25-ioc-and-misp)
26. [Morgana Configuration](#26-morgana-configuration)
27. [Agents Intelligence](#27-agents-intelligence)
28. [Tests and Operations](#28-tests-and-operations)
29. [AI Mission Engine](#29-ai-mission-engine)
30. [Promptbooks](#30-promptbooks)
31. [Adaptive Reports](#31-adaptive-reports)
32. [Settings Reference](#32-settings-reference)
33. [Anacleto, Logs, Ribbon Refresh, and Custom Functions](#33-anacleto-logs-ribbon-refresh-and-custom-functions)
34. [Privacy and Security](#34-privacy-and-security)
35. [Backup, Restore, and Administration](#35-backup-restore-and-administration)
36. [Troubleshooting](#36-troubleshooting)
37. [FAQ](#37-faq)
38. [Glossary](#38-glossary)
39. [References](#39-references)

## 1. Product Overview

Merlino uses Excel tables as the working data model. Most analysis is driven by three common columns:

- `Pick`: an analyst-controlled Boolean selection.
- `CrossPick`: a calculated percentage or score that expresses relevance to the current selection.
- `TCodes`: one or more MITRE ATT&CK technique IDs, such as `T1059` or `T1059.001`.

A typical workflow is:

1. Install the add-in through an approved custom-manifest path.
2. Open a new workbook and load an official Merlino template.
3. Import ATT&CK techniques and the entity types needed for the analysis.
4. Import defensive controls, detection rules, vulnerability data, exploits, or MISP intelligence.
5. Set `Pick=TRUE` on relevant rows.
6. Run **Include Picks in Catalogue**, **Update Core**, and the required **Smart View** mode.
7. Review Main Coverage, Data Insights, Attack Knowledge, or Adaptive Reports.
8. Optionally synchronize Chain definitions and Test evidence with a separately administered Morgana server.
9. Optionally run Promptbooks or report analysis through a configured AI provider.

Merlino is an analysis and orchestration client. It is not a SIEM, vulnerability scanner, MISP server, AI service, or endpoint execution engine.

## 2. Current Feature Status

### 2.1 Verified active features

The production build includes these taskpanes:

- Templates
- Sources
- Agents Intelligence
- Tests & Operations
- Exploit Database
- IOC
- Adaptive Reports
- AI Mission Engine
- Runbooks
- Data Insights
- Attack Knowledge
- Logs
- Anacleto
- Settings
- CVE Enrichment

It also includes a ribbon Refresh command and four utility custom functions.

### 2.2 Present in source but not active

Do not plan an operational workflow around these items:

| Item | Current status |
|---|---|
| Red Vision | Source files exist, but there is no production build entry. It is not an active taskpane. |
| Standalone `Insights` implementation | Source exists without a built HTML/taskpane entry. Use **Data Insights**. |
| Orchestrator, Excel, and MITRE agent classes | Framework code exists, but the active AI Mission Engine UI runs Promptbooks directly. Do not describe these dormant agents as the current user workflow. |
| Legacy Mistral and AWS Bedrock adapters | Adapter files remain in source, but neither provider appears in the active provider selector. They are not supported active choices. |
| Legacy Caldera proxy/certificate controls | Some handlers and help text remain in source, but the visible Settings page is the authority. Use direct Morgana HTTPS configuration. |
| Legacy static Excalibur CDN path | Compatibility code exists, but the active simulation selector reads packages already installed in Morgana. |

### 2.3 Important product boundaries

- Merlino does **not** execute Morgana Tests, Scripts, Chains, or Campaigns.
- Merlino can create or update Morgana Chain definitions, read Agent intelligence, import Test evidence, and request Morgana-generated reports.
- Operators execute offensive content from Morgana under their own authorization and rules of engagement.
- AI is optional. Merlino does not automatically inherit a GitHub Copilot subscription or sign in on the user's behalf.
- Data is not guaranteed to remain local. Optional imports, synchronization, MISP, and AI features create network egress as described in this manual.

## 3. Architecture, Storage, and Network Flow

```text
Excel workbook
		|
		| Office.js table reads and writes
		v
Merlino taskpanes hosted by the official web deployment
		|
		+--> MITRE/GitHub/CDN data downloads
		+--> NIST NVD and optional CISA KEV helper
		+--> configured MISP server
		+--> configured Morgana server
		+--> configured cloud or local AI endpoint

Browser-host storage:
		localStorage + IndexedDB + OfficeRuntime.storage
```

### 3.1 What is stored in the workbook

Imported intelligence, selections, coverage values, Test evidence, Promptbook instructions, and AI output are stored in workbook cells and tables. Saving the workbook preserves that content in the `.xlsx` file.

### 3.2 What is stored outside the workbook

The Office web runtime stores configuration and cache data, including:

- Morgana URL and API key.
- MISP URL and API key.
- AI provider endpoint, model, deployment, and API key or token.
- Theme and toast preferences.
- First-run and Anacleto UI state.
- Coverage baseline selection.
- MITRE STIX cache in IndexedDB.
- Application logs in localStorage.
- Best-effort settings snapshots in OfficeRuntime storage.

This data belongs to the Office profile and web origin, not to a specific workbook. Clearing the Office/WebView cache can remove it.

### 3.3 Network egress

Network access depends on the feature used:

| Destination type | Data or purpose |
|---|---|
| Official Merlino deployment | Add-in pages, manifest, templates, version checks, and published support files |
| Microsoft Office.js CDN | Office Add-in runtime library |
| MITRE ATT&CK public data | STIX bundle download |
| Camelot GitHub content | Public Exploit-DB mapping and community references |
| NIST NVD | CVE queries and counts |
| CISA KEV helper | Optional KEV catalog retrieval through the configured companion path |
| MISP | Catalogue export, event search, and IOC import |
| Morgana | Health check, package/Chain synchronization, Agent intelligence, Test evidence, and reports |
| AI provider | Prompts assembled from selected workbook rows and report context |

## 4. Requirements

### 4.1 Excel and platform

Verified public installation files target Excel 2016 or later, Microsoft 365 Excel Desktop, and Excel on the web. The Windows trusted-catalog installer is Windows-specific. Availability of custom add-ins in managed Microsoft 365 tenants depends on organizational policy.

For the fullest workflow, use a current Excel Desktop build on Windows. In particular, **Open Local Template** depends on an Excel API that is unavailable in Excel on the web.

### 4.2 Browser and Office requirements

- JavaScript and Office Add-ins must be enabled.
- The Office host must reach the official Merlino deployment over HTTPS.
- The workbook must permit tables, formulas, and worksheet changes.
- Pop-up/download policy must allow report, JSON, script, and template downloads.
- For local or private services, the Excel webview must trust their TLS certificates and be allowed by CORS policy.

### 4.3 Optional integration requirements

| Feature | Requirement |
|---|---|
| Morgana | Reachable HTTPS server, trusted certificate, and purpose-specific API key |
| MISP | Reachable MISP base URL and automation key |
| Microsoft source extraction | PowerShell and a tenant application/account with the permissions stated by the downloaded script |
| Cloud AI | Provider account, API access, approved model, and credential |
| GitHub AI providers | A user-supplied GitHub token with the required service entitlement and scope |
| Ollama | Reachable OpenAI-compatible Ollama endpoint and installed model |

## 5. Install Merlino

Merlino is currently supported through custom Office Add-in installation. This manual does not claim Microsoft AppSource availability.

### 5.1 Install from the manifest URL

Use this path where Excel exposes **Add a custom add-in > Add from URL**:

1. Open Excel.
2. Open **Insert > My Add-ins** or **Office Add-ins**.
3. Select **Add a custom add-in > Add from URL**.
4. Enter the official production manifest URL:

	 ```text
	 https://merlino-addin.x3m.ai/manifest.xml
	 ```

5. Confirm the prompt.
6. Close and reopen Excel if the Merlino ribbon tab does not appear immediately.

The exact menu labels can vary by Excel release and tenant policy. If **Add from URL** is unavailable, ask the Microsoft 365 administrator to permit or deploy the custom manifest.

### 5.2 Windows trusted-catalog installation

The current Windows installer scripts download the production manifest into a per-user Merlino folder and register that folder as an Office trusted catalog under the current user's Office settings.

1. Obtain the official `INSTALL-MERLINO.bat` or installation package from the [Merlino portal](https://x3m.ai/merlino/).
2. Review the script according to organizational software policy.
3. Close Excel.
4. Run the installer as the intended Excel user. The current per-user catalog process does not require local administrator rights.
5. Reopen Excel.
6. Open **Insert > My Add-ins > Shared Folder**.
7. Select **Merlino**.

Do not modify and redistribute the manifest. Use only the current official deployment URL.

### 5.3 Excel on the web

Custom add-in availability is controlled by the tenant. Once Merlino is available, download a public template and open that workbook through **File > Open**. The **Open Local Template** button inside the taskpane is not supported in Excel on the web.

### 5.4 Verify installation

1. Confirm the **Merlino** ribbon tab appears.
2. Open **Settings** and confirm a version/build badge is displayed.
3. Open **Templates** and confirm the public template catalog loads.
4. Do not load a template into a workbook containing unsaved data.

## 6. First Run and Workbook Safety

### 6.1 Accept the first-run notice

The first taskpane opened displays a welcome overlay and Terms of Use checkbox. After acceptance, the state is saved in local storage and the overlay is suppressed across taskpanes. **About Merlino** in the taskpane information strip can reopen it.

### 6.2 Safe first-run procedure

1. Create a new blank workbook.
2. Save it under a new name before loading data.
3. Open **Templates**.
4. Choose the current Main or NIS2 public template.
5. Read the replacement warning.
6. Load the template only after confirming the workbook contains nothing that must be retained.
7. Save the populated workbook as a new version.

> [!DANGER]
> Template loading creates a temporary placeholder, deletes all existing worksheets, inserts every worksheet from the selected `.xlsx`, and removes the placeholder. Undo is not a recovery plan. Use a new or backed-up workbook.

### 6.3 Import safety

The following workflows can rebuild or replace destination data:

- Threat Groups, Campaigns, Software, Mitigations, Data Components, Detection Strategies, CVE, and ExploitDB imports delete and recreate their destination sheet.
- **Synchronize Tests** clears and rebuilds the Tests table from Morgana and resets `Pick` and `CrossPick`.
- Universal Catalogue JSON import replaces the current target-table data range.
- Repeated **Include Picks in Catalogue** runs can add duplicate business records because the operation appends selected rows.

Save a checkpoint before every bulk import, synchronization, or template change.

## 7. Ribbon Map

The active commands are organized into three workflow groups.

### 7.1 Operations

| Command | Purpose |
|---|---|
| Templates | Load official or local workbook templates |
| Sources | Import ATT&CK, Catalogue, Microsoft, Darktrace, TTP attribution, and Excalibur metadata |
| Agents | Read Morgana Agent intelligence, health, timeline, and relationship graph |
| Tests & Operations | Synchronize Chains and Tests, inspect analytics, and download Morgana reports |
| Exploit Database | Import filtered Exploit-DB records mapped to ATT&CK |
| IOC | Export Catalogue records to MISP and import/visualize MISP intelligence |
| Reports | Open the context-sensitive Main Coverage or Techniques report |

### 7.2 Logics

| Command | Purpose |
|---|---|
| AI Mission Engine | Configure the active AI provider and run Promptbooks |
| Runbooks | Run workbook recalculation, Smart View, Catalogue, reset, and analytic export workflows |
| Data Insights | Inspect the ATT&CK technique found in the selected cell |
| Attack Knowledge | Build a graph from selected rows and shared TCodes |

### 7.3 Help and administration

| Command | Purpose |
|---|---|
| Logs | Download or clear browser-stored Merlino logs |
| Anacleto | Search sheet, table, and taskpane guidance |
| Settings | Configure Morgana, MISP, UI preferences, theme, backups, and cache recovery |
| CVE Enrichment | Query NVD or CISA KEV and rebuild the CVE sheet |

### 7.4 Ribbon Refresh

The Refresh command runs a template-aware workbook refresh pipeline and reports status in the Excel status bar. It does not install templates, execute Morgana content, or replace the explicit Source import commands.

## 8. Workbook Schema

The current public Main template contains these sheets and tables.

### 8.1 Main Coverage

`Main Coverage` is a matrix, not a named Excel table. Each tactic occupies a five-column block:

1. Technique name and TCode.
2. Technique Coverage.
3. Data Components Coverage.
4. Test Coverage.
5. CrossPick.

Do not change the five-column block structure if you expect Update Core and Adaptive Reports to read it.

### 8.2 Techniques table

The `Techniques` sheet contains table `Techniques` with these columns:

```text
Pick | CrossPick | TCodes | Domain | Name | Technique Coverage |
Data Components Coverage | Test Coverage | No. Data Sources |
Data Sources Connected | Detections by Techniques | Url | Tactics |
Description | Detection | Platform | Data Sources | Is Sub-technique |
Sub-technique Of | Relationship Citations | STIX ID
```

### 8.3 Data Components table

The `Data Components` sheet contains table `Data_Components`:

```text
Pick | CrossPick | Component ID | Connected | Name | Description |
Platforms | Url | TCodes | STIX ID
```

### 8.4 Catalogue table

The `Catalogue` sheet contains table `Catalogue`:

```text
Pick | CrossPick | Name | Source | Priority | Enabled |
Validation_Score | Tests | Expected_Tests | Tests_Validated |
TCodes | Description | Notes | Data
```

`Data` is a JSON-bearing field used to preserve source-specific details. Treat it as potentially sensitive.

### 8.5 Tests table

The `Tests` sheet contains table `Tests`:

```text
Pick | CrossPick | TCodes | Name | Description | Exit Code | State |
Script | Date | Type | Agent | Duration | Created | Finished |
STDOUT | STDERR | AI Review | AI Summary | AI Fix | AI Signals |
AI Technique | AI Confidence | AI Model | AI At | DF Verdict |
DF Detected | DF Confidence | DF Matched | DF Candidates | DF Reason |
DF Updated | DF Outcome | Raw State | Detections | Marker |
Agent Executed | Agent Completed | ID
```

This table can contain command output, host information, AI interpretation, and Detection Fabric evidence. Protect the workbook accordingly.

### 8.6 IOC table

The shipped template and active MISP importer use table `IOC`. References to `IOCTable` in older help text are legacy. Its columns are:

```text
Pick | CrossPick | TCodes | Name | Source | Description | IPs | Domains |
Hashes | CVEs | Threat Actors | Campaigns | Risk Score | MISP Event ID |
MISP Event Link | Last Update | Related Events
```

### 8.7 Promptbooks table

The `Promptbooks` sheet contains table `Promptbooks`:

```text
Name | Description | Prompt | Table_Name | Input_Columns |
Output_Column | Enabled | Priority | Stats
```

### 8.8 Settings tables

The `Settings` sheet contains:

- `PickColor`: color code and minimum/maximum range metadata.
- `CrossPickTables`: table names participating in Pick/CrossPick workflows.
- `enterpriseattack`, `mobileattack`, and `icsattack`: tactic ordering metadata.

### 8.9 Dynamically created sheets

Source imports can create or recreate hidden `Threat Groups`, `Campaigns`, `Software`, `Mitigations`, and `Detection Strategies` sheets. CVE and ExploitDB create visible working sheets. Do not rename their tables or required columns unless the consuming workflow explicitly supports aliases.

## 9. Templates

### 9.1 Current public templates

The active catalog currently advertises:

| Template | Purpose |
|---|---|
| Main MITRE ATT&CK Template | General ATT&CK analysis across supported domains |
| NIS2 Compliance Template | NIS2-oriented workbook mapped to ATT&CK |

The ATT&CK domain is selected later in **Sources**; separate Enterprise, Mobile, and ICS workbook entries are not currently present in the public template catalog.

### 9.2 Load a public template

1. Start with a blank or backed-up workbook.
2. Open **Templates**.
3. Wait for **Public Templates** to load.
4. Select **Load** on the required template.
5. Confirm that the standard sheets and tables are present.
6. Save the workbook under a new name.

The catalog and workbook are downloaded from the official Merlino deployment.

### 9.3 Open a local template

On Excel Desktop:

1. Open **Templates > Open Local Template**.
2. Select an `.xlsx` file.
3. Confirm that replacing every current sheet is acceptable.
4. Wait for Main Coverage to become active.

On Excel on the web, download the public template and open the file through Excel's **File > Open** workflow instead.

## 10. Sources Overview

The Sources taskpane contains six active workflows:

1. Import a local Merlino Catalogue JSON file.
2. Download/cache and import MITRE ATT&CK STIX data.
3. Perform local TTP Attribution over the loaded STIX bundle.
4. Read Excalibur packages already installed in Morgana and import their Chains into Catalogue.
5. Download Microsoft extraction scripts whose output can be imported into Catalogue.
6. Import a Darktrace JSON export.

### 10.1 Local Catalogue JSON

The universal schema is:

```json
{
	"schema": {
		"version": "1.0",
		"type": "catalogue",
		"description": "<DESCRIPTION>",
		"created": "<ISO_8601_TIMESTAMP>"
	},
	"data": [
		{
			"Name": "<RECORD_NAME>",
			"Source": "<SOURCE_NAME>",
			"TCodes": "T1059.001",
			"Description": "<DESCRIPTION>"
		}
	]
}
```

The importer validates the schema, destination table, and field compatibility. At least three fields must match. It accepts aliases including `Techniques_Validated`, `Source_Techniques`, or `TCode` for `TCodes`; `Atomic_Tests` or `Caldera_Tests` for `Tests`; and `Cross_Pick` for `CrossPick`.

Current behavior writes the imported dataset into the target table and clears surplus existing rows. Treat this as replacement, not as a guaranteed append operation.

## 11. MITRE ATT&CK Imports

### 11.1 Select and cache data

1. Open **Sources > ATT&CK STIX Data**.
2. Select Enterprise, Mobile, or ICS.
3. Select an offered ATT&CK version.
4. Optionally select **Download STIX Datasets** to cache all domains in IndexedDB.
5. Select a Data Type.
6. Select **Import**.

**Clear Cache** removes the local STIX cache. The next import must download the bundle again.

### 11.2 Available ATT&CK data types

| Data type | Destination | Behavior |
|---|---|---|
| Techniques | Existing `Techniques` table | Appends a new domain when requested and deduplicates by TCode/STIX ID; preserves table structure |
| Groups | Hidden `Threat Groups` / `Threat_Groups` | Deletes and recreates the destination sheet |
| Campaigns | Hidden `Campaigns` / `Campaigns` | Deletes and recreates the destination sheet |
| Software | Hidden `Software` / `Software` | Deletes and recreates the destination sheet |
| Mitigations | Hidden `Mitigations` / `Mitigations` | Deletes and recreates the destination sheet |
| Data Components | `Data Components` / `Data_Components` | Deletes and recreates the destination sheet |
| Detection Strategies | Hidden `Detection Strategies` / `Detection_Strategies` | Deletes and recreates the destination sheet |

Importing a different domain for a recreated entity sheet replaces the prior content of that sheet. Plan multi-domain work accordingly.

## 12. Microsoft and Third-Party Imports

### 12.1 Microsoft sources

The visible Microsoft choices are:

- Microsoft Intune policies.
- Microsoft Defender for Office 365 policies.
- Microsoft Sentinel analytics rules.
- Microsoft Defender for Identity configurations.
- Microsoft Defender for Endpoint policies.

Selecting **Import** for one of these sources downloads the corresponding PowerShell extraction script. It does not directly authenticate to the tenant from the taskpane.

1. Download the script from **Sources**.
2. Review it and its required tenant permissions.
3. Run it in the authorized Microsoft environment.
4. Protect the generated JSON because policy and query content may be sensitive.
5. Return to **Sources > Import Catalogue Data**.
6. Import the generated JSON.

The visible Microsoft **Import by TTPs with Picks = TRUE** checkbox does not filter a script download. Filter the resulting Catalogue through the workbook workflow after import.

### 12.2 Darktrace NDR

1. Export supported Darktrace model data to JSON.
2. Open **Sources > Third-Party Platforms** and select Darktrace.
3. Optionally enable the Pick-based filter.
4. Select **Import** and choose the JSON file.

When filtering is enabled, Merlino collects TCodes from `Pick=TRUE` rows across `CrossPickTables` and keeps hierarchically matching Darktrace records. If no picked techniques or matches exist, the import is cancelled.

The Darktrace importer rebuilds its destination data. Back up any manual edits first.

## 13. Data Components and Detection Strategies

Data Components describe observable telemetry elements, such as process creation or network connection creation. Detection Strategies explain how a component can detect a particular technique.

### 13.1 Data Components workflow

1. Import ATT&CK Techniques.
2. Import **Data Components** for the same domain/version.
3. Set `Connected=TRUE` for components available in the organization.
4. Run **Update Core**.
5. Review `No. Data Sources`, `Data Sources Connected`, `Data Components Coverage`, and `Detections by Techniques` in Techniques.

### 13.2 Detection Strategies workflow

Import **Detection Strategies** when analysts need the ATT&CK detection method, component, source, platform, and technique relationship in a separate searchable table.

### 13.3 Interpretation limits

- A mapped component is a requirement, not proof that telemetry is collected correctly.
- `Connected=TRUE` is analyst-maintained state.
- A zero caused by missing mappings is not necessarily a confirmed visibility gap.
- Validate collection and alerting in the source security platform.

## 14. TTP Attribution

TTP Attribution analyzes the current STIX bundle locally; it does not require an AI provider.

1. Download or load the required ATT&CK STIX domain.
2. Enter comma-, space-, semicolon-, or newline-separated technique IDs.
3. Choose a 10-100 percent threshold.
4. Select a mode.
5. Select **Analyze TTPs**.
6. Review matching Threat Groups, Campaigns, and Software.
7. Select the entities to import.

### 14.1 Modes

| Mode | Purpose |
|---|---|
| Attribution | Weighted overlap plus description context and attribution indicators; distinctive TTPs weigh more and commodity TTPs can be penalized |
| Threat-Informed Defense | Emphasizes breadth of the input TTP set covered by an entity |
| Pure TTP Match | Simple technical overlap for transparent comparison |

Attribution scoring is analytical ranking, not proof of actor identity. Validate against time, victimology, infrastructure, malware, and independent intelligence.

Importing selected results recreates the corresponding Threat Groups, Campaigns, or Software sheet with the selected subset.

## 15. Excalibur Package Import

The active workflow uses packages already installed in Morgana.

1. Download the approved Excalibur package from the [Camelot Excalibur area](../morgana/excalibur/).
2. In Morgana, import it through **Scripts > Import Package**.
3. Configure and validate the package in Morgana.
4. In Merlino, configure Morgana under **Settings**.
5. Open **Sources > Excalibur Attack Simulations**.
6. Select the installed package and **Import**.

Merlino queries Morgana for installed packages, reads Chains belonging to the selected `package_id`, and creates one Catalogue row per Chain. The Catalogue row stores package and Chain metadata; it does not copy endpoint execution capability into Excel.

> [!IMPORTANT]
> Importing an Excalibur package into Merlino does not execute it. Merlino does not launch Morgana Tests or Chains. Execute approved content from the Morgana interface.

The legacy static package path is not the active selector workflow and should not be used as the operational procedure.

## 16. Pick, CrossPick, and Catalogue

### 16.1 Pick

Set `Pick=TRUE` to include a row in selection-driven analysis. Merlino accepts Boolean `TRUE` and common string/number equivalents, but use Excel Boolean values for consistency.

### 16.2 CrossPick

CrossPick is calculated by Smart View. Depending on the selected mode it represents normalized TCode frequency, entity overlap, gap rate, or normalized defense priority. It is not a universal probability or risk score.

### 16.3 CrossPickTables

`Settings!CrossPickTables` defines which named tables participate. Each participating table should contain:

- `Pick`.
- `CrossPick`.
- `TCodes` or a supported equivalent.
- Preferably `Name` and `Description` for Catalogue and graph workflows.

A table listed there but absent from the workbook is skipped by most analysis. A table omitted from the list does not participate even if it has compatible columns.

### 16.4 Include Picks in Catalogue

This runbook scans the configured tables, finds `Pick=TRUE` rows, and appends mapped rows to Catalogue. It sets Source to the originating table, initializes coverage fields, generates a record identifier where supported, and stores the source row as JSON in `Data`.

The runbook does not perform business-level deduplication. Review Catalogue before rerunning it with the same selection.

### 16.5 Catalogue as the defensive inventory

Catalogue combines controls, detection rules, policies, selected intelligence, and simulation metadata. Review these fields before coverage analysis:

- `Enabled`: whether the source control is intended to be active.
- `TCodes`: ATT&CK mappings used by all downstream calculations.
- `Expected_Tests`: expected validation count.
- `Tests` and `Tests_Validated`: derived Test counts.
- `Validation_Score`: derived assurance measure.
- `Data`: source-specific evidence, query, or metadata.

## 17. Runbooks

Runbooks can be selected together and run sequentially in the displayed order.

| Runbook | Current behavior |
|---|---|
| Update Core | Recalculates Test, technique, component, Catalogue, validation, and Main Coverage data |
| Smart View | Runs the selected Smart View analysis mode and writes colors/CrossPick values |
| Set All Picks False | Clears Pick in every configured CrossPick table, then refreshes Smart View |
| Include Picks in Catalogue | Appends selected rows from configured tables into Catalogue |
| Export Analytic Reports | Generates and downloads a single HTML analytics report from Main Coverage and Techniques |

Runbooks can make broad workbook changes. Save first, confirm required sheets/tables exist, and run one workflow at a time when diagnosing a problem.

## 18. Update Core

Update Core requires Main Coverage, Settings, Tests, Techniques, Data Components, and Catalogue. It runs these steps in order:

1. Calculate Test Coverage from Tests status.
2. Update Test totals in Catalogue.
3. Recompute Technique Coverage.
4. Align Technique Coverage from successful Tests.
5. Rebuild the Main Coverage tactic matrix.
6. Map required Data Components to Techniques.
7. Update validated Test counts in Catalogue.
8. Recompute detection validation scores.

If a step fails, later steps do not run. Open Logs, search by the correlation ID, correct the missing sheet/column/data issue, and run Update Core again.

Run Update Core after ATT&CK imports, Catalogue changes, Data Component connectivity changes, or Morgana Test synchronization.

## 19. Smart View

Choose a **Smart View Approach** in Runbooks before running **Smart View**.

### 19.1 Threat-Informed Defense

Counts how often selected TCodes occur across all configured Pick tables. For each matching row, CrossPick is its highest matching TCode frequency divided by the maximum selected frequency.

### 19.2 Attribution Analysis

For each row, calculates the percentage of that entity's TCodes found in the selected set:

$$
	ext{CrossPick} = \frac{\text{matching entity TCodes}}{\text{all entity TCodes}} \times 100
$$

### 19.3 Coverage Gap Analysis

Builds a threat set from picked Groups, Campaigns, and Software, then compares it with all TCodes in Catalogue:

- Red: the row contains at least one threat TCode absent from Catalogue.
- Green: the row contains threat TCodes and all are represented in Catalogue.
- White: the row is outside the selected threat set.

CrossPick is the fraction of matched threat TCodes that are gaps.

### 19.4 Priority Defense

Combines selected-TCode frequency with a 2x multiplier for TCodes absent from Catalogue, then normalizes the result to 0-100.

### 19.5 Standard Smart View color bands

Threat-Informed Defense, Attribution, and Priority Defense use:

| CrossPick score | Color | Meaning |
|---:|---|---|
| 0% | White | No current match |
| 1-39% | Light yellow | Lower relative score |
| 40-74% | Orange | Medium relative score |
| 75-100% | Red | Highest relative score |

These are relative analysis bands, not severity levels. Coverage Gap mode uses its separate red/green/white meaning.

## 20. Main Coverage

Update Core rebuilds Main Coverage from parent techniques in the Techniques table. Tactics follow the current ATT&CK order, including newer tactic names when present in imported data. Sub-techniques are not written as separate matrix rows.

Each technique row is styled using this priority:

| Color | Meaning |
|---|---|
| Dark red | At least one Test in the technique family has `ERROR` or `FAILED` |
| Orange | Technique Coverage equals the legacy `0.99` marker |
| Darker purple | Technique Coverage is greater than zero and no failed Test overrides it |
| Light purple | No calculated technique coverage |

These Main Coverage colors are not the same as Smart View's white/yellow/orange/red relative bands.

The four metrics beside each tactic are Technique Coverage, Data Components Coverage, Test Coverage, and CrossPick. Run Update Core before treating them as current.

## 21. Data Insights

Data Insights is the active cell-selection inspector.

1. Open **Data Insights**.
2. Select a cell containing a valid ATT&CK TCode.
3. Review technique name and ATT&CK link.
4. Review Technique, Data Source/Component, Test, and CrossPick metrics.
5. Expand sub-techniques, detection text, Data Sources, and failed/error Tests where available.

The panel reacts to the selected cell. A name without a recognizable `T####` or `T####.###` value produces **No technique detected**.

The older standalone `insights.ts` source is not built. References to a second active Insights taskpane are legacy.

## 22. Attack Knowledge

Attack Knowledge builds a force-directed relationship graph from `Pick=TRUE` rows in `CrossPickTables`.

- Entity nodes represent selected workbook rows.
- Technique nodes represent normalized ATT&CK IDs.
- Edges connect entities and techniques or entities that share techniques.
- Relationship-strength and graph-depth controls reduce or expand the graph.
- Selecting a node shows source table, CrossPick, TCodes, and connected edges.
- Pivot focuses the graph around a selected non-Technique entity.

Large selections can be capped for readability. The taskpane reports hidden/capped nodes when this occurs. Graph proximity is an analytical aid, not evidence of attribution or causation.

## 23. CVE Enrichment

### 23.1 Import from NIST NVD

1. Open **CVE Enrichment**.
2. Select Today, Last Week, Last Month, Last 90 Days, Last Year, or a custom date range.
3. Select severity values.
4. Optionally filter Attack Complexity, CVE ID, status, CWE name, description, or comma-separated TCodes.
5. Choose whether to include rejected records.
6. Leave **Automatic CWE to Techniques mapping** enabled when ATT&CK enrichment is required.
7. Select **Preview Count**.
8. Select **Import CVEs**.

Merlino queries NVD API 2.0 directly. The UI has no NVD API-key field, so public unauthenticated rate limits can apply. Large date ranges are chunked and may take significant time.

### 23.2 CISA KEV

Enable **Only CISA KEV vulnerabilities** to use the KEV path. The current browser implementation requires the companion local proxy because the CISA feed does not permit the required browser cross-origin request. If that helper is unavailable, use standard NVD import or an approved external export process.

### 23.3 Output and replacement behavior

The importer deletes and recreates the `CVE` sheet/table with:

```text
Pick | CrossPick | TCodes | CVE_ID | Published | LastModified | Status |
CVSS_Score | Severity | Attack_Vector | Attack_Complexity | CWE_IDs |
Name | Description | Affected_Products | Primary_Reference | CISA_KEV | Notes
```

CWE-to-TCode mappings are heuristic. Validate them against the vulnerability mechanism and ATT&CK semantics.

## 24. Exploit Database

The Exploit Database taskpane downloads a public mapped dataset from Camelot. The optional **AI-enriched dataset** is a pre-generated dataset; toggling it does not call the configured AI provider during import.

Available filters include:

- Publication date: week, month, 90 days, year, three years, all time, or custom.
- Platform: Windows, Linux, Multiple, Hardware, macOS, Unix, Android, or iOS.
- Type: Remote, Local, WebApps, or DoS.
- Mapping confidence.
- Has CVE.
- Has ATT&CK techniques.
- EDB ID, title, and author text.
- Pick-based TCode filtering.

**Import Exploits** deletes and recreates `ExploitDB`. **Clear Table** removes its current rows after confirmation.

The table contains source and download links plus mapped TCodes, CVEs, platform, type, author, confidence, and optional pre-generated AI fields. A public exploit reference is not authorization to retrieve, compile, or execute exploit code.

## 25. IOC and MISP

### 25.1 Configure MISP

1. Create a purpose-specific MISP automation key with the least privileges needed.
2. Open **Settings > MISP Configuration**.
3. Enter `<MISP_URL>` without a trailing slash.
4. Enter `<MISP_API_KEY>`.
5. Select **Check MISP**.
6. Select **Save MISP**.

### 25.2 Catalogue to MISP

**Catalogue to MISP** reads Catalogue rows and creates one MISP event per row, including ATT&CK tags and structured source content. Review the selected workbook data and MISP sharing-group/distribution policy before export.

### 25.3 Import from MISP

**Import from MISP** searches for events tagged as Merlino exports, extracts indicators and contextual entities, and writes them into the IOC table.

### 25.4 Import by Pick Criteria

1. Select rows across participating tables.
2. Choose **Preview Criteria**.
3. Review collected TCodes, threat actors/groups, campaigns, CVEs, and software.
4. Choose **Import by Pick Criteria**.

Merlino queries MISP for matching events. Broad criteria can return sensitive or high-volume results.

### 25.5 IOC graph

**Visualize IOC Clusters** builds an interactive graph of events and IP, domain, hash, CVE, threat-actor, and campaign nodes. It is a relationship view over the imported IOC data, not an independent enrichment engine.

## 26. Morgana Configuration

### 26.1 Configure the connection

1. In Morgana, create a purpose-specific named API key.
2. Trust the Morgana CA certificate on the Excel host.
3. Open **Settings > Morgana Configuration**.
4. Enter `<MORGANA_URL>`, including HTTPS scheme and port where required.
5. Enter `<MORGANA_API_KEY>`.
6. Select **Check Morgana**.
7. Select **Save Morgana**.

Do not use certificate-validation bypasses or a master key for routine integration.

### 26.2 Compatibility naming

Some internal modules and older help strings still use `Caldera` names. The active settings fields and integration target are Morgana. Do not infer that a visible legacy label enables an unsupported Caldera workflow.

### 26.3 Responsibility boundary

Merlino sends and receives API data. Morgana owns Scripts, Agents, Jobs, Tests, execution, cleanup, Detection Fabric, and server-side report generation. See the [Morgana User and Administrator Manual](../morgana/README.md).

## 27. Agents Intelligence

Agents Intelligence is read-only operational analysis over Morgana's Merlino API.

It provides:

- Time windows from minutes through seven days.
- Total, active, and inactive Agent counts.
- Host, platform, status, last-seen, risk, and health columns.
- Selected-Agent detail including identity, privilege, risk, and recent activity.
- A timeline with severity and event type.
- A relationship graph with depth and relationship-strength controls.

Select **Refresh** after changing the time window or graph controls.

Merlino does not deploy, configure, approve, remove, or run commands on Agents. Perform those tasks in Morgana.

## 28. Tests and Operations

### 28.1 Synchronize Chains

This one-way operation reads Catalogue, matches installed Morgana Scripts by TCode, and creates missing Chain definitions. Existing populated Chains are left unchanged; empty matching Chains can be populated. When no executable Script is available, compatibility knowledge-card placeholders may be created and a Chain can remain without executable content.

Synchronize Chains does not run a Chain.

### 28.2 Synchronize Tests

This one-way operation calls Morgana, clears the Merlino Tests table body, imports all returned Test rows, and resets `Pick` and `CrossPick`.

Imported fields include lifecycle, stdout/stderr, AI review, Detection Fabric verdict/evidence, correlation marker, Agent timing, and record ID when supplied by Morgana.

### 28.3 Intelligence dashboard

The dashboard provides:

- Tests Graph.
- Success Analysis.
- Health Matrix.
- Error Analytics.
- Real-Time Metrics.
- KPI summaries for Test counts, success/error state, Agents, AI review, and Detection Fabric outcomes.

These views analyze synchronized or API-returned evidence. They do not trigger endpoint execution.

### 28.4 Reports

- **Operational Report** becomes available after Test/operation data is loaded and generates a self-contained HTML analytics report from the current dashboard data.
- **Full Detection Report** requests the complete server-side operational/detection report from Morgana and downloads the returned HTML. No prior local sync is required.

Morgana remains the authority for raw Test and Detection Fabric records.

## 29. AI Mission Engine

The active AI Mission Engine has two functions: configure one active provider and run enabled Promptbooks.

### 29.1 Active provider choices

| Provider | Required fields | Operational notes |
|---|---|---|
| OpenAI | API key, model; endpoint can be reviewed | Direct provider billing; browser Test Connection is available |
| Anthropic Claude | API key, model, endpoint | Browser Test Connection is disabled because of CORS; saved configuration can still be used where the runtime permits |
| Azure OpenAI | Resource endpoint, API key, Deployment Name, API Version | Deployment Name is used for the request route |
| Microsoft Foundry | OpenAI-compatible Foundry endpoint, API key, Deployment Name | Uses the v1-compatible route and does not use an Azure OpenAI API Version parameter |
| GitHub Copilot | User-supplied GitHub token and model | Merlino does not discover or reuse an IDE subscription automatically; access and billing/entitlement depend on the GitHub account |
| GitHub Models | User-supplied GitHub token and model | Service tier and rate limits are controlled by GitHub |
| Ollama | Endpoint and installed model | No API key required by default; browser Test Connection is available |
| Custom | OpenAI-compatible endpoint, model, and key if required | CORS and response compatibility must be validated by the administrator |

Mistral and AWS Bedrock adapter source files are legacy/dormant and are not active provider-selector choices.

### 29.2 Configure a provider

1. Open **AI Mission Engine**.
2. Select **Configure**.
3. Select the provider.
4. Enter the endpoint, model, key/token, Deployment Name, and API Version fields shown for that provider.
5. Use **Test Connection** when enabled.
6. Select **Save & Apply**.
7. Verify the Active Provider card.

For providers whose Test Connection is disabled, run a one-row, non-sensitive Promptbook test and verify the output and provider-side usage record.

### 29.3 Credential handling

Provider credentials are stored in browser localStorage and are not protected by an operating-system credential vault. Restrict access to the Office profile, do not use shared Windows accounts, and rotate credentials after suspected cache/profile compromise.

## 30. Promptbooks

Promptbooks are workbook-controlled batch instructions. **Start AI Review** reads enabled rows in ascending Priority order.

### 30.1 Columns

| Column | Meaning |
|---|---|
| Name | Human-readable instruction name |
| Description | Operator purpose and scope |
| Prompt | Prompt template; `[ColumnName]` placeholders are replaced from each target row |
| Table_Name | Named Excel table to process |
| Input_Columns | Columns documented as inputs and included in the generated review report |
| Output_Column | Existing target column where the primary response is written |
| Enabled | `FALSE`, `NO`, or `0` disables the row; other values are treated as enabled |
| Priority | Numeric ascending execution order |
| Stats | Completion/error summary written by the engine |

### 30.2 Execution behavior

1. Validate the active provider.
2. Read enabled Promptbooks.
3. Find the target table and output column.
4. If the table has a Pick column, process only `Pick=TRUE` rows. If no Pick column exists, every row is processed.
5. Replace `[ColumnName]` placeholders with values from that row.
6. Call the provider sequentially for each row.
7. Write the primary response to `Output_Column`.
8. Update Promptbook Stats.
9. Enable **AI Review Report** for the completed session.

### 30.3 Cost and volume warning

The current engine makes one primary call plus four additional Purple Team intelligence calls for each selected row. After row processing, it can make up to three additional synthesis calls from successful output.

For $r$ selected rows, the normal upper call count is approximately:

$$
5r + 3
$$

There is no preflight cost estimator, budget cap, or token-usage total in the active Promptbooks UI. Provider limits and charges apply. Start with one row, inspect provider usage, and scale only after estimating the cost.

### 30.4 Promptbook privacy and safety

- The final prompt can contain values from every column in the selected row because placeholder substitution is based on the full row.
- The engine also sends generated output into follow-up adversary, detection, CTI, and Merlino/Morgana prompts.
- The report can contain input values, final prompts, provider output, and generated offensive examples.
- Do not process credentials, private keys, personal data, customer identifiers, unrestricted telemetry, or production secrets.
- Treat generated commands, mappings, and intelligence as untrusted suggestions requiring human review.

## 31. Adaptive Reports

Adaptive Reports detects the active worksheet:

- On **Techniques**, it shows the Techniques dashboard.
- Otherwise, it attempts to load Main Coverage and shows the tactic radar report.

### 31.1 Main Coverage report

The report includes KPI cards and a radar view for Technique Coverage, Data Components Coverage, Test Coverage, and CrossPick by tactic. It compares actual values with the selected baseline and automatically requests AI interpretation when a provider is configured.

### 31.2 Techniques dashboard

The dashboard includes:

- Total and average coverage KPIs.
- Tactic comparison bars.
- Coverage-band distributions.
- Technique Coverage versus Test Coverage scatter plot with Data Component context.
- Tactic/coverage heatmap.
- Prioritized validation-debt techniques.
- AI summary, tactic/distribution/relationship analysis, and per-technique drill-down.

Missing, partial, not-mapped, and error Data Component states are kept distinct. A missing mapping is not treated as proven zero telemetry.

### 31.3 Baselines

| Profile | Technique | Data Components | Tests | CrossPick |
|---|---:|---:|---:|---:|
| Minimum | 50% | 50% | 30% | 20% |
| Standard | 60% | 60% | 40% | 25% |
| Mature | 75% | 75% | 60% | 40% |
| Custom | Operator-defined | Operator-defined | Operator-defined | Operator-defined |

The selected baseline is saved in localStorage. It is a comparison target, not an industry certification threshold.

### 31.4 AI behavior

Opening or refreshing a supported Adaptive Report automatically requests AI analysis when a provider is configured. Changing the baseline also triggers a new analysis. **Refresh AI** forces another request. These actions can create provider cost and data egress.

### 31.5 Exports

| Export | Behavior |
|---|---|
| Export as PNG | Captures the full taskpane at 2x scale and downloads a PNG |
| Export as HTML | Embeds a captured PNG in a standalone HTML file; suitable for offline viewing and printing |
| Runbooks > Export Analytic Reports | Builds a data-driven HTML report with embedded data but loads ECharts from a public CDN; charts require network access unless the dependency is made local |
| Tests & Operations reports | Export operational or full detection evidence sourced from Morgana |

Review every export for workbook, Test, detection, host, and AI content before sharing.

## 32. Settings Reference

### 32.1 Top actions

| Field/action | Meaning |
|---|---|
| Save Settings | Copies supported local settings into OfficeRuntime storage |
| Export Settings | Downloads the supported settings as JSON |
| Import Settings | Restores supported settings from a JSON export |

### 32.2 Morgana Configuration

| Field/action | Meaning |
|---|---|
| Morgana Server URL | HTTPS base URL of the Morgana server |
| API Key | Purpose-specific Morgana key |
| Check Morgana | Calls the Merlino compatibility health route and reports version/status |
| Save Morgana | Persists URL and key in localStorage and triggers best-effort backup |

### 32.3 MISP Configuration

| Field/action | Meaning |
|---|---|
| MISP Server URL | MISP base URL without trailing slash |
| MISP API Key | MISP automation key |
| Check MISP | Calls the MISP version endpoint |
| Save MISP | Persists URL and key in localStorage and triggers best-effort backup |

### 32.4 Backup & Restore

| Field/action | Meaning |
|---|---|
| Last Backup | Timestamp of the browser-stored automatic backup |
| AI Providers count | Count from the legacy AI configuration collection |
| Export All Settings | Downloads the legacy-supported AI configs, theme, Morgana, and MISP settings |
| Import Settings | Reads that JSON format and merges supported values |
| Restore from Auto-Backup | Restores the browser/session backup when present |

### 32.5 UI Preferences

| Field | Range/default |
|---|---|
| Info Messages Duration | 1-60 seconds; default 12 |
| Error Messages Duration | 1-60 seconds; default 20 |
| Save UI Preferences | Persists current values |
| Reset to Defaults | Restores defaults |

### 32.6 Theme Customization

The visible color fields are Background Taskpanes, Background Panels, Background Tables, Text Color, Accent Color, Border Color, and Secondary Text. Each supports a color picker and hexadecimal value. **Save Theme** persists the values; **Reset to Default** restores the standard theme. Other taskpanes update when reopened.

### 32.7 Troubleshooting

**Download Cache Clear Script** downloads a Windows batch file that closes Office applications and clears Office Add-in/WebView cache locations. Save every open document and export required settings before running it.

### 32.8 Current settings limitations

- There is no visible proxy, Microsoft Graph credential, licensing, or AI provider form in Settings. AI providers are configured in AI Mission Engine.
- The active per-provider AI store is not included in the current legacy JSON backup or OfficeRuntime snapshot key list. Revalidate and, where necessary, re-enter AI provider settings after cache reset, profile migration, or reinstall.
- Settings export files can contain Morgana/MISP keys and legacy AI credentials in plaintext JSON. Store them as secrets.
- OfficeRuntime backup is best-effort and is not a substitute for a tested export and workbook backup.
- Settings backup does not contain workbook sheets, imported data, reports, or external-server data.

## 33. Anacleto, Logs, Ribbon Refresh, and Custom Functions

### 33.1 Anacleto

The Anacleto taskpane provides searchable guidance under Sheets, Taskpanes, and Tables. Mini-Anacleto panels in taskpanes update their help when the pointer moves over supported controls. Help content can lag current implementation; when a label conflicts with actual visible controls, this manual and the active UI take precedence.

### 33.2 Logs

Merlino logs are browser-stored records, not operating-system files at the displayed pseudo-path.

- **Refresh** reloads the list.
- **Open** downloads one log as a text file.
- **Clear All Logs** deletes all Merlino log keys and the current-session marker from localStorage.
- Each log storage key is capped at roughly 512 KiB; older content is trimmed when necessary.

Logs can contain workbook names, source URLs, record metadata, provider errors, and integration context. Sanitize them before sharing.

### 33.3 Ribbon Refresh

The ribbon Refresh command runs the template-aware workbook refresh logic and writes progress to Excel's status bar. Use explicit Runbooks when you need a predictable named sequence and explicit taskpane status.

### 33.4 Custom functions

The production bundle contains these utility functions:

- `ADD(first, second)`.
- `CLOCK()` streaming current time.
- `CURRENTTIME()` is an internal helper and is not registered as a custom function.
- `INCREMENT(incrementBy)` streaming counter.
- `LOG(message)` writes to the browser console and returns the message.

They are generic utility/sample functions, not CTI calculations and not required by the standard workflow.

## 34. Privacy and Security

### 34.1 Data does not always stay local

Merlino has no required Merlino application account, but that does not mean every workflow is local. Data leaves the workbook when the operator uses MISP export/search, Morgana synchronization/reporting, cloud AI, public-data imports, template downloads, or update checks.

### 34.2 AI egress

Cloud AI requests can contain selected workbook fields, generated prompts, Script/Test context, coverage values, and prior AI output. Review provider retention, training, geography, and contractual controls before use.

Ollama can keep model inference on a controlled local endpoint, but Merlino still stores configuration/output locally and other enabled features can use the network.

### 34.3 Credential storage

Morgana, MISP, and AI credentials are stored in browser-accessible localStorage, not in an OS credential vault. Morgana/MISP and legacy AI values can also appear in OfficeRuntime snapshots or exported JSON; the current active-provider AI store is omitted by those backup paths.

Administrator controls should include:

- Dedicated user profiles on managed endpoints.
- Least-privilege, purpose-specific API keys.
- TLS trust and hostname validation for private services.
- Restricted access to settings exports and workbooks.
- Credential rotation after export, cache, or device compromise.
- DLP review for workbooks and reports.

### 34.4 Workbook and report sensitivity

Workbooks and exports can contain attack mappings, control gaps, MISP intelligence, command output, host names, Detection Fabric evidence, and AI-generated offensive material. Classify, encrypt, retain, and share them under organizational policy.

### 34.5 Responsible use

Merlino analysis does not grant authorization to test a system. Any execution in Morgana or use of exploit material requires explicit written authorization, approved targets, a controlled network, and an exercise cleanup plan.

## 35. Backup, Restore, and Administration

### 35.1 Back up a workbook

1. Save the `.xlsx` before template loading or bulk import.
2. Create a timestamped copy before Update Core, synchronization, or a large Promptbook run.
3. Store sensitive workbooks in an approved encrypted repository.
4. Test that the backup opens and retains named tables.

### 35.2 Back up settings

1. Open Settings.
2. Select **Export All Settings**.
3. Store the JSON as a credential-bearing secret.
4. Separately record the active AI provider configuration in the approved secret manager because the current exporter may omit it.
5. Select **Save Settings** to refresh the best-effort OfficeRuntime snapshot.

### 35.3 Restore settings

1. Open Settings.
2. Select **Import Settings** and choose the trusted JSON file, or use **Restore from Auto-Backup**.
3. Reopen taskpanes.
4. Re-enter and test the active AI provider if it was not restored.
5. Test Morgana and MISP.
6. Delete temporary plaintext settings exports when policy requires.

### 35.4 What settings backup does not restore

- Workbook sheets, tables, formulas, or imported data.
- MITRE IndexedDB cache.
- All log history.
- External Morgana/MISP records.
- Guaranteed active-provider configuration from the current AI Mission Engine.

### 35.5 Update administration

Merlino checks its published version metadata and loads code from the configured production deployment. For managed tenants, administrators should control manifest deployment, origin allowlists, update review, and rollback through Microsoft 365 change management. Always retain a workbook backup before opening a materially updated add-in against an important workbook.

### 35.6 Remove or reset Merlino

- Remove the custom add-in through Excel or the tenant deployment method.
- For a Windows trusted catalog, remove the Merlino entry through the same approved per-user deployment process.
- Cache-clearing is separate from uninstall and can erase local configuration.
- Removing the add-in does not delete data already saved in `.xlsx` workbooks or data stored in Morgana/MISP.

## 36. Troubleshooting

### 36.1 Installation and loading

| Symptom | Action |
|---|---|
| Merlino is not in the ribbon | Reopen Excel, verify the custom manifest/trusted catalog is allowed, and confirm the production host is reachable |
| Add from URL is absent | Ask the Microsoft 365 administrator to permit or centrally deploy the custom add-in |
| Blank or stale taskpane | Save work, export settings, run the downloaded cache-clear tool, reopen Excel, and re-add the manifest if required |
| Public templates do not load | Verify HTTPS access to the official Merlino template catalog |

### 36.2 Workbook and imports

| Symptom | Action |
|---|---|
| Required sheet/table not found | Load the current template and do not rename required tables |
| Imported sheet lost manual edits | Restore the workbook backup; the importer rebuilds that destination |
| Catalogue JSON rejected | Verify `schema.version`, supported `schema.type`, `schema.description`, `schema.created`, `data[]`, and at least three matching fields |
| Smart View shows no color | Verify `Pick=TRUE`, valid TCodes, and the table name in `CrossPickTables` |
| Duplicate Catalogue rows | Restore/deduplicate manually and avoid rerunning Include Picks with the same selection |
| Update Core stops | Check the named failing step and required core sheets in Logs |

### 36.3 CVE and Exploit Database

| Symptom | Action |
|---|---|
| NVD rate limit or timeout | Reduce the date range and retry after the public API window resets |
| KEV import fails | Verify the companion local proxy is running and can reach the CISA feed |
| No mapped CVE techniques | Enable enrichment and verify the CVE has mapped CWE values; mappings remain heuristic |
| Exploit dataset fails | Allow HTTPS access to Camelot public content and the official Merlino deployment for the selected dataset |
| Pick-filtered exploit import is empty | Verify selected rows have valid TCodes and are listed in CrossPickTables |

### 36.4 Morgana and MISP

| Symptom | Action |
|---|---|
| Check Morgana fails | Verify URL, key, TLS trust, firewall, and Morgana health from the Excel host |
| Agent dashboard is empty | Confirm Morgana has enrolled Agents and the configured key can read the Merlino intelligence API |
| Synchronize Chains creates empty Chains | Install matching Morgana Scripts for the Catalogue TCodes |
| Synchronize Tests removed local selections | Expected: it rebuilds Tests and resets Pick/CrossPick; restore a workbook copy if those selections were needed |
| MISP 401 | Replace the automation key and retest |
| MISP browser/CORS error | Configure MISP reverse proxy/CORS for the Merlino origin without disabling TLS validation |

### 36.5 AI and reports

| Symptom | Action |
|---|---|
| Test Connection is disabled | This is expected for providers blocked by browser CORS; use a one-row non-sensitive Promptbook validation |
| GitHub Copilot fails | Supply an eligible token explicitly; an IDE subscription is not discovered automatically |
| Promptbook processes too many rows | Add/verify the Pick column and set only intended rows to TRUE before starting |
| AI output column not found | Correct `Output_Column` to an existing column in the named target table |
| Unexpected provider bill | Remember that one row can produce five calls plus session-level synthesis; stop and review provider usage |
| Adaptive Report shows no data | Activate Techniques or populate Main Coverage with Update Core, then Refresh |
| Runbook HTML has blank charts offline | It loads ECharts from a CDN; use Adaptive Report HTML for an offline image-based snapshot |

### 36.6 Logs and storage

| Symptom | Action |
|---|---|
| Settings disappeared after cache clear | Import the protected settings export or use OfficeRuntime restore, then re-enter the active AI provider |
| Log list is empty | Logs are session/browser storage records and may have been cleared, trimmed, or created under another Office profile/origin |
| localStorage quota errors | Export required logs/settings, clear old logs, and retry |

## 37. FAQ

### Is Merlino available from Microsoft AppSource?

This manual does not claim AppSource availability. Use the verified custom manifest or Windows trusted-catalog installation path approved by your administrator.

### Does Merlino require an account?

The add-in does not require a Merlino application account. External providers and integrations can require their own accounts and credentials.

### Does all data stay inside Excel?

No. Workbook processing is client-side, but enabled imports, MISP, Morgana, cloud AI, templates, and update checks communicate with external services.

### Does GitHub Copilot work automatically because I use Copilot in VS Code?

No. Merlino requires an explicitly configured token and compatible service entitlement. It does not automatically reuse the IDE session or subscription.

### Can Merlino execute a Morgana Test or Chain?

No. Merlino synchronizes definitions and evidence. Execute Scripts, Chains, Campaigns, and Tests in Morgana.

### Can I load a template into an existing workbook safely?

Only if every existing sheet may be deleted. The recommended procedure is a new or fully backed-up workbook.

### Why did a source import replace a sheet?

Most ATT&CK entity importers and the CVE/Exploit importers deliberately delete and recreate their destination sheet for performance and schema consistency.

### Is CrossPick a risk probability?

No. Its meaning depends on the selected Smart View mode. It is a relative score used for prioritization and filtering.

### Is AI required for coverage calculations?

No. Update Core, Smart View, Main Coverage, Data Insights, and Attack Knowledge have deterministic workbook logic. AI adds optional interpretation and Promptbook output.

### Is the AI-enriched Exploit Database generated live?

No. It selects a pre-generated published dataset. It does not call the active AI provider during import.

### Are settings exports encrypted?

No. Treat them as plaintext credential backups.

### Is a report a complete backup?

No. Reports are presentation/evidence artifacts. Back up the workbook and external systems separately.

## 38. Glossary

| Term | Meaning |
|---|---|
| ATT&CK | MITRE knowledge base of adversary tactics and techniques |
| TCode | ATT&CK technique or sub-technique ID |
| Pick | Analyst Boolean selection used by cross-table workflows |
| CrossPick | Mode-dependent normalized relevance, overlap, gap, or priority score |
| Catalogue | Merlino inventory of controls, rules, selected intelligence, and simulation metadata |
| Data Component | Observable telemetry element associated with ATT&CK detection |
| Detection Strategy | ATT&CK guidance connecting a technique to detection data and method |
| Promptbook | Workbook row describing an AI prompt, target table, inputs, output, and execution priority |
| Adaptive Report | Context-sensitive Main Coverage or Techniques report |
| Excalibur Pack | Morgana package of Scripts, Chains, and tag metadata |
| Script | Morgana atomic execution unit |
| Chain | Morgana ordered Script flow |
| Test | Morgana execution record synchronized into Merlino |
| Agent | Morgana endpoint service; Merlino displays intelligence but does not administer execution |
| Detection Fabric | Morgana evidence-correlation subsystem whose results can be imported into Tests |

## 39. References

- [Merlino portal](https://x3m.ai/merlino/)
- [Getting Started](../docs/merlino/getting-started.md)
- [Community templates](../standard-templates/)
- [Lab 01: Create Organization Threat Profile](../laboratories/Merlino%20User%20Guide-Lab%2001--Create-Organization-Threat-Profile.md)
- [Lab 02: Microsoft Sentinel Detection Coverage](../laboratories/Merlino%20User%20Guide-Lab%2002--Microsoft%20Sentinel%20Detection%20Coverage.md)
- [Lab 03: Red Team Testing with Morgana Arsenal](../laboratories/Merlino%20User%20Guide-Lab%2003--Red%20Team%20Testing%20with%20Morgana%20Arsenal.md)
- [Morgana User and Administrator Manual](../morgana/README.md)
- [Camelot community discussions](https://github.com/x3m-ai/Camelot/discussions)
- [MITRE ATT&CK](https://attack.mitre.org/)
- [NIST National Vulnerability Database](https://nvd.nist.gov/)
- [CISA Known Exploited Vulnerabilities Catalog](https://www.cisa.gov/known-exploited-vulnerabilities-catalog)
- [MISP Project](https://www.misp-project.org/)

---

Merlino is developed by [X3M.AI Ltd](https://x3m.ai). Use external integrations only with approved data, credentials, and authorization.
