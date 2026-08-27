# Excalibur Packages

Excalibur is the certified adversary emulation script library for the **Morgana Advanced Red Team Platform**.

Excalibur packages are professionally crafted attack script collections covering real-world MITRE ATT&CK tactics and techniques. Each package targets a specific platform, identity domain, or detection surface and is designed for authorised Purple Team and Red Team exercises — including adversary emulation, kill chain execution, and detection validation against enterprise security controls (Microsoft Sentinel, Defender for Endpoint, and others).

> **Access notice:** Excalibur packages run inside Morgana, which is a controlled-distribution platform. To use Excalibur packs for Red Team or Purple Team operations, you must have authorised access to Morgana. [Contact X3M.AI](https://x3m.ai/contact/) to request access.

---

## Available Packages

| Category | Source | Purpose |
|---|---|---|
| Excalibur | X3M.AI | Curated Morgana-native adversary emulation packs |
| [Atomic Red Team](art/) | Red Canary | Atomic tests converted to Morgana pack JSON |
| [MITRE CALDERA Stockpile](stockpile/) | MITRE | Command-based Stockpile abilities converted to Morgana pack JSON |

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

### Detection Rules Covered

All 22 chains map 1:1 to Microsoft Sentinel Entra ID analytics rules (`ACN-ST-EntraID-*`):

- ACN-ST-EntraID-Attempts to sign in to disabled accounts
- ACN-ST-EntraID-Brute force attack against Azure Portal
- ACN-ST-EntraID-Bulk changes to privileged account permissions
- ACN-ST-EntraID-Credential added to Service Principal
- ACN-ST-EntraID-Distributed Password cracking attempts in AzureAD
- ACN-ST-EntraID-ExplicitMFADeny
- ACN-ST-EntraID-FailedLogonToAzurePortal
- ACN-ST-EntraID-GuestAccountInvite
- ACN-ST-EntraID-Impossible travel activity
- ACN-ST-EntraID-Mail.Read Permissions Granted to Application
- ACN-ST-EntraID-MaliciousOAuthApp
- ACN-ST-EntraID-Multi-Factor Authentication Disabled
- ACN-ST-EntraID-Multiple admin membership removals from newly created admin
- ACN-ST-EntraID-NRT PIM Elevation Request Rejected
- ACN-ST-EntraID-New access credential added to Application or Service Principal
- ACN-ST-EntraID-New Admin account activity seen which was never seen before
- ACN-ST-EntraID-Password spray attack against Azure AD application
- ACN-ST-EntraID-Privileged Role Assigned Outside PIM
- ACN-ST-EntraID-Sign-ins from IPs that attempt sign-ins to disabled accounts
- ACN-ST-EntraID-Suspicious application consent similar to O365 Attack Toolkit
- ACN-ST-EntraID-Suspicious application consent similar to PwnAuth
- ACN-ST-EntraID-Suspicious granting of permissions to an account
