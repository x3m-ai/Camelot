# Morgana User and Administrator Manual

> **Applies to:** Morgana 0.4.0 (27 August 2026)  
> **Audience:** Red Team operators, Purple Teams, Detection Engineers, SOC analysts, and Morgana administrators  
> **Product status:** Controlled distribution. Use only in environments covered by explicit written authorization.

Morgana is an adversary-emulation and detection-assurance platform. A Windows server coordinates endpoint Agents, Scripts, Chains, Campaigns, Tests, detection evidence, reports, and optional AI services through an HTTPS web interface and REST API.

> [!CAUTION]
> Morgana can execute PowerShell, command-shell, Bash, and Python content with the privileges of the Agent service. It also provides an interactive remote Console. Never expose Morgana to the public Internet. Place it on a dedicated, access-controlled test network and use it only against systems included in an approved rules-of-engagement document.

This public manual intentionally contains no passwords, API keys, tokens, tenant identifiers, or customer-specific values. Text such as `<MORGANA_API_KEY>` is a placeholder.

## Table of Contents

1. [Product Overview](#1-product-overview)
2. [Architecture and Network Flow](#2-architecture-and-network-flow)
3. [Requirements and Supported Platforms](#3-requirements-and-supported-platforms)
4. [Install the Morgana Server](#4-install-the-morgana-server)
5. [First Launch, Sign-In, and TLS](#5-first-launch-sign-in-and-tls)
6. [Authentication, Users, and API Keys](#6-authentication-users-and-api-keys)
7. [Dashboard and Navigation](#7-dashboard-and-navigation)
8. [Agents](#8-agents)
9. [Scripts](#9-scripts)
10. [Excalibur Packs](#10-excalibur-packs)
11. [Tags and Workspaces](#11-tags-and-workspaces)
12. [Chains](#12-chains)
13. [Tests and Jobs](#13-tests-and-jobs)
14. [Campaigns](#14-campaigns)
15. [Detection Fabric](#15-detection-fabric)
16. [Reports and Portable Exports](#16-reports-and-portable-exports)
17. [AI Mission Engine](#17-ai-mission-engine)
18. [Automation Center](#18-automation-center)
19. [Settings Reference](#19-settings-reference)
20. [Merlino Integration](#20-merlino-integration)
21. [REST API for Operators](#21-rest-api-for-operators)
22. [Logs and Diagnostics](#22-logs-and-diagnostics)
23. [Backup, Restore, and Disaster Recovery](#23-backup-restore-and-disaster-recovery)
24. [Upgrade the Server](#24-upgrade-the-server)
25. [Uninstall](#25-uninstall)
26. [Security and Responsible Operation](#26-security-and-responsible-operation)
27. [Troubleshooting](#27-troubleshooting)
28. [FAQ](#28-faq)
29. [Accessibility and Keyboard Use](#29-accessibility-and-keyboard-use)
30. [Glossary](#30-glossary)
31. [References](#31-references)

## 1. Product Overview

Morgana turns approved adversary behavior into repeatable, evidence-producing exercises:

1. Install the Morgana Server on a protected Windows host.
2. Enroll Agents on authorized Windows or Linux targets.
3. Install Excalibur Packs or create custom Scripts.
4. Execute a Script, Chain, Campaign, or schedule.
5. Inspect the resulting Test and Job output.
6. Ingest SOC telemetry through Detection Fabric.
7. Correlate Tests with detections and review the evidence.
8. Export a portable evidence report or generate an AI-assisted Intelligent Report.

### 1.1 Current product edition

Morgana 0.4.0 has one installed server product. The implementation does not expose separate Community, Enterprise, or licensed feature editions. Some capabilities are optional because they depend on external services:

- Excalibur catalog access requires HTTPS access to the public Camelot GitHub content.
- Defender XDR ingestion requires a Microsoft Entra application and Microsoft Graph permissions.
- AI features require a configured cloud provider or a local inference service.
- Merlino integration requires the Merlino Excel Add-in.

The server is Windows-only. Linux is supported as an Agent platform, not as a Morgana Server platform.

### 1.2 Core terminology

| Term | Meaning |
|---|---|
| **Script** | One atomic execution unit, including its command, executor, platform, optional runtime tags, and cleanup command. |
| **Chain** | An ordered flow of Script nodes with optional IF/ELSE branches. |
| **Test** | One recorded execution instance. It stores lifecycle, target, output, timing, AI review, and Detection Fabric results. |
| **Campaign** | A larger exercise flow containing Chains, Scripts, branches, and parallel groups. |
| **Agent** | The endpoint service that polls Morgana, executes Jobs, and returns results. |
| **Job** | The internal server-to-Agent dispatch record for a Test. |
| **Excalibur Pack** | A versioned package of Scripts, Chains, and runtime tag metadata distributed through Camelot. |
| **Detection** | A normalized alert, incident, event, or finding ingested by Detection Fabric. |

### 1.3 Installed product versus development use

This manual documents the installed Morgana product. Administrators should use the installer, Windows Services, the web UI, and the public REST API. Source-tree commands, development restart scripts, Python virtual environments, build commands, and release-publishing scripts are not installed-product procedures and are intentionally excluded.

## 2. Architecture and Network Flow

```text
Operator browser / Merlino
          |
          | HTTPS TCP 8888
          v
Morgana Server (Windows service)
          |
          | Agent long polling over HTTPS
          v
Windows or Linux Agent service
          |
          | local process execution
          v
Authorized target host

Optional server egress:
  - Camelot on GitHub: Excalibur catalog and version metadata
  - Microsoft Graph: Defender XDR detections
  - Configured AI provider: reviews, detection analysis, and reports
```

### 2.1 Default ports and direction

| Flow | Direction | Default | Purpose |
|---|---|---|---|
| Browser or Merlino to server | Inbound to server | TCP 8888, HTTPS | UI and API |
| Agent to server | Outbound from target | TCP 8888, HTTPS/WSS | Registration, long poll, results, heartbeat, Console |
| Server to GitHub | Outbound from server | TCP 443 | Catalog and update metadata |
| Server to Microsoft Graph | Outbound from server | TCP 443 | Defender XDR ingestion |
| Server to cloud AI | Outbound from server | TCP 443 | Optional AI calls |
| Server to Ollama or LM Studio | Server-local or controlled LAN | Provider-specific | Optional local AI |

Agents require no inbound listening port. Restrict server TCP 8888 to approved operator, Merlino, and Agent source networks.

### 2.2 Persistent data

The installed product keeps runtime state below `%ProgramData%\Morgana`. This includes the SQLite database, certificates, server and Agent logs, backups, configuration, provider credentials, detection data, and temporary execution files. Treat the entire directory as sensitive.

The program files are installed below `%ProgramFiles%\Morgana Server` on a standard 64-bit Windows installation.

## 3. Requirements and Supported Platforms

### 3.1 Server

- 64-bit Windows capable of running the Morgana installer and a Windows service.
- Local administrator rights for installation, service changes, firewall changes, and certificate trust.
- A modern browser with JavaScript and local storage enabled.
- TCP 8888 available, unless the installed service was explicitly configured for another port.
- Outbound HTTPS to the services used by your deployment.
- Sufficient disk for the database, Test output, detections, logs, and backups.

No authoritative fixed RAM or disk minimum is enforced by the current application. Size the host for expected Agent count, Test history, Detection Fabric retention, and report volume.

### 3.2 Agents

| Platform | Current support | Service | Typical executors |
|---|---|---|---|
| Windows | Supported | `MorganaAgent` Windows service, automatic start | PowerShell, `cmd`, Python if installed, manual |
| Linux | Supported when the Linux binary is present on the server | `morgana-agent.service` under systemd | Bash/`sh`, Python if installed, manual |
| macOS | Not currently supported as an installed service | None | UI filters exist, but no working macOS service installer is provided |

An executor must exist on the target. Selecting Python does not install Python. Platform metadata does not prevent an operator from choosing an incompatible Agent, so verify the Script before execution.

Server and Agent versions are independent. The Morgana 0.4.0 source declares Agent version 0.2.0; verify the version shown in the Agents table after every deployment.

## 4. Install the Morgana Server

Morgana is controlled-distribution software. Obtain the current installer through the approved X3M.AI channel or the authorized [release directory](Install/).

### 4.1 Pre-install checklist

1. Confirm written authorization and the target scope.
2. Select a dedicated Windows host on a protected network.
3. Confirm TCP 8888 is available.
4. Define which operator and Agent networks may reach the port.
5. Prepare a protected backup destination.
6. Verify the installer source and publisher according to your software-assurance process.

### 4.2 Interactive installation

1. Sign in to Windows with an account that can elevate locally.
2. Right-click `Morgana-Server-Setup.exe` and select **Run as administrator**.
3. Review the license and installation destination.
4. Optionally select the desktop Dashboard shortcut.
5. Complete the wizard and wait for the post-install configuration to finish.
6. Keep the final page open long enough to record the bootstrap sign-in information in an approved password vault. This manual does not reproduce it.

The installer performs these actions:

- Installs the 64-bit server and bundled Windows Agent binary.
- Creates the `Morgana` Windows service under `LocalSystem`.
- Sets the service to start automatically and configures restart-on-failure actions.
- Creates the persistent data, database, log, certificate, and configuration directories.
- Generates a random master API key, saves it under the protected Morgana configuration directory, and supplies it to the service.
- Opens an inbound Windows Firewall rule for TCP 8888. The generated rule is not source-address restricted; scope it immediately after installation.
- Attempts to add `%ProgramData%\Morgana` to Microsoft Defender exclusions.
- Starts the server.
- Generates a Morgana root CA and server certificate on first start.
- Trusts the Morgana root CA on the server host.

> [!IMPORTANT]
> The account and password shown by the 0.4.0 installer are fixed bootstrap values, not per-installation credentials. Change the password locally before allowing remote access. The installer finish page also contains an obsolete instruction to download Atomic Red Team content with **Refresh Canary Scripts**. Ignore it; the current workflow is **Scripts > Excalibur Script Packs > Refresh catalog**.

> [!WARNING]
> A broad antivirus exclusion weakens host protection. Use a dedicated lab server, restrict access to the directory, and confirm the exclusion against organizational policy. Do not add exclusions to production endpoints merely to make an exercise succeed.

### 4.3 Verify the service

Open an elevated PowerShell window on the server:

```powershell
Get-Service -Name Morgana
```

Expected result: the service exists and its status becomes `Running`.

Then open:

```text
https://localhost:8888/ui/
```

The root address `https://localhost:8888/` redirects to the UI. The unauthenticated health endpoint is:

```text
https://localhost:8888/health
```

Expected JSON includes `"status":"ok"` and the installed version.

### 4.4 Silent installation

Use silent installation only within an approved software deployment system and capture its log:

```powershell
Start-Process -FilePath ".\Morgana-Server-Setup.exe" `
  -ArgumentList "/VERYSILENT", "/NORESTART", "/LOG=<INSTALL_LOG_PATH>" `
  -Verb RunAs -Wait
```

Afterward, verify the service, health endpoint, certificate, firewall scope, and first sign-in manually. Do not place credentials in deployment command lines or logs.

## 5. First Launch, Sign-In, and TLS

### 5.1 First sign-in

1. Open `https://localhost:8888/ui/` on the server.
2. Enter the bootstrap local account values displayed by the installer.
3. After sign-in, open **Users**.
4. Use the break-glass warning link or edit the break-glass account.
5. Set a unique password of at least 12 characters and store it in an approved vault.
6. Sign out and sign in again to verify the new password.

Expected result: the Dashboard loads, the sidebar displays the signed-in identity, and the break-glass default-password warning no longer appears.

The browser stores the session JWT in local storage. Its default lifetime is 24 hours. Use **Log out** on shared operator systems; it clears the browser JWT and any browser-stored API key.

### 5.2 Certificate model

At first start, Morgana creates:

- A private Morgana root CA, valid for approximately ten years.
- A server certificate signed by that CA, valid for approximately two years.
- Subject Alternative Names for `localhost`, `127.0.0.1`, the server hostname, and non-loopback LAN IPv4 addresses detected at generation time.

The private CA key and server private key must never leave the server or be included in reports. Only the public CA certificate should be distributed to trusted operator and Merlino hosts.

### 5.3 Trust Morgana on another Windows computer

1. On the server, obtain the public file `%ProgramData%\Morgana\certs\morgana-ca.crt` through an approved administrative channel.
2. Copy only that `.crt` file to the operator computer.
3. Verify its fingerprint out of band according to your certificate policy.
4. Open PowerShell as Administrator on the operator computer.
5. Run:

```powershell
certutil -addstore -f Root "<PATH_TO_MORGANA_CA_CERTIFICATE>"
```

6. Close all browser or Excel windows that used the old trust state.
7. Reopen `https://<SERVER_HOST>:8888/ui/`.

Expected result: Windows trusts the connection when `<SERVER_HOST>` matches a certificate SAN.

> [!IMPORTANT]
> Trust the Morgana CA certificate, not `server.crt`. Never distribute `morgana-ca.key` or `server.key`.

### 5.4 Hostname or IP changes

The **Admin > Public DNS name** field changes generated Agent deployment URLs only. It does not add that DNS name to the existing TLS certificate.

If the server address changes and is not in the current certificate:

1. Schedule downtime and make a full backup.
2. Stop the `Morgana` service.
3. Preserve the root CA files.
4. Remove only the old server leaf certificate and server private-key files from the certificate directory.
5. Start the service so it issues a new leaf certificate from the existing Morgana CA.
6. Verify the new SAN list and reconnect.

There is no automatic certificate-renewal UI in 0.4.0. Monitor expiry through your normal certificate-management process.

## 6. Authentication, Users, and API Keys

Morgana has two operator authentication paths:

- **Browser session:** local account sign-in returns a JWT used by the UI.
- **API key:** the master key or a named key is sent in the `KEY` HTTP header.

### 6.1 Local accounts

The visible login page supports local email-and-password sign-in. The **Users** page can create records with these fields:

| Field | Purpose |
|---|---|
| Full name | Display identity |
| Email | Unique sign-in identifier |
| Alias | Short sidebar/display name |
| Password | Required for a usable local account; the user-management UI/API accepts eight characters, but use 12 or more |
| Role | `admin`, `contributor`, or `reader` metadata |
| Auth provider | Local, Google, GitHub, Microsoft, or OIDC metadata |
| Workspaces | Workspace identifiers, or unrestricted access when left blank |

To create a local user:

1. Open **Users**.
2. Select **+ New User**.
3. Enter name, email, alias, and a strong password.
4. Select **Local** and the intended role.
5. Leave Workspaces blank unless tested workspace identifiers are in use.
6. Select **Create**.
7. Verify the record appears, then test sign-in in a private browser window.

### 6.2 Current identity limitations

These limitations are important in 0.4.0:

- Roles and workspace memberships are stored, but most product routes accept any valid browser JWT or API key without enforcing those role distinctions. Do not treat `reader` as a complete technical read-only boundary.
- The visible Enabled checkbox sends `is_enabled` through the generic user-update route, which ignores that field. Separate enable/disable API routes work, but the current edit dialog does not call them.
- Many routes validate only a JWT signature and expiry, not the current user record. Disabling an account therefore does not reliably revoke its already-issued JWT before the default 24-hour expiry.
- The installed service does not generate a unique JWT signing secret by default. Unless an administrator supplies a strong private `MORGANA_SECRET_KEY` through the service environment, the source default is used.
- Legacy account registration and password-reset-token issuance routes are reachable without authentication. The reset-request route can return a reset token in its response. Do not expose the server to untrusted clients.
- OAuth and OIDC server support exists, but the current login page hides provider buttons. External SSO is not a supported end-user workflow in this release.
- The break-glass account cannot be deleted or disabled.

Use network controls and a small set of trusted users as the primary access boundary.

### 6.3 Named API keys

Use a named key for Merlino or automation instead of sharing the master key:

1. Open **Admin > API Keys**.
2. Select **+ New Key**.
3. Enter a purpose-specific name such as `merlino-lab` or `report-automation`.
4. Select **Create**.
5. Copy the full value immediately into an approved secret store.
6. Close the reveal dialog.

Expected result: the table retains only the key name, prefix, and creation time. The full value is not recoverable from Morgana after the one-time reveal. Morgana stores a SHA-256 hash of named keys.

Named keys currently have no scope or expiration controls. Create separate keys per integration and revoke them when no longer needed.

### 6.4 Revoke a named key

1. Identify the key by name and prefix under **Admin > API Keys**.
2. Select its revoke/delete action.
3. Confirm the integration immediately receives HTTP 401.
4. Remove the old value from the external secret store.

Revocation does not affect browser sessions or the master key.

### 6.5 Credential recovery

- Lost named key: sign in to the UI, revoke the old key, and create a replacement.
- Lost browser password but valid API key: an authorized administrator can use the user-management API from the protected server console. Current user routes treat a valid key as break-glass administration.
- Lost named keys and browser access: retrieve the installer-generated master key only from `%ProgramData%\Morgana\config\master-api-key.txt` at the server console, then recover the account and create a new named key. Restrict this file to administrators.
- Lost all keys and account access: stop and follow an approved backup or vendor-assisted recovery procedure. Do not delete the database without a full backup.

## 7. Dashboard and Navigation

The left sidebar contains:

| Page | Primary use |
|---|---|
| **Dashboard** | Last-hour Test summary, Agent state, update check |
| **Agents** | Enrollment, health, naming, beacon interval, Console, removal |
| **Scripts** | Script library, Excalibur, editing, execution, import/export |
| **Chains** | Ordered Script flows and execution logs |
| **Tests** | Execution records, output, AI status, Detection Fabric verdicts, reports |
| **Campaigns** | Multi-Chain and multi-Script exercise flows |
| **Tags** | Tag definitions and saved workspace selectors |
| **Adapters** | Detection Fabric configuration, ingestion, detections, and evidence |
| **Automation Center** | Scheduled Script, Chain, and Campaign execution |
| **Users** | Local account records and identity metadata |
| **Logs** | Searchable server JSON logs |
| **AI** | Provider, agent, model, and prompt configuration |
| **Admin** | Server information, DNS, keys, global Agent default, logging, backups |

### 7.1 Dashboard

The Dashboard shows:

- Online Agents.
- Running Tests.
- Tests passed and failed in the last-hour data window.
- Total visible Scripts.
- Up to 20 recent Tests.
- A quick Agent status grid.

Select **Refresh** to reload. Select **Check Update** to query the public version manifest. Morgana also checks for updates after UI startup and approximately hourly.

Dashboard counts are operational summaries, not Detection Fabric assurance results. A process exit code of zero is not proof that security monitoring detected or prevented the behavior.

## 8. Agents

### 8.1 Agent security model in 0.4.0

Agent enrollment is open to any host that can reach the registration endpoint. The current Agent also skips server-certificate verification, Agent API tokens are empty, Agent poll/result/heartbeat requests are not authenticated, and Jobs are dispatched without an HMAC signature. The Agent-side Console WebSocket is also accepted without Agent authentication. There is no approval queue.

> [!CAUTION]
> Deploy Agents only on an isolated, trusted exercise network. Restrict TCP 8888 by source IP and network segment. Do not rely on Agent approval, mutual TLS, certificate pinning, or signed Jobs in this release; those controls are unavailable.

### 8.2 Deploy a Windows Agent

1. Open **Agents** on the Morgana server UI.
2. Select **+ Deploy Agent**.
3. In the Windows block, select **Copy**.
4. On the authorized target, open Windows PowerShell 5.1 or later as Administrator.
5. Paste the one-line command and run it.
6. Wait for the success message and note the returned PAW identifier.
7. On Morgana, select **Refresh**.

Expected result:

- Windows service `MorganaAgent` exists and starts automatically.
- The Agent appears in **Agents** as `online` or `idle`.
- The row shows hostname, platform, OS, beacon interval, and Agent version.

Verify on the target:

```powershell
Get-Service -Name MorganaAgent
```

The 0.4.0 UI generates this command shape:

```powershell
curl.exe -k -o morgana-agent.exe https://<SERVER_HOST>:8888/download/morgana-agent.exe
.\morgana-agent.exe install --server https://<SERVER_HOST>:8888
```

The `-k` option disables download certificate validation. Prefer removing it after trusting the Morgana CA; otherwise verify the server address and binary through an approved channel before execution. A deploy token is not required or validated in 0.4.0.

Windows Agent locations:

| Item | Installed location |
|---|---|
| Binary and configuration | `%ProgramData%\Morgana\agent` |
| Agent-token file | `%ProgramData%\Morgana\agent\.agent_token` (empty under current open enrollment) |
| Work area | `%ProgramData%\Morgana\work` |
| Agent log | `%ProgramData%\Morgana\logs\agent.log` |
| Execution audit | `%ProgramData%\Morgana\logs\execution.log` |

The UI deployment command uses TLS verification bypass during download. Use it only on the trusted network after verifying the server address through another channel.

### 8.3 Deploy a Linux Agent

Linux deployment is available only when the server has a Linux Agent binary. If the download endpoint returns 404, obtain a release that includes it; building is a development task and is outside this installed-product procedure.

1. Open **Agents > + Deploy Agent**.
2. Copy the Linux command.
3. On the authorized target, open a root shell or use `sudo`.
4. Run the copied command.
5. Verify:

```bash
systemctl status morgana-agent
journalctl -u morgana-agent --no-pager -n 100
```

6. Return to Morgana and select **Refresh**.

Expected result: `morgana-agent.service` is enabled and active, and the Agent appears as Linux in the table.

The 0.4.0 UI generates this command shape:

```bash
curl -ksSL 'https://<SERVER_HOST>:8888/download/morgana-agent' -o morgana-agent
chmod +x morgana-agent
sudo ./morgana-agent install --server 'https://<SERVER_HOST>:8888'
```

The `-k` option disables download certificate validation. Trust the Morgana CA or independently verify the binary before installation.

Linux Agent locations:

| Item | Installed location |
|---|---|
| Binary | `/usr/local/bin/morgana-agent` |
| Configuration | `/etc/morgana/config.json` |
| Agent-token file | `/etc/morgana/.agent_token` (empty under current open enrollment) |
| Work area | `/var/lib/morgana/work` |
| Agent log | `/var/log/morgana/agent.log` |
| Execution audit | `/var/log/morgana/execution.log` |

### 8.4 Understand Agent states

| State | Meaning |
|---|---|
| `online` | Newly registered or reporting online |
| `idle` | Long-polling with no active Job |
| `busy` | A Job was dispatched |
| `offline` | No recent check-in within the stale threshold |
| `stale` | UI category for an old Agent record |

The Agent long-polls for up to 28 seconds and sends a separate heartbeat approximately every 60 seconds. The server checks stale Agents every 15 seconds and uses the greater of three beacon intervals or 30 seconds as the offline threshold.

The server transitions records among `online`, `idle`, `busy`, and `offline`; it does not currently assign `stale`. That value exists only as a UI filter.

### 8.5 Rename and configure an Agent

- Select **[name]** or **[edit]** in the Agent row, enter an alias, and confirm.
- Select the Beacon value, enter 5 to 3600 seconds, and confirm.

The server pushes a per-Agent beacon change on the next poll and the Agent persists it. Because long polling controls normal idle cadence, the beacon value mainly affects status thresholds and configuration rather than adding a sleep after every poll.

The **Admin > Global Agent Defaults** value applies to newly enrolled Agents. It does not overwrite existing per-Agent values.

### 8.6 Agent tags and approval

- Approval before first use: unavailable.
- Assigning typed Tags to Agents in the current web UI: unavailable.
- Agent list tag display is legacy metadata and is not a complete typed-tag assignment workflow.
- Saved workspaces therefore should not be treated as an Agent authorization boundary.

### 8.7 Interactive Console

Select **Console** in an Agent row to open an interactive shell. On an installed Windows server, Morgana launches a PowerShell-hosted terminal window in the active server desktop session and relays it to the Agent shell.

> [!DANGER]
> The target shell runs as the Agent service account: normally `LocalSystem` on Windows and `root` on Linux. Console commands are not wrapped as normal Tests and can cause immediate, unaudited changes. Use only under explicit operator authorization.

Console characteristics:

- Windows target shell: `cmd.exe`.
- Linux target shell: Bash or `sh`.
- Agent GUI applications run in a service session and may not be visible to a logged-in desktop user.
- The Agent must connect within about 30 seconds.
- A Console session has a maximum lifetime of about four hours.
- **Reset** closes a stale session before starting another.
- The operator-side WebSocket authenticates with a JWT or API key in its query string. The native Console relay uses the master key internally, and current diagnostic logging can record the full key-bearing URL. Treat all Console and server logs as credentials.

If no native window appears, confirm an interactive Windows session exists on the Morgana server and inspect server and Agent logs.

### 8.8 Update an Agent

There is no in-place Agent update action in 0.4.0. To replace an Agent binary:

1. Confirm no Test or Console session is active.
2. Use **Uninstall** in the Agent row to display target-specific removal commands.
3. Run those commands on the target with administrative privileges.
4. Deploy the Agent again from the updated server.
5. Delete the old server record only after the new Agent is visible.

The new enrollment receives a new PAW.

### 8.9 Remove an Agent

1. Select **Uninstall** in the Agent row.
2. Run the displayed Windows or Linux commands on the target.
3. Verify the target service is gone.
4. Select `x` in the Agent row to remove the server record.

Deleting only the server record does not uninstall endpoint software. It deletes dependent Jobs and unlinks the Agent from retained Tests.

**Purge stale** deletes records not seen for more than 24 hours. Confirm each is genuinely retired before purging.

## 9. Scripts

### 9.1 Browse and search

Open **Scripts**. Morgana loads up to 5,000 records and renders up to 500 matching rows at once. Use filters to narrow large libraries:

- TCode or name search.
- Tactic.
- Pack.
- Executor.
- Platform.
- Modified by user versus original.
- Red Team status.

The statistics strip summarizes total Scripts, TCodes, tactics, platforms, Excalibur/custom content, modifications, and executors.

If no Scripts exist, install an Excalibur Pack from the panel at the top of the page.

### 9.2 Inspect a Script

Select **Open**. The editor contains:

| Field | Required | Notes |
|---|---|---|
| Name | Yes | Human-readable unique purpose; package names follow pack conventions |
| TCode | Yes | MITRE ATT&CK technique such as `T1059.001`; saved uppercase |
| Tactic | No | ATT&CK tactic label |
| Executor | Yes | PowerShell, `cmd`, Bash, Python, `sh`, or manual |
| Platform | No | All, Windows, Linux, or macOS metadata |
| Source | Read-only | Pack or custom origin |
| Description | No | Purpose, prerequisites, expected telemetry, and safety notes |
| Command | Yes except API-created manual cards | Command sent to the Agent |
| Cleanup command | No | Runs automatically after the main command |
| Tags | No | Runtime values used by `#{tag_key}` placeholders |

The editor does not provide a static sandbox or syntax validator. Saving verifies basic required fields only. **Review with AI** is optional assistance, not proof of safety or correctness.

### 9.3 Create a custom Script

1. Select **+ New Script**.
2. Enter Name and TCode.
3. Select the executor and platform that match the target.
4. Describe prerequisites, expected effects, and expected telemetry.
5. Enter the command.
6. Enter a cleanup command that reverses created files, registry values, services, tasks, accounts, or other artifacts.
7. Select **Save Changes**.
8. Reopen the Script and verify every field before execution.

Use the `manual` executor only for a knowledge card that should return a manual-execution message rather than execute its command.

### 9.4 Edit, duplicate, and reset

- **Duplicate** creates a custom copy with ` - Copy` in its name.
- Editing a pack-owned Script marks it as user-modified.
- Pack updates preserve user-modified Scripts with the same name.
- **Reset to Pack** downloads the current original from the catalog, loads it into the editor, and waits for **Save Changes** before persisting.

Review a reset carefully: it can replace local command and cleanup changes.

### 9.5 Runtime parameters and Tags

Use `#{tag_key}` inside the saved command, for example:

```text
#{target_host}
```

To set values:

1. Save the Script first.
2. Select **+ Add Tag**.
3. The picker shows keys found in the command and keys declared by its pack.
4. Check each parameter to assign.
5. Enter a value or review an optional **Ask AI** suggestion.
6. Select **Save**.
7. Reopen the picker and confirm the values.

Resolution order at execution is:

1. Script assignment value.
2. Global Tag Definition value.
3. Pack default value.
4. Unresolved placeholder left literally in the command, with a warning in the server log.

Script assignment values are applied to direct Script runs and standard scheduled Script runs. In 0.4.0, Script nodes executed inside a Chain or Campaign do not pass the Script identity into tag substitution; they use the global Tag Definition value or pack default instead. Set and verify a non-sensitive global/default value before composite execution, or run the Script directly when a per-Script override is required.

Runtime Tag substitution is applied to the main command, not to `cleanup_command`. Do not put `#{tag_key}` placeholders in cleanup. Use a reviewed literal cleanup value or an execution path whose legacy `input_args` explicitly supplies that placeholder.

> [!WARNING]
> Runtime Tag values are stored in the Morgana database and are visible to authorized operators. Pack `sensitive` metadata does not provide a secret vault or guaranteed masking in 0.4.0. Do not store production passwords, tokens, or private keys in Tags.

The Script editor does not expose the older `input_args` structure. API callers can send input overrides, but Tags are the current UI workflow for runtime values.

### 9.6 Execute a Script

1. Open the Script.
2. Confirm all placeholders have safe lab values.
3. Confirm cleanup is appropriate and idempotent.
4. Select an online Agent.
5. Leave **Use Red Team** off for standard deterministic execution.
6. Select **Run Now**.

If the Script has unsaved changes, Morgana asks to save first. A successful queue response displays a Job identifier and begins output polling.

The inline editor polls for up to about 60 seconds. If it times out, the Job may still be running; inspect **Tests** instead of running it again blindly.

### 9.7 What the Agent executes

For standard execution, the Agent:

1. Receives the Job and marks the Test running.
2. Resolves remaining input arguments.
3. Adds a Morgana correlation marker to the process environment and command context.
4. Runs the selected executor with the Job timeout, normally 300 seconds.
5. Runs the cleanup command with the same executor and timeout, even when the main command fails.
6. Appends cleanup output to stdout/stderr under cleanup separators.
7. Returns main exit code, output, duration, and Agent-side UTC timing.

Cleanup failure is appended to stderr but does not replace the main process exit code. The reported main duration is not a complete measure of cleanup time.

Timeout cancellation targets the executor process. Descendant processes created by a Script can survive, so verify endpoint state and perform approved manual cleanup after a timeout.

Server and Agent output are truncated to approximately 100 KiB for stdout and 100 KiB for stderr. Store large evidence outside command output and reference it through approved procedures.

### 9.8 AI review and Red Team mode

In the Script editor:

- **Review with AI** analyzes the saved Script and can propose command and cleanup changes.
- **Review Output with AI** analyzes the displayed result and can propose a fix.
- Proposed content is not saved until the operator applies it and selects **Save Changes**.
- **Use Red Team** starts an iterative Orchestrator/Attacker/Analyst workflow that can generate and execute revised commands.

Red Team mode is optional and high risk. Review each generated command, keep iteration and timeout limits small, provide only non-sensitive context, and use **Pause** or **Stop** when required. Stopping the UI stream does not guarantee that an already dispatched endpoint process is terminated.

### 9.9 Bulk actions

The list supports selected or all-item execution and deletion. Bulk execution asks for an Agent and can save it to items that lack a default target.

> [!DANGER]
> **Delete Selected** and **Delete All** are destructive. Deleting a Script also deletes its linked Jobs, Tests, and Detection Fabric results. Flow references can become invalid. Export and back up before bulk deletion.

### 9.10 Import and export

- **Import Package** accepts JSON with a non-empty `scripts` array.
- Packages with a `package_id` replace only unmodified content owned by that package.
- User-modified Scripts survive package updates.
- A package without `package_id` uses broader legacy replacement behavior and should not be imported without a backup.
- Imported Chains are created when the package contains valid `chains` entries.
- **Export Package** exports Scripts whose names use the Morgana or Excalibur prefixes. It is not a complete backup of every custom or community Script.

Use database/full-data backup for authoritative recovery, not Script export alone.

## 10. Excalibur Packs

Excalibur is Morgana's native Script library and package format. Morgana does not clone or index a native Atomic Red Team repository.

The public catalog also contains community packs converted from Red Canary Atomic Red Team source material. These are displayed in a separate **Atomic Red Team (Red Canary)** category, but Morgana installs and runs them as Excalibur-format package records. Treat community content as unverified until reviewed in your lab.

### 10.1 Refresh the catalog

1. Open **Scripts**.
2. Expand **Excalibur Script Packs** if hidden.
3. Select **Refresh catalog**.

Expected result: the panel lists catalog version/date, package name, package version, tactic, platform metadata, Script and Chain counts, and installed state.

If it fails, allow the server and browser to reach `raw.githubusercontent.com` over HTTPS and inspect **Logs**.

### 10.2 Install one pack

1. Review package description, tactic, platform, prerequisites, status, and counts.
2. Select **Install**.
3. Read the replacement warning and confirm.
4. Wait for the progress bar to report imported Scripts and Chains.
5. Verify the pack is marked Installed.
6. Filter Scripts by the package and inspect its content before execution.

The single-pack UI currently displays a success progress state without checking the importer's `success` flag. Always inspect the returned error count through server logs and verify Script/Chain counts; a green progress bar is not sufficient evidence of a complete import.

### 10.3 Install selected or all packs

- Check package rows and select **Import Selected** for controlled installation.
- Select **Install All** to install every catalog item.
- When everything is installed, **Re-install / Update All** refreshes each package independently.

One package failure does not stop later packages. Review the final success/failure count and server logs.

### 10.4 Pack update and ownership behavior

For a package with a stable `package_id`, reinstallation:

- Deletes unmodified Scripts owned by that package.
- Preserves user-modified Scripts.
- Recreates the package's Chains.
- Does not delete custom Scripts or content from another package.
- Reports unresolved Chain references as import errors.

Replacement is destructive to history linked to the unmodified Script rows: their Jobs, Tests, and Detection Fabric relationships are deleted before replacement. Export evidence and create a database backup before updating a pack.

Script replacement and Chain creation are committed in separate phases. An import can therefore leave updated Scripts and only some Chains when errors occur; it is not an all-or-nothing transaction. In addition, the current Chain-reference resolver indexes only `Excalibur - ` Script names, so Chain definitions in `ART - ` community packs can report unresolved references even when their Scripts imported. Review every import report.

Deleting a pack is not a distinct UI operation. Delete its Scripts/Chains only after a backup and impact review.

### 10.5 Configure required pack Tags

Pack Scripts can declare `required_tags` and metadata such as label, description, default, example, required, and sensitive intent.

1. Open the installed Script.
2. Select **+ Add Tag**.
3. Review each declared parameter.
4. Check and fill required values.
5. Select **Save**. Missing Tag Definitions are created automatically as runtime parameters.
6. Verify no unresolved `#{...}` remains before execution.

AI suggestions are examples only. Never accept a suggested host, account, address, or path without checking the exercise scope.

### 10.6 Authoring a pack

New pack work should follow this structure:

```json
{
  "package_id": "excalibur-<domain>-<platform>-<tactic>-<slug>",
  "package_name": "Excalibur - <Name>",
  "version": "1.0.0",
  "description": "<purpose>",
  "author": "<author>",
  "mitre_domain": "enterprise-attack",
  "mitre_tactic": "<TAxxxx>",
  "mitre_tactic_name": "<tactic name>",
  "platform": "<platform>",
  "prerequisites": [],
  "tag_categories": [],
  "scripts": [],
  "chains": []
}
```

Authoring rules verified by the importer and current authoring contract:

- Use a stable, unique `package_id` for replacement scope.
- Script names must use an accepted package prefix, normally `Excalibur - `.
- The importer enforces name, TCode, an accepted prefix, and a non-empty command; it defaults omitted executor/platform values. The authoring contract still requires explicit executor and platform fields.
- Use `#{lowercase_tag_key}` for runtime values and list each key in `required_tags`.
- Include metadata for each required key in `tag_categories`.
- Mark credential-like values as sensitive intent, while recognizing that the current UI is not a secret vault.
- Always provide a cleanup command; use an explicit no-cleanup message when the Script is non-persistent, and do not rely on runtime Tag substitution inside cleanup.
- Chain `script_refs` must exactly match Script names in the same package.
- Keep commands valid JSON strings. Escape `"`, represent a literal backslash as `\\`, and never place raw newlines or comments inside JSON strings.
- Prefer single-quoted PowerShell strings inside JSON commands to reduce escaping errors.
- Add the package to [the public catalog](excalibur/catalog.json) with its public raw URL, category, version, counts, platform, prerequisites, and status.

Validate before publication:

```powershell
python -m json.tool "<PACK_FILE>" > $null
python -m json.tool "<CATALOG_FILE>" > $null
```

Then import into a disposable Morgana instance and verify Script counts, Chain references, required Tags, execution, output, and cleanup. Never test a new pack first on a production endpoint.

## 11. Tags and Workspaces

Tags have two roles:

- Runtime parameters substituted into Script commands.
- Descriptive/filterable metadata intended for selectors and workspaces.

### 11.1 Tag Definition fields

The **Tags > Tag Definitions** area displays:

- Label and key.
- Optional global value.
- Namespace.
- Type (`flag`, `string`, `number`, `boolean`, `enum`, or `list` in the UI).
- Color and description.
- Runtime parameter flag.
- Filterable flag.
- Assignment count.
- Sensitive and usage filters.

Deleting a definition also deletes all its assignments.

### 11.2 Current creation limitation

The standalone **+ New Tag** form is not reliably wired to its current fields in 0.4.0. Use the Script **+ Add Tag** picker to auto-create runtime definitions, or use the authenticated Tags API. Existing non-system definitions can be edited and deleted in the UI.

### 11.3 Workspaces

A Workspace backend record stores a selector expression such as:

```text
os=windows AND env=lab
```

Supported selector syntax includes `AND`, `OR`, `NOT`, parentheses, bare labels, and `key=value` tokens. The authenticated Tags API can create, edit, delete, activate, clear, and evaluate Workspace records, and allows only one globally active record.

The current web page contains Workspace controls, but their JavaScript handlers are absent. Creating, activating, clearing, or applying a Workspace is not a supported UI workflow in 0.4.0. The rest of the UI also does not apply the active record as a reliable global data filter. Use the API only for tested selector queries, not as an operational or security boundary.

> [!WARNING]
> Workspaces are filtering metadata, not a security boundary. Typed Agent assignment is not available in the current UI, and route authorization does not consistently enforce workspace membership.

## 12. Chains

A Chain is a saved flow of Script nodes. The current execution engine supports sequential Script nodes and IF/ELSE branching.

### 12.1 Create a Chain

1. Open **Chains**.
2. Select **+ New Chain**.
3. Enter a name and objective-focused description.
4. Select a Default Agent if the Chain should retain one.
5. Select a `+` insertion point.
6. Choose **Script Node** and filter by TCode, tactic, executor, or platform.
7. Select **Insert** for the Script.
8. Repeat in intended order.
9. Select **Save**.

Expected result: the Chain list shows the saved name and node count; **Execute** becomes available.

### 12.2 Add an IF/ELSE condition

1. Add **If / Then / Else** after a Script whose stdout determines the branch.
2. Enter the case-insensitive text that previous stdout must contain.
3. Add nodes under **IF TRUE** and **ELSE**.
4. Save the Chain.

An empty `contains` value always selects the ELSE branch. Matching uses only the latest preceding Script stdout, not stderr, exit code, Detection Fabric verdict, or AI status.

### 12.3 Ordering and removal

The visual flow order is execution order. Selecting **Remove** on a node removes that node **and every following node in the same branch**. Export or duplicate the Chain before major restructuring.

### 12.4 Execute and monitor

1. Save the Chain.
2. Select **Execute** from the list or editor.
3. Choose an Agent.
4. Confirm and start.
5. Watch the progress modal or open **Recent Executions > Log**.

Each Script node creates its own Test and Job. The Chain continues after a failed Script. Final states include:

| State | Meaning |
|---|---|
| `running` | Background flow active |
| `completed` | No recorded Script step failed |
| `partial_fail` | At least one Script failed, timed out, or errored; later nodes may still have run |
| `failed` | Chain orchestration itself raised an unrecoverable error |

Open the log for step stdout, stderr, exit code, branch choice, and a link to each Test.

### 12.5 Retry and cancellation

- Automatic Chain retry: unavailable.
- Stop-on-first-failure: unavailable in the current visual engine.
- Cancel a running Chain: unavailable.
- The editor offers Parallel nodes, but the current Chain execution walker has no Parallel-node implementation and silently skips them. Remove Parallel nodes before execution; Parallel Chain branches are unavailable.

Do not delete an Agent or referenced Script while a Chain is running.

### 12.6 Import, export, duplicate, and delete

- **Export JSON** requires a saved Chain.
- **Import JSON** creates a new Chain with ` (imported)` appended.
- **Duplicate** copies flow and default Agent.
- Deleting a Chain preserves execution history but removes the active definition.
- **Clear Log** deletes all Chain execution records.
- **Delete All** removes every Chain and leaves old execution records without a live Chain reference.

## 13. Tests and Jobs

### 13.1 Test lifecycle

| Test state | Meaning |
|---|---|
| `pending` | Test and Job created, not yet dispatched |
| `running` | Agent received the Job |
| `finished` | Agent returned main exit code 0 |
| `failed` | Agent returned a non-zero exit code or execution error |
| `timeout` | Reconciliation determined the Agent became unavailable beyond Job timeout plus grace period |

The server reconciles stale running Jobs about every 15 seconds. Default Job timeout is 300 seconds plus a 30-second reconciliation grace period.

Reconciliation examines Tests already marked `running`; a Job that remains `pending` because an Agent never polls can remain pending indefinitely.

### 13.2 Job lifecycle

Jobs are internal dispatch records:

| Job state | Meaning |
|---|---|
| `pending` | Waiting in the Agent queue |
| `dispatched` | Returned to the Agent poll |
| `completed` | Result accepted, regardless of process exit code |
| `failed` | Server reconciliation closed an abandoned Job |

A completed Job can correspond to a failed Test when the endpoint process exit code is non-zero.

### 13.3 Browse and filter Tests

Open **Tests**. Use:

- State cards.
- Search by TCode, name, or Script.
- Lifecycle state.
- AI execution status.
- Detection Fabric outcome.
- Script or Chain type.
- Agent.
- Exit code.
- Creation date range.
- Sortable table headings.

The metrics strip shows success rate, average duration, unique TCodes, Agents, and Scripts. Detection Intelligence summarizes validated outcomes.

### 13.4 Inspect a Test

Open a Test row to view:

- ID and TCode.
- Lifecycle and state reason.
- Exit code and Agent.
- Created, started, finished, and duration values.
- Complete retained stdout and stderr.
- AI review when available.
- Detection Fabric verdict, reason, confidence, candidates, validation metadata, and related evidence.
- Link back to the saved Script when it still exists.

### 13.5 Do not conflate the status layers

| Layer | Examples | Question answered |
|---|---|---|
| Test lifecycle | pending, running, finished, failed, timeout | Did transport/process execution complete? |
| Process exit | 0 or non-zero | What did the main process report? |
| AI execution review | FINISHED, BLOCKED, INTERCEPTED, ERROR, FAILED | How does AI classify execution output? |
| Detection Fabric outcome | Confirmed, Possible, Not Detected, No Telemetry, Inconclusive, Error | What detection evidence can be correlated? |

AI execution meanings:

- `FINISHED`: technique appears to have completed.
- `BLOCKED`: a preventive security control appears to have stopped execution.
- `INTERCEPTED`: a security signal appeared without full prevention.
- `ERROR`: Script/interpreter/dependency failure.
- `FAILED`: command ran but did not meet its objective.

AI classifications are advisory and must be reviewed against raw evidence.

### 13.6 Detection synchronization

- **Synchronize Selected Tests with Detection** refreshes enabled adapters, then processes selected completed Tests.
- **Sync All Tests** creates a persistent synchronization run for all completed Tests.
- Active runs can be resumed after UI interruption or server restart.
- Cancelling a synchronization run stops pending items; an AI request already running may finish.

The current bulk path performs deterministic correlation locally and does not call AI for every candidate. Ambiguous evidence remains Possible for analyst review.

### 13.7 Delete Tests

Deleting a Test also deletes its Jobs and Detection Fabric result/link records. **Delete All** removes the entire Test, Job, and Test-correlation history.

There is no Test cancellation endpoint and no direct Rerun button. To repeat an exercise, return to its Script, Chain, Campaign, or schedule and execute again.

## 14. Campaigns

A Campaign coordinates Chains and individual Scripts in one visual exercise.

### 14.1 Create a Campaign

1. Open **Campaigns**.
2. Select **+ New Campaign**.
3. Enter name and description.
4. Select a Default Agent.
5. At a `+` point, add a Chain, Script, IF/ELSE, or Parallel node.
6. Save.

The Campaign picker lets you search existing Chains. Script selection reuses the Script picker.

### 14.2 Campaign conditions

IF/ELSE uses case-insensitive `stdout contains` logic from the most recent preceding individual Script. A preceding Chain or Parallel group resets that stdout context, so do not use a Chain's nested output as a Campaign branch condition.

### 14.3 Parallel groups

Campaign Parallel nodes execute all branches concurrently and wait for each to finish. Each branch can contain Chains and Scripts; limited IF/ELSE handling is available within branches.

Parallel branches can contend for the same Agent and SQLite writes. Start with two small branches and inspect logs before scaling.

### 14.4 Execute and monitor

1. Save the Campaign.
2. Select **Execute**.
3. Choose the target Agent.
4. Confirm.
5. Review **Recent Executions > Log**.

Campaign states are `running`, `completed`, or `failed`. In 0.4.0, `completed` means the Campaign walker finished; nested Chain or Script failures may still be present. Always inspect the nested log and Tests page.

### 14.5 Lifecycle operations

- **Duplicate** copies the flow.
- **Import JSON** accepts an exported Campaign definition.
- **Export JSON** downloads the current editor flow.
- **Clear Log** deletes Campaign execution history.
- **Delete** removes the definition.
- Running Campaign cancellation and automatic retry are unavailable.

Reports operate on the Tests produced by Campaign execution. The UI does not provide a dedicated Campaign report button.

The current Campaign walker does not populate the `campaign_id` field on nested Tests. Campaign-scoped report filtering is therefore unreliable; use the Campaign execution log to identify Test IDs, then select those Tests explicitly for an Intelligent Report.

## 15. Detection Fabric

Detection Fabric ingests detection-system evidence into a canonical local model, correlates it with Tests, and records traceable Test-to-detection relationships.

### 15.1 Data model

| Record | Purpose |
|---|---|
| Detection | Normalized source alert, incident, event, finding, signal, or case; preserves source/evidence data |
| Adapter state | Health, coverage, cursor, last success/error, and item counts |
| Test result | One current verdict, confidence, correlation fingerprint/version, time window, and reason per Test |
| Test-detection link | Possible or confirmed relation, rank, score, components, and AI evidence |
| Sync run/item | Persistent bulk synchronization status and per-Test progress |

Detection records are stored in the local Morgana database. Configured SaaS adapters pull data outbound; Morgana does not require an inbound webhook.

### 15.2 Adapters page

Open **Adapters** to see:

- Fabric enabled state.
- Adapter configuration-entry count; this is not proof that credentials are present or a connection test succeeded.
- Total Detection count.
- Ingestion interval.
- Vendor adapter configured/enabled state, health, last sync, counts, and last error.
- Universal folder adapters and run history.
- Recent Detections and Test associations.

The only built-in vendor API adapter in 0.4.0 is **Microsoft Defender XDR**.

### 15.3 Configure Defender XDR

Prerequisites:

- Microsoft Entra application registration.
- Microsoft Graph **Application** permissions `SecurityIncident.Read.All` and `SecurityAlert.Read.All`.
- Administrator consent for those permissions.
- A current client secret stored through Morgana's encrypted adapter-secret field.
- Optional `ThreatHunting.Read.All` when Advanced Hunting per-firing granularity is enabled.

Procedure:

1. Open **Adapters**.
2. In Microsoft Defender XDR, select **Configure**.
3. Enter Tenant ID and Client ID.
4. Leave Graph Base URL at `https://graph.microsoft.com/v1.0` unless using a supported sovereign endpoint.
5. Set Poll interval, Lookback, and Retention according to SOC latency and policy.
6. Enable **Per-firing granularity** only when `ThreatHunting.Read.All` is granted.
7. Enter the client secret. Leaving the field blank preserves a saved secret; **Clear stored value** removes it.
8. Select **Save**.
9. Select **Test**.
10. When successful, select **Enable** and then synchronize the adapter.

Expected Test result: OAuth token acquisition succeeds and a one-item Graph alert query is reachable. A successful Test does not prove that alerts exist in the selected lookback.

Adapter secrets are Fernet-encrypted on disk and never returned in plaintext through the API. The encryption key is a critical backup asset.

### 15.4 Synchronize vendor adapters

- **Sync Selected** runs checked adapters that are both configured and enabled.
- **Sync All Adapters** runs every enabled vendor adapter and enabled Universal folder adapter.
- **Detections** on a vendor row filters the recent Detection table to that adapter.
- **Cleanup Expired** deletes Detection records whose retention expiry has passed.

Review fetched, inserted, updated, and error counts. Zero inserted can be valid when source records were already deduplicated.

### 15.5 Universal Morgana JSON adapter

The saved Universal adapter workflow in 0.4.0 supports local folder ingestion of Morgana normalized JSON only.

1. Open **Adapters > Universal Adapter (Morgana JSON)**.
2. Select **+ Add Universal Adapter**.
3. Enter a unique name and a folder path accessible to the `Morgana` service account.
4. Optionally add a description.
5. Enable only after the folder ACL and producer are verified.
6. Select **Save**.
7. Place one valid event object or an array of valid event objects in a `.json` file in that folder.

The folder is non-recursive and scanned about every ten seconds. Valid successfully imported files are deleted. Keep the producer's authoritative copy elsewhere.

Use **Test Parser / Normalizer** to preview a sample without storing it. Although parser components exist for formats such as CEF, LEEF, ECS, OCSF, OpenTelemetry, NDJSON, syslog, CSV, and raw JSON, the current saved folder-adapter UI forces `morgana_json`; those other live ingestion formats are not supported workflows in 0.4.0.

Run History shows received, accepted, rejected, duplicate, and error counts. Parse/Validation Errors shows line, type, message, and a fragment.

> [!DANGER]
> **Delete All Imported Data** removes every Universal-adapter Detection, clears its run/error history, deletes affected Test verdicts, and marks those Tests for revalidation.

### 15.6 Browse Detection evidence

Recent Detections supports filters for:

- Free text across title, entity, IP, command, and hash.
- Source, type, severity, and status.
- MITRE technique.
- Associated or unassociated Tests.
- Specific Test ID.
- UTC date/time range.

Open a Detection to inspect normalized fields, source timestamps, evidence, entities, and raw source data. Use **Related Tests** to reverse-navigate persisted Test links.

From a Test, use **Related detections** for possible and confirmed records, then **Correlation audit** to inspect score components, thresholds, time window, adapter coverage, cache status, and candidate truncation.

### 15.7 Correlation and scoring

Current default score signals include:

| Signal | Default points |
|---|---:|
| Exact Morgana marker | 100 |
| Technique | 60 |
| Exact command | 50 |
| Device identity | 35 |
| Distinctive command keyword | 35 |
| Unique technique bonus | 30 |
| Time within 15 minutes | 25 |
| Partial command | 25 |
| Hostname | 25 |
| Time within 60 minutes | 20 |
| User, IP, or process | 15 each |
| Title keyword | 10 |

Default thresholds are 70 for strong candidates and 40 for possible candidates. Use **Tests > Detection Settings** to tune the minimum proposal threshold and signal weights. Changes apply to later correlation and can change results; record changes in exercise evidence.

The strict primary correlation window starts at execution and ends no more than 15 minutes after completion. Distinctive command-content lookup can extend to 60 minutes. Agent-side timestamps are preferred; server timestamps are a lower-quality fallback.

### 15.8 Verdict meanings

| Outcome | Meaning |
|---|---|
| **Confirmed** | Exact marker or sufficiently strong, reliable timing plus behavior and target evidence |
| **Possible** | Candidate evidence exists but does not meet confirmation requirements |
| **Not Detected** | Successful Test, closed window, complete healthy adapter coverage, and no adequate match |
| **No Telemetry** | A negative conclusion is unsafe because execution, window closure, or adapter coverage is incomplete |
| **Inconclusive** | Candidate truncation, weak evidence, model uncertainty, or another unresolved condition |
| **Error** | Execution or validation/provider failure prevented an assurance conclusion |

Never report **Possible** as confirmed. Never report **No Telemetry** as a detection gap.

### 15.9 Automatic and manual validation

When the Fabric and AI validation switches are enabled, Test completion schedules validation after a default delay of about 60 seconds so adapters can ingest evidence. Manual validation remains available from Test detail.

Bulk selected/all synchronization refreshes adapters once and then correlates Tests. Confirmed current-version results can be reused when the correlation fingerprint is unchanged; stale correlation versions are hidden until recomputed.

### 15.10 Detection Fabric limitations

- Defender XDR is the only built-in vendor API adapter.
- Universal live folder ingestion is Morgana JSON only in the current UI.
- Embeddings are disabled by default and no semantic-search workflow is exposed.
- Adapter coverage must be complete before a defensible Not Detected result.
- Correlation and AI can be wrong; raw source evidence remains authoritative.
- Detection retention and Test history are independent. Expiring source Detections can reduce later drill-down evidence.

## 16. Reports and Portable Exports

### 16.1 Export Report ZIP

This is the evidence-rich, AI-independent export.

1. Open **Tests**.
2. Select **Export Report ZIP**.
3. Save the downloaded ZIP in an approved evidence repository.
4. Extract the entire ZIP to a normal folder.
5. Double-click `Open-Morgana-Report.cmd` inside the extracted package.
6. Keep its PowerShell window open while viewing the report.
7. Close the window to stop the loopback-only report server.

Do not open the report directly inside the ZIP or open `index.html` directly. The launcher creates a random URL token and dynamic `127.0.0.1` port so the viewer can load detail files on demand.

The ZIP includes up to 5,000 newest Tests, output, AI review data, summary metrics, MITRE counts, host names, deduplicated Detection records, and possible/confirmed relationships. It does not call Morgana or the Internet after export.

> [!WARNING]
> Portable reports contain offensive execution output and detection evidence. Anyone with file access can read them. Encrypt, retain, and share them under your evidence-handling policy.

### 16.2 Generate an Intelligent Report

This workflow requires a working Report AI Agent.

1. Complete or review AI execution status and Detection Fabric validation for the intended Tests.
2. Filter or select Tests as needed.
3. Select **Generate Intelligent Report**.
4. Choose scope:
   - Current filtered view.
   - Selected Tests.
   - All Tests.
   - Date range.
5. Select **Generate Intelligent Report** and wait for all model stages.
6. Review reported Test count, provider, and model.
7. Select **Open Intelligent Report** or **Download HTML**.
8. Record the Report ID for traceability.

The report persists in the Morgana database and contains:

- Executive assurance decision and confidence.
- Detection-assurance posture.
- Evidence-grounded, prioritized findings.
- Root-cause classification.
- Detection and Test references.
- SOC hunts and investigation steps.
- Remediation owners and validation steps.
- Retest criteria, strengths, residual risk, and limitations.

Generation fails rather than publishing a report when the AI provider cannot produce valid structured, evidence-grounded content. Retry with a model that has reliable JSON output or use the portable report for raw evidence.

### 16.3 Scope details

- **Filtered** sends the IDs currently present in the loaded filtered view.
- **Selected** requires at least one selected Test.
- **All** queries up to 5,000 newest Tests from the database.
- **Date range** uses inclusive UTC day boundaries.

The Intelligent Report is analysis, not the complete evidence archive. Pair it with the portable ZIP.

## 17. AI Mission Engine

AI is optional. It powers Script review/improvement, output analysis, Tag suggestions, Test review, Detection Agent decisions when needed, Red Team iteration, and Intelligent Reports.

### 17.1 Configure the active provider

1. Open **AI**.
2. Review **Engine Status** and **Active Provider**.
3. Select **Change Provider**.
4. Select a provider.
5. Enter the provider-specific endpoint, credential, model, deployment, or API version.
6. Select **Test Connection**.
7. Confirm a successful provider/model response.
8. Select **Save & Apply**.
9. Refresh and verify **READY**.

Leaving an API-key field blank preserves its saved value. The UI masks stored provider keys after save.

### 17.2 Supported providers

| Provider | Configuration | Authentication | Notes |
|---|---|---|---|
| GitHub Models | Model; fixed service endpoint | GitHub CLI/device-flow token | Free tier is rate-limited; current mapping supports a limited model set |
| GitHub Copilot | Model | GitHub CLI/device-flow token and eligible subscription | Uses Copilot chat-completions service |
| Azure OpenAI | Resource base URL, API key, Deployment Name, API Version | `api-key` header | Deployment Name is authoritative, not the marketing model name |
| Microsoft Foundry | Endpoint ending at an OpenAI-compatible v1 base, API key, Deployment Name | `api-key` header | No `api-version` query parameter is added |
| OpenAI | Chat-completions endpoint, API key, model | Bearer key | Supported by server/API and per-agent routing; omitted from the main provider selector in 0.4.0 |
| Anthropic | Messages endpoint, API key, Claude model | `x-api-key` | Uses Anthropic Messages API |
| Ollama | OpenAI-compatible endpoint, model | None by default | Local inference; reasoning models receive no-think handling where supported |
| LM Studio | OpenAI-compatible endpoint, loaded model ID | None by default | Local inference; model must be loaded and local server running |
| Custom | OpenAI-compatible chat endpoint, optional/required key, model | Bearer key when supplied | Validate compatibility with Morgana's request and response shape |

The global provider selector omits direct OpenAI even though the backend supports it. Per-role selectors are also inconsistent: Microsoft Foundry is visible for the Intelligent Report Agent but not for the other four roles. Configure omitted combinations through the authenticated AI API only after testing them; a backend provider entry does not make every UI selector offer it.

### 17.3 GitHub Models or GitHub Copilot

1. Install GitHub CLI on the Morgana server if it is not present.
2. In **AI > Change Provider**, choose the GitHub provider.
3. Select **Sign in to GitHub**.
4. Open the displayed device URL on a trusted browser.
5. Enter the one-time code and authorize the intended account.
6. Return to Morgana and wait for success.
7. Test and save the provider.

The login flow can persist the resulting token in the AI provider configuration. Treat the Morgana data directory and backup as credential-bearing.

### 17.4 Azure OpenAI

1. Choose **Azure OpenAI**.
2. Enter the resource base URL, for example `https://<RESOURCE>.openai.azure.com`.
3. Enter `<AZURE_OPENAI_API_KEY>`.
4. Enter the deployed model's **Deployment Name**.
5. Enter the required API Version; the current default is `2024-08-01-preview`.
6. Test and save.

If a full chat-completions URL is supplied, Morgana uses it and adds `api-version` when absent.

### 17.5 Microsoft Foundry

1. Choose **Microsoft Foundry (AI Services)**.
2. Enter the Foundry OpenAI-compatible v1 endpoint, normally ending in `/openai/v1`.
3. Enter `<FOUNDRY_API_KEY>`.
4. Enter the deployment/model name in **Deployment Name**.
5. Do not enter an Azure OpenAI API Version; Foundry uses the v1 route without that query parameter.
6. Test and save.

Morgana appends `/chat/completions` unless it is already present.

### 17.6 OpenAI direct

Direct OpenAI is implemented but is not listed in the main active-provider selector in 0.4.0. Configure it through the authenticated AI provider API, or use **Custom** with the OpenAI chat-completions URL.

Required fields are:

```json
{
  "provider": "openai",
  "endpoint_url": "https://api.openai.com/v1/chat/completions",
  "api_key": "<OPENAI_API_KEY>",
  "model": "<MODEL_ID>"
}
```

Submit this only over trusted HTTPS and never place the real key in source control or shared shell history.

### 17.7 Anthropic

1. Choose **Anthropic Claude**.
2. Keep the default Messages endpoint unless your service requires another.
3. Enter `<ANTHROPIC_API_KEY>` and an available model ID.
4. Test and save.

Morgana requests structured text but model availability remains account-dependent.

### 17.8 Ollama

1. Install and run Ollama on the Morgana server or an approved private inference host.
2. Pull an appropriate model using the Ollama administration procedure.
3. Choose **Ollama (local)**.
4. Use `http://localhost:11434/v1/chat/completions` when Ollama runs on the server host; otherwise use the approved private endpoint.
5. Enter the exact installed model ID.
6. Test and save.

Because Morgana runs as a Windows service, `localhost` means the Morgana server, not the operator browser. Ensure the Ollama process remains running independently of an interactive user session.

### 17.9 LM Studio

1. Load a model in LM Studio on the Morgana server.
2. Start its Local Server.
3. Read the exact model ID from LM Studio or its `/v1/models` response.
4. Choose **LM Studio**.
5. Use `http://localhost:1234/v1/chat/completions` unless configured differently.
6. Enter the exact loaded model ID, test, and save.

LM Studio must remain available while Morgana's Windows service calls it.

### 17.10 Custom OpenAI-compatible endpoint

Enter the full chat-completions URL, model ID, and bearer key when required. The endpoint must accept `model`, `messages`, `max_tokens`, and `temperature`, and return assistant content under the OpenAI-compatible `choices[0].message.content` shape.

### 17.11 AI Agents

Morgana routes five roles independently:

| Agent | Purpose |
|---|---|
| Script Agent | Script explanation, requirements, risk, improvement, output fixes, Tag suggestions |
| Test Result Agent | Execution classification |
| Detection Agent | Candidate-evidence judgment |
| Intelligent Report Agent | Evidence clusters, findings, synthesis, actions, and retest criteria |
| Red Team Agent | Iterative strategy, command generation, execution analysis, and cleanup generation |

Leave Provider blank to inherit the active provider, or select an already configured provider and optional model override. **Apply to All** fills the forms; select **Save Agents Config** to persist.

### 17.12 Prompt customization

**Agent Prompts > View / Edit Prompts** exposes 21 prompt templates. A custom prompt is active on the next call. **Reset to Default** deletes the customization.

> [!WARNING]
> Prompt changes can weaken structured-output, safety, evidence-grounding, and status rules. Export a full backup and validate each affected workflow before operational use.

### 17.13 Engine controls and caching

The installed UI does not expose the runtime engine switch, timeout, global fallback model, or generation token limit as fields. They are available through `GET/POST /api/v2/ai/config`:

- AI enabled: default `true`.
- Review timeout: default 180 seconds, minimum 30.
- Generation token limit: default 1000, allowed 256 to 4096.

These values are in-memory and can return to process defaults after a server restart. Provider and per-Agent configurations persist on disk.

Completed Test reviews are cached unless explicitly forced. Detection Fabric reuses only eligible confirmed results whose current correlation version and fingerprint still match.

### 17.14 AI privacy and limitations

- Cloud providers receive selected Script content, Test output, Tag context, Detection summaries, or report evidence required for the requested function.
- Detection evidence is normalized/redacted before AI validation, but redaction cannot guarantee removal of every sensitive value.
- Ollama and LM Studio can avoid external model egress when fully local, but Morgana still stores inputs/results locally.
- AI provider API keys are XOR-obfuscated, not strongly encrypted, in the current provider store. Protect the host and data-directory ACLs.
- AI can generate unsafe, incorrect, or out-of-scope commands. Human review is mandatory.
- Rate limits, timeouts, unavailable models, and invalid JSON can produce `ERROR` or report-generation failure.

## 18. Automation Center

Automation Center schedules Scripts, Chains, and Campaigns.

### 18.1 Create a schedule

1. Open **Automation Center**.
2. Select **+ New Schedule**.
3. Enter name and optional description.
4. Select target type and target.
5. Select an Agent PAW.
6. Choose a trigger:
   - Once.
   - Daily.
   - Weekly.
   - Monthly.
   - Interval, minimum 60 seconds in the UI.
   - Custom five-field cron.
7. Choose Standard or Red Team mode.
8. Review advanced concurrency and timeout fields.
9. Select **Save**.

Expected result: the table shows Enabled, next run, target, mode, and run count. The scheduler checks due work approximately every 30 seconds.

### 18.2 Time handling

Friendly daily, weekly, and monthly fields are entered in browser local time and converted to UTC cron values. Custom cron is explicitly UTC:

```text
minute hour day-of-month month day-of-week
```

The parser supports `*`, lists, ranges, and step values. Day of week uses 0 for Sunday through 6 for Saturday.

Recheck schedules after daylight-saving changes because saved UTC cron does not dynamically retain a local timezone rule.

### 18.3 Run and inspect

- **Run** triggers immediately regardless of enabled or next-run state.
- **History** shows schedule executions.
- **Detail** shows downstream Test/Chain/Campaign execution ID, status, mode, logs, errors, and Red Team fields.
- **Off/On** disables or enables future trigger evaluation.
- **Del** removes the schedule, not its execution evidence.

### 18.4 Current scheduling limitations

- Retry fields are stored but retry execution is not implemented.
- Notification fields exist in the API/model but no notification delivery is implemented.
- `skip_new_run` is enforced.
- `fail_new_run` skips a due run but does not create a failed execution record.
- `run_in_parallel` starts another run.
- `queue_new_run` currently also starts another thread rather than a true serialized queue.
- `stop_previous_and_start_new` does not terminate the previous thread; it starts another run.
- Standard scheduled Chain/Campaign success records dispatch success, not completion of every nested Test. Inspect downstream execution logs.
- Red Team scheduling is supported for a single Script. Composite Chain/Campaign Red Team mode is experimental and may not resolve current visual flow nodes correctly.
- There is no UI action to cancel an active schedule execution.

## 19. Settings Reference

Morgana has no single Settings page. Configuration is distributed across **Admin**, **AI**, **Adapters**, **Tests > Detection Settings**, **Tags**, **Users**, and **Automation Center**.

### 19.1 Admin settings

| Section/field | Default or range | Persistence and effect |
|---|---|---|
| Server IP, machine, platform, port, memory, disk | Read-only | Current host information |
| Public DNS name | Empty | Persists; changes generated Agent deployment URL only |
| Named API keys | None | Hash persists in database; full value shown once |
| Default beacon interval | 5 seconds; 5-3600 | Applies immediately to new enrollments; saved for display, but startup does not currently reload the saved value into Agent registration, so reapply it after restart |
| Log retention | 24 hours; 1-168 | Persists; cleanup runs at startup and hourly |
| Runtime log level | INFO initially; DEBUG/INFO/WARNING/ERROR | Immediate, resets on restart |
| Auto-backup | Off | Persists |
| Auto-backup interval | 24 hours; 1-168 | Checked by an hourly loop |
| Maximum backup files | 10; 1-100 | Oldest managed database backups are deleted |

### 19.2 Detection Fabric settings

| Field | Current default | Effect |
|---|---:|---|
| Fabric enabled | On | Starts ingestion/retention scheduler at server startup |
| Default retention | 7 days | Fallback Detection TTL |
| Ingestion interval | 5 minutes | Background adapter pass |
| Default lookback | 1440 minutes | First/full source query window |
| AI validation | On | Allows Detection Agent on ambiguous candidates |
| Maximum AI candidates | 10 | Candidate prompt cap |
| Maximum telemetry candidates | 500 | Local retrieval cap |
| Strong/possible thresholds | 70/40 | Correlation classification |
| Embeddings | Off | Reserved; no supported UI workflow |

The Adapters top-level Settings dialog writes polling, retention-hours, and AI-toggle fields. Per-adapter `retentionDays`, `lookbackMinutes`, and `pollIntervalMinutes` are the verified controls used by vendor ingestion; prefer those for operational configuration.

The top-level Retention (hours) field is saved as `retentionHours`, which the current retention service does not consume. The scheduler captures `ingestionIntervalMinutes` when its task starts, and enabling Detection Fabric after a startup in which it was disabled does not create that task. Restart the service during a controlled window after changing the global enabled state or ingestion interval. Per-adapter retention remains measured in days.

### 19.3 User and Tag settings

Users store identity provider, role, enabled state, workspaces, and Tags. Tag Definitions store label, key/value, namespace, type, color, scope/capabilities, defaults, and runtime/filter behavior. Review the limitations in [Authentication](#6-authentication-users-and-api-keys) and [Tags](#11-tags-and-workspaces) before treating either as access control.

### 19.4 Security implications

- DNS changes do not reissue TLS certificates.
- Short beacon intervals increase status sensitivity and request turnover.
- DEBUG logs can contain more command/evidence context.
- Long Detection retention increases database size and sensitive-data exposure.
- Provider/model changes alter AI output and report reproducibility.
- Detection score changes can alter assurance outcomes.
- Backup files contain users, named-key hashes, Tests, output, and detection evidence.

## 20. Merlino Integration

Morgana implements the API contract expected by Merlino. Historical compatibility names may appear in Merlino settings, but Morgana documentation and operations use Morgana terms.

### 20.1 Prerequisites

- Morgana health endpoint is reachable from the Excel host.
- Morgana root CA is trusted on the Excel host.
- A purpose-specific named Morgana API key exists.
- At least one Agent is enrolled for execution.
- Required Excalibur Scripts are installed.

### 20.2 Connect Merlino

1. In Morgana **Admin > API Keys**, create a named key for Merlino and store it securely.
2. On the Merlino host, install the public Morgana CA certificate in Trusted Root.
3. In Merlino, open Settings and locate the existing Caldera/Morgana connection area.
4. Enter `https://<SERVER_HOST>:8888` as the server URL.
5. Enter the named Morgana key.
6. Save and run the connection/status check.

Expected result: Morgana returns status `ok` and its version from `/api/v2/merlino/check_status`.

### 20.3 Synchronize and execute

Depending on the Merlino workflow:

- `/api/v2/merlino/synchronize` creates or updates Tests, resolves the assigned Agent by hostname, and queues the first Script matching the first TCode when the row state is running.
- `/api/v2/merlino/synchronize_morgana` creates a Chain for a Merlino Test row when missing, using all installed Scripts for its TCode, then returns Chain/Test execution evidence.
- `/api/v2/merlino/realtime` returns recent Test and Agent metrics.
- `/api/v2/agents` provides the compatibility Agent list.

Morgana returns AI review and Detection Fabric fields when available. A missing TCode Script produces a Chain with no executable nodes or a synchronization record without a queued Job; install or create the Script first.

The direct `/synchronize` path sends the saved Script command without runtime Tag substitution and does not deduplicate an existing active Job when the same row is synchronized again in `running` state. Use concrete reviewed commands on this path and avoid repeated synchronization until the current Job finishes.

### 20.4 Troubleshoot Merlino

- TLS error: trust the Morgana CA and use a hostname/IP in the certificate SAN.
- HTTP 401: replace the named key in Merlino and verify it has not been revoked.
- No Agent: match the Merlino assigned hostname to the Morgana Agent hostname.
- No Job: verify state is running and at least one Script exactly matches the first TCode.
- Stale result: synchronize again after the Test and optional Detection Fabric validation finish.

## 21. REST API for Operators

### 21.1 Discovery

| Resource | URL |
|---|---|
| Health | `GET /health` |
| OpenAPI UI | `/docs` |
| OpenAPI document | `/openapi.json` |

OpenAPI reflects registered routes, but a route's presence does not guarantee that every UI workflow is production-ready. Apply the limitations in this manual.

### 21.2 Authentication

Use one of:

```http
KEY: <MORGANA_API_KEY>
```

or a browser-issued token:

```http
Authorization: Bearer <MORGANA_JWT>
```

Use named API keys for integrations. Do not put keys in URLs. Console WebSockets are an exception in the current implementation and pass a key in the query string; protect proxy and access logs accordingly.

### 21.3 PowerShell examples

Set placeholders only in the current trusted shell session:

```powershell
$base = "https://<SERVER_HOST>:8888"
$headers = @{ KEY = "<MORGANA_API_KEY>" }

Invoke-RestMethod -Uri "$base/health"
Invoke-RestMethod -Uri "$base/api/v2/agents" -Headers $headers
Invoke-RestMethod -Uri "$base/api/v2/scripts?search=T1059&limit=50" -Headers $headers
```

Queue a saved Script on an Agent:

```powershell
$body = @{ paw = "<AGENT_PAW>" } | ConvertTo-Json
Invoke-RestMethod `
  -Method Post `
  -Uri "$base/api/v2/scripts/<SCRIPT_ID>/execute" `
  -Headers $headers `
  -ContentType "application/json" `
  -Body $body
```

Expected response includes `test_id`, `job_id`, `paw`, and `queued: true`. Poll the Job or inspect the Test:

```powershell
Invoke-RestMethod -Uri "$base/api/v2/jobs/<JOB_ID>" -Headers $headers
Invoke-RestMethod -Uri "$base/api/v2/tests/<TEST_ID>" -Headers $headers
```

Do not bypass TLS verification in routine automation. Install the Morgana CA in the calling host's trust store.

### 21.4 Major API groups

| Prefix | Purpose |
|---|---|
| `/api/v2/auth` | Browser account sign-in and token operations |
| `/api/v2/api-keys` | Named key lifecycle |
| `/api/v2/agents` | Agent list/configuration/removal |
| `/api/v2/agent` | Agent registration, poll, result, heartbeat |
| `/api/v2/scripts` | Script/package CRUD and execution |
| `/api/v2/chains` | Chain CRUD, execution, and logs |
| `/api/v2/tests` | Test detail, deletion, and exports |
| `/api/v2/campaigns` | Campaign CRUD, execution, and logs |
| `/api/v2/tags` | Definitions, assignments, workspaces, and selectors |
| `/api/v2/detection-fabric` | Configuration, ingestion, correlation, and evidence |
| `/api/v2/reports` | Intelligent Reports |
| `/api/v2/ai` | Providers, agents, reviews, prompts, and Red Team functions |
| `/api/v2/scheduler` | Schedules and execution history |
| `/api/v2/admin` | Server settings, logs, information, and backup |
| `/api/v2/merlino` | Backward-compatible Merlino integration |

### 21.5 API cautions

- Named keys have full practical API access, no scope, and no expiry.
- Agent registration, poll, result, heartbeat, install-script, binary-download, health, update-check, and update-status routes are unauthenticated.
- Script list/detail/create and every current Chain CRUD, execution, and log route lack the normal route-level authentication dependency.
- Legacy account registration, activation, reset request, and reset completion routes are unauthenticated; reset request can disclose the token in its response.
- The Agent-side Console WebSocket accepts a PAW without validating the Agent token. The operator-side Console key travels in a query string.
- API deletion operations are immediate and can cascade into Test/evidence loss.
- Do not expose `/docs`, `/openapi.json`, Agent registration, downloads, or any API route to untrusted networks.

## 22. Logs and Diagnostics

### 22.1 Server Logs page

Open **Logs**. The default view loads the last 30 minutes. Filters support:

- Text search across message and exception.
- INFO, WARNING, or ERROR.
- From and To timestamps.
- Quoted phrases; multiple terms are combined with AND.

Select **Export JSON** only after loading a result set. Review and sanitize exported logs before sharing. Select **Clear All** only after preserving required evidence.

### 22.2 Installed log locations

| Log | Purpose |
|---|---|
| `%ProgramData%\Morgana\logs\server.log` | JSONL application log, rotating 10 MiB with five backups |
| `%ProgramData%\Morgana\logs\service.log` | Windows service stdout |
| `%ProgramData%\Morgana\logs\service_error.log` | Windows service stderr |
| `%ProgramData%\Morgana\logs\agent.log` | Windows Agent operational log when Agent is co-located |
| `%ProgramData%\Morgana\logs\execution.log` | Append-only Agent execution metadata |
| Windows Application log | Service lifecycle and NSSM events |

On a Linux Agent, use `/var/log/morgana/agent.log`, `/var/log/morgana/execution.log`, and `journalctl -u morgana-agent`.

Server application logs are JSON objects with UTC timestamp, level, logger name, message, and optional exception. On version change, the prior main server log can be archived with the old version in its filename.

> [!WARNING]
> Startup logs write the full master API key on every server start. Native Console diagnostics can also write a key-bearing internal WebSocket URL. Provider, Script, Test, and Console logs can contain additional sensitive context. Restrict log ACLs, exports, backups, and support attachments; never send raw logs to an untrusted recipient.

### 22.3 Diagnostic sequence

1. Check `Get-Service Morgana`.
2. Query `/health` locally.
3. Check **Logs** for the feature namespace and exact timestamp.
4. Review service stdout/stderr.
5. For endpoint work, review Agent log and execution audit.
6. Verify DNS, TCP 8888, Windows Firewall, TLS trust, and clock synchronization.
7. Reproduce once with a harmless General Utilities Script.
8. Use DEBUG temporarily only if required, then return to INFO.

## 23. Backup, Restore, and Disaster Recovery

### 23.1 Database backup from the UI

1. Open **Admin > Database Backup**.
2. Select **Backup Now**.
3. Confirm filename, size, and time appear.
4. Copy the backup to an access-controlled external location through an approved administrative process.

Morgana uses SQLite `VACUUM INTO` and stores managed files under `%ProgramData%\Morgana\backups`.

To enable automatic database backups:

1. Set Auto-backup to **ON**.
2. Choose 1-168 hours.
3. Choose 1-100 retained files.
4. Select **Save**.

The background loop checks approximately hourly. This is database backup only.

### 23.2 What database backup includes

It includes records stored in SQLite, such as:

- Agents, Scripts, Chains, Campaigns, Tests, and Jobs.
- Named API-key hashes and users.
- Tags, workspaces, schedules, and histories.
- Detections, evidence links, results, and Intelligent Reports.

It does **not** include all files needed for full recovery, including TLS keys, the master key, AI provider configuration, Detection Fabric encryption key/configuration, custom prompts, server settings files, logs, or Agent binaries.

### 23.3 Full configuration backup

For disaster recovery, back up the complete `%ProgramData%\Morgana` directory:

1. Notify operators and stop new work.
2. Confirm no Test, Campaign, report, backup, or sync run is active.
3. Stop the `Morgana` service.
4. Copy the complete data directory to encrypted, access-controlled storage.
5. Preserve ACL and timestamp metadata where possible.
6. Start the service and query `/health`.
7. Test restoration periodically on an isolated host.

The Detection Fabric secret-encryption key must be restored with its encrypted secret store. Losing that key makes saved adapter secrets unrecoverable.

### 23.4 Restore a managed database backup

1. Create a new backup of the current database.
2. Open **Admin > Database Backup**.
3. Select **Restore** next to the intended file.
4. Confirm.
5. Restart the Morgana service immediately:

```powershell
Restart-Service -Name Morgana
```

6. Verify health, version, users, keys, Scripts, Agents, Tests, Detection Fabric, schedules, and reports.

Restore replaces the live database. Data created after that backup is lost. It does not roll back files outside the database.

### 23.5 Full disaster recovery

1. Provision an isolated Windows host with the same or compatible Morgana version.
2. Install Morgana but do not admit untrusted network clients.
3. Stop the service.
4. Preserve the fresh data directory separately.
5. Restore the complete protected data directory and ACLs.
6. Start the service.
7. Verify TLS identity, server address, API keys, AI providers, adapter secrets, and database migrations.
8. Reissue named keys and provider secrets when compromise is suspected.
9. Re-enroll Agents if server identity or network addressing changed.

## 24. Upgrade the Server

### 24.1 Recommended installer upgrade

1. Review **Dashboard > Check Update** and release notes.
2. Confirm no Tests, Chains, Campaigns, Consoles, reports, backups, or sync runs are active.
3. Create both a managed database backup and a full data-directory backup.
4. Download the approved new installer from the authorized release source.
5. Verify source, publisher, and release integrity.
6. Run the installer as Administrator.
7. The post-install process replaces/recreates the service while preserving `%ProgramData%\Morgana`.
8. Open `/health` and confirm the new version.
9. Sign in and validate Agents, Scripts, Chains, Tests, Detection Fabric, AI, reports, schedules, and Merlino.

Database migrations run at startup. Do not downgrade by replacing only the executable unless the release procedure explicitly supports it.

### 24.2 Advanced in-place update API

The authenticated `/api/v2/update/apply` route can download a raw server executable, verify SHA-256 when supplied by the public manifest, stop the service, swap the executable, run a health check, and roll back on failure. The current UI shows a download link rather than exposing this action.

Use the API-only path only under a documented change procedure with console access to the server. The installer upgrade remains the supported operator workflow.

Supplying an override `download_url` bypasses the manifest SHA-256 value, and the network helper has a last-resort mode that disables remote certificate verification. Never use an override URL in routine operations; verify the publisher and hash independently if an emergency procedure requires it.

## 25. Uninstall

### 25.1 Uninstall the server and preserve data

Use the provided [complete uninstall script](uninstall/03-uninstall-morgana.ps1), because it stops/removes the service before removing program files:

1. Create and verify backups.
2. Copy the uninstall script to the server through an approved channel.
3. Open PowerShell as Administrator in that folder.
4. Run:

```powershell
.\03-uninstall-morgana.ps1
```

Expected result: service and program files are removed, while `%ProgramData%\Morgana` is preserved for reinstall/recovery.

### 25.2 Clean server removal

> [!DANGER]
> This permanently deletes the database, API material, certificates, AI configuration, detections, reports, logs, and backups stored under the Morgana data root.

After independently verifying the backup:

```powershell
.\03-uninstall-morgana.ps1 -WipeData
```

Also remove the Morgana firewall rule, Defender exclusion, and trusted root CA if the script or local policy leaves them behind. Verify no Agent still points to the retired server.

### 25.3 Uninstall Agents

Use **Agents > Uninstall** for exact platform commands. Then delete the Agent row.

On a machine that also hosts the Morgana Server, do not use an Agent `--purge` operation that removes the shared `%ProgramData%\Morgana` root.

## 26. Security and Responsible Operation

### 26.1 Mandatory controls

- Obtain explicit written authorization and a defined scope.
- Isolate Morgana and Agents from public/untrusted networks.
- Restrict TCP 8888 by firewall source.
- Use dedicated lab targets and service identities.
- Change bootstrap credentials immediately.
- Use one named API key per integration; rotate and revoke promptly.
- Protect `%ProgramData%\Morgana`, backups, logs, reports, and certificates with administrator-only ACLs.
- Synchronize clocks on server, Agents, and detection systems.
- Review every Script, runtime value, target, cleanup command, and AI proposal.
- Start with harmless General Utilities before adversary behavior.
- Monitor exercise execution from both endpoint and SOC sides.
- Preserve evidence and perform post-exercise cleanup.

### 26.2 Current technical limitations that affect deployment approval

Morgana 0.4.0 does not currently provide:

- Authenticated or approved Agent enrollment.
- Effective Agent token authentication.
- Signed Job enforcement.
- Agent certificate validation or pinning.
- Consistent route-level authentication on every API.
- Fine-grained API-key scopes or expiry.
- Consistent role/workspace authorization across product routes.
- A per-installation JWT signing secret unless one is supplied administratively.
- Immediate revocation of already-issued JWTs across routes that validate only signature and expiry.
- Server-side termination of an already running endpoint process.
- A complete Agent update mechanism.

The installer also creates a broad inbound firewall rule, does not explicitly harden every file ACL below the data root, and logs the master API key. Scope the firewall and enforce administrator-only ACLs before remote use.

These limitations make Internet-facing or untrusted-network deployment unsupported.

### 26.3 Antivirus exclusions

The installer attempts to exclude the Morgana data directory because offensive content can trigger endpoint controls. An exclusion is not a functional requirement for every Script and should never be applied automatically to production systems without risk approval.

Prefer:

- A dedicated server.
- Narrow ACLs and network segmentation.
- Time-bounded, documented endpoint exclusions only when the exercise requires them.
- Removal and verification after the exercise.

### 26.4 AI-generated content

AI is not an authorization mechanism. It can invent tools, select the wrong target, generate destructive behavior, or misclassify prevention/detection. Keep a human approval gate before every generated command and every report decision.

## 27. Troubleshooting

### 27.1 Server and access

| Symptom | Checks and action |
|---|---|
| UI does not open | Check `Get-Service Morgana`, `/health`, TCP 8888 listener, firewall scope, and service logs. |
| Port already in use | Identify the approved process using TCP 8888. Reconfigure only through a controlled service change; generated shortcuts assume 8888. |
| Browser certificate warning | Install the Morgana CA, use a SAN-matching host/IP, check clock, and restart browser. Do not trust the leaf certificate as a root. |
| Sign-in returns Invalid credentials | Verify the local account, keyboard layout, account state, and password-vault record. Do not repeatedly guess the bootstrap password. |
| Session repeatedly expires | JWT default is 24 hours; check server time and whether the signing configuration changed on restart. Sign in again. |
| UI actions return HTTP 401 | Browser token or stored API key is invalid. Log out, sign in, and replace revoked integration keys. |

### 27.2 Agents and Jobs

| Symptom | Checks and action |
|---|---|
| Agent never appears | Verify target can reach HTTPS 8888, deployment used correct server address, service exists, and Agent log shows registration. |
| Linux download is 404 | Installed server does not include the Linux Agent binary. Obtain the correct release. |
| Agent becomes offline | Check service, DNS, route, TLS reachability, target sleep/reboot, and last Agent log entry. |
| Job remains pending | Agent may be offline or the in-memory queue may have been lost on restart. Pending Jobs are not reconciled automatically. Confirm the Agent state and Job ID; delete the stale Test/Job before deliberately starting a replacement. |
| Test becomes timeout | Agent was unavailable beyond Job timeout plus grace. Inspect target processes because a late endpoint process may have run even when the server timed out. |
| Console window not visible | Sign in interactively to the Morgana server, check server Console logs, and ensure the Agent connects within 30 seconds. |
| Console is connected but GUI app is invisible | Agent runs in service Session 0. Use CLI tools only. |

### 27.3 Scripts and Chains

| Symptom | Checks and action |
|---|---|
| Script saves but fails immediately | Confirm executor exists, platform matches, syntax is correct, and all dependencies are installed. |
| Literal `#{tag_key}` reaches the shell | Tag is missing, not marked runtime, or has no assignment/global/default value. Reopen **+ Add Tag** and inspect server warning. |
| Inline output times out | Open **Tests**; the editor stops polling after about 60 seconds while the Job can continue. |
| Cleanup reports an error | Inspect cleanup section in stderr, reverse artifacts manually under approval, and correct the cleanup command. |
| Catalog cannot refresh | Allow GitHub raw HTTPS access and inspect proxy/TLS/server logs. |
| Pack update did not replace a Script | The Script is marked user-modified. Use **Reset to Pack**, review, and save. |
| Chain shows `partial_fail` | Open execution Log and each linked Test. The Chain intentionally continued after failure. |
| Progress modal stays Running after partial failure | Close it and use **Recent Executions**; `partial_fail` is terminal but the current modal polling recognizes fewer terminal labels. |
| Branch took unexpected path | Matching uses only prior stdout, case-insensitive. It ignores stderr and exit code. |

### 27.4 Detection Fabric

| Symptom | Checks and action |
|---|---|
| Defender XDR Not Configured | Enter Tenant ID and Client ID, save a client secret, and test. |
| `invalid_client` | Verify App/Client ID and secret value/expiry. Do not paste the secret identifier in place of its value. |
| `unauthorized_client` or Graph 403 | Grant required Application permissions and administrator consent. For hunting, add `ThreatHunting.Read.All`. |
| Sync fetches zero | Expand lookback, verify source has incidents/alerts, check tenant, source timestamps, and adapter state. |
| Universal file remains | Validate Morgana JSON shape and inspect Run History/Errors. Only successful imports are deleted. |
| No Telemetry | Adapter coverage does not fully close the Test window, the Test did not succeed, or the post window remains open. Sync again after source data arrives. |
| Possible Detection | Inspect Related Detections and Correlation audit. Evidence is not strong enough to confirm. |
| Not Detected seems wrong | Verify healthy coverage, Agent-side timestamps, source timestamps, marker visibility, and score changes; force revalidation after new evidence. |
| Sync run interrupted | Reopen Tests; Morgana marks active runs interrupted after restart and supports resume. |

### 27.5 AI and reports

| Symptom | Checks and action |
|---|---|
| AI Not Ready | Enable runtime AI through API if disabled, configure provider credentials/model, and Test Connection. |
| GitHub token missing | Complete device flow on the server and verify the service can access the persisted token. |
| HTTP 401 | Replace provider key/token and test before saving. |
| HTTP 429 | Wait for provider reset or select another approved provider/model; Morgana retries several times with backoff. |
| AI timeout | Verify model health and network; use a faster model or raise runtime timeout through the API. |
| Ollama/LM Studio refused | Confirm service is running on the Morgana host and reachable from the Windows service context. |
| Non-JSON review | Retry with a model that follows structured output. Inspect raw provider/server error. |
| Intelligent Report fails | Confirm selected scope has meaningful evidence, Report Agent is configured, and model supports reliable JSON. Use Export Report ZIP meanwhile. |
| Offline report does not open | Extract the full ZIP, run its `.cmd` launcher, keep PowerShell open, and preserve folder structure. |

### 27.6 Backup and upgrade

| Symptom | Checks and action |
|---|---|
| Backup fails | Verify free disk, database access, backup directory ACL, and server log. |
| Restored data looks unchanged | Restart the server after restore and confirm the selected filename/time. |
| Adapter secret fails after recovery | Restore the Detection Fabric encryption key with the encrypted store, or enter a new secret. |
| Update check fails | Verify server HTTPS access to the public Camelot version manifest. Manual operation can continue. |
| Service fails after upgrade | Review update/service logs, verify executable and data ACLs, and restore the tested backup or previous approved installer. |

## 28. FAQ

### Is Morgana safe to expose through a public reverse proxy?

No. Current Agent enrollment, Agent authentication, Job signing, certificate verification, and route authorization require trusted-network compensating controls.

### Does a finished Test mean the attack was detected?

No. `finished` means main process exit code 0. Use Detection Fabric evidence for Confirmed/Possible/Not Detected/No Telemetry outcomes.

### Does a blocked AI status prove an alert exists?

No. It is an AI interpretation of endpoint output. Detection Fabric must independently correlate source evidence.

### Does cleanup always run?

No. When an Agent remains alive through a normal Job attempt, it runs a non-empty cleanup command after the main command regardless of the main exit code. Agent termination, host loss, forced process termination, or an unreceived Job can prevent cleanup. Cleanup can also fail or leave descendant-process artifacts. Verify output and endpoint state.

### Can I cancel a Test, Chain, or Campaign?

Not through the current API/UI. Stop initiating new work, isolate the target if required by the incident procedure, and manage the endpoint process through an authorized administrative channel.

### Can I approve Agents before they execute?

No. There is no approval state in 0.4.0. Network allowlisting is mandatory.

### Are Tags a password vault?

No. Runtime values are stored in the database and can be displayed to authorized operators.

### Is Red Canary Atomic Red Team the native library?

No. Excalibur is the native package model. Some community Excalibur-format packs are converted from Red Canary source material.

### Can the server run on Linux?

No. The current installed server is Windows-only. Linux is an Agent platform.

### Can I update Agents from the server?

No. Remove and redeploy them from the updated server.

### Does database backup protect everything?

No. Use a complete protected backup of `%ProgramData%\Morgana` for disaster recovery.

### Can I use AI without sending data to a cloud provider?

Yes, with a locally hosted Ollama or LM Studio service. The data still exists on the Morgana host and in model-server memory/logs according to that product's settings.

### Why is a Campaign completed when a nested Test failed?

Campaign completion currently records that orchestration finished. Inspect nested execution logs and Tests for outcome quality.

## 29. Accessibility and Keyboard Use

Morgana 0.4.0 has no published keyboard-shortcut map or accessibility conformance statement.

- Use standard browser `Tab` and `Shift+Tab` navigation for native controls.
- `Enter` submits many focused form actions; `Escape` closes some, but not all, modals.
- Sortable table headings and many icon-like controls are mouse-oriented.
- Large tables can require horizontal scrolling.
- The visible **Console** action opens a native PowerShell terminal on the Morgana server; keyboard and accessibility behavior follows that terminal and the remote shell.

Operators who require assistive technology should validate critical workflows in a non-production instance and keep an API-based alternative for tasks the UI cannot complete accessibly.

## 30. Glossary

| Term | Definition |
|---|---|
| Agent PAW | Short unique identifier assigned at Agent registration |
| Assurance outcome | Detection Fabric classification based on execution, coverage, and evidence |
| Break-glass account | Non-removable local administrator identity for recovery |
| Candidate | Detection whose score meets the possible threshold for a Test |
| Cleanup | Command automatically executed after a normal Job's main command |
| Correlation fingerprint | Hash of Test, configuration, model context, and candidate evidence used for cache validity |
| Excalibur | Morgana's native package format and catalog |
| Executor | Shell/runtime used by the Agent: PowerShell, `cmd`, Bash, Python, `sh`, or manual |
| Marker | Per-Test value injected into execution context to support exact detection correlation |
| Named API key | Purpose-labeled key stored by hash and shown in plaintext once |
| Runtime Tag | Tag Definition whose value replaces a `#{key}` placeholder |
| Workspace | Saved Tag selector used as a global UI filter, not an authorization boundary |

## 31. References

- [Morgana release directory](Install/)
- [Current version manifest](Install/version.json)
- [Excalibur catalog](excalibur/catalog.json)
- [Complete server uninstall script](uninstall/03-uninstall-morgana.ps1)
- [MITRE ATT&CK](https://attack.mitre.org/)
- [X3M.AI contact](https://x3m.ai/contact/)
- [Camelot community discussions](https://github.com/x3m-ai/Camelot/discussions)

---

Morgana is developed by [X3M.AI Ltd](https://x3m.ai). Product behavior in this manual was verified against the Morgana 0.4.0 UI, registered server routes, models, configuration, Agent implementation, installer, and lifecycle scripts current on 27 August 2026.