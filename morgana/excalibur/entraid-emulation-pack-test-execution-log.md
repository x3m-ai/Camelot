# Excalibur — Entra ID Emulation Pack — Test Execution Log

> **Package:** `excalibur-entraid-emulation-pack.json` v1.0.0
> **Author:** X3M.AI
> **Date started:** ____________________
> **Tester:** ____________________
> **Environment:** Test tenant only — NEVER run against production

---

## Prerequisites Checklist

Before running any test, verify all of the following:

- [ ] Microsoft.Graph PowerShell module installed: `Install-Module Microsoft.Graph -Scope CurrentUser`
- [ ] Connected to Microsoft Graph: `Connect-MgGraph -Scopes 'Group.ReadWrite.All','User.ReadWrite.All','RoleManagement.ReadWrite.Directory','Policy.ReadWrite.AuthenticationMethod','AuditLog.Read.All'`
- [ ] Package imported in Morgana via the Import Package button on the Scripts page
- [ ] Microsoft Sentinel workspace open — Log Analytics ready for query verification
- [ ] Target Analytics Rules enabled in the Sentinel workspace
- [ ] Entra ID P2 license active in test tenant (required for UC#12, #13, #18, #21, #22)

---

## Morgana Status Reference

### Test Lifecycle State
Shown in the **State** column of the Morgana Tests table.

| State | Meaning |
|---|---|
| `pending` | Test dispatched to agent, not yet started |
| `running` | Agent is executing the script |
| `finished` | Script completed with exit code 0 |
| `failed` | Script completed with non-zero exit code |

### AI Review Status
Returned by the Morgana AI Review engine (`copilot_reviewer.py`). Shown in the **AI Review** column.

| Status | Meaning |
|---|---|
| `FINISHED` | Script executed cleanly — no defender interference detected |
| `FAILED` | Script execution failed (script error, not defender-related) |
| `ERROR` | Script itself is broken — syntax error, missing dependency, permission denied (unrelated to any defender) |
| `BLOCKED` | A defender (AV / EDR / WDAC / AMSI / AppLocker / SmartScreen / firewall) prevented execution |
| `INTERCEPTED` | Execution proceeded but a defender logged or warned without blocking — telemetry generated |

### Effective Status (composite — shown as badge in Morgana UI)
Derived from the combination of AI Review + Detection Fabric verdict.

| Effective Status | Condition | Badge Color |
|---|---|---|
| `DETECTED` | AI Review = `BLOCKED` AND Detection Fabric = `ATTACK_DETECTED` | Red |
| `BLOCKED` | AI Review = `BLOCKED` AND Detection Fabric did NOT detect | Orange |
| _(falls back to lifecycle state)_ | No AI Review result yet | Grey / default |

### Sentinel Alert Column (this log)
Tracks whether Microsoft Sentinel generated the expected alert.

| Value | Meaning |
|---|---|
| `[ ]` | Not yet verified |
| `YES` | Alert generated — detection rule fired |
| `NO` | Alert NOT generated — investigate |
| `PENDING` | Script run, waiting for log ingestion latency (5–15 min) |
| `N/A` | Detection not applicable in this environment |
| `SKIP` | Test skipped — reason in Notes |

---

## Test Execution Table

> **Important:** Always run the `cleanup_command` after each test.
> Allow 5–15 minutes between tests for log propagation to Sentinel.

### Group 1 — Identity & Group Management

| # | Detection Rule | Morgana Script | What It Does | State | AI Review | Effective Status | Sentinel Alert | Executed At | Notes |
|---|---|---|---|---|---|---|---|---|---|
| 1a | ACN-ST-EntraID-Group Deleted | `Morgana-EntraID-GroupCreate` | Creates test security group, saves ID to temp file | `[ ]` | | | | | Run BEFORE 1b |
| 1b | ACN-ST-EntraID-Group Deleted | `Morgana-EntraID-GroupDelete` | Deletes the test group created by 1a | `[ ]` | | | `[ ]` | | Run AFTER 1a |
| 2 | ACN-ST-EntraID-Bulk Changes to Privileged Account Permissions | `Morgana-EntraID-BulkPrivPermChange` | Creates 5 test users, adds all to privileged group in rapid succession | `[ ]` | | | `[ ]` | | |
| 3 | ACN-ST-EntraID-Account Created and Deleted in Short Timeframe | `Morgana-EntraID-AccountCreateDelete` | Creates user then deletes it within 5 seconds | `[ ]` | | | `[ ]` | | |
| 4 | ACN-ST-EntraID-User added to Microsoft Entra ID Privileged Groups | `Morgana-EntraID-AddUserPrivGroup` | Adds test user to Security Reader directory role | `[ ]` | | | `[ ]` | | |
| 16 | ACN-ST-AuditLogs-EntraID-Sensitive Group Modification Detection | `Morgana-EntraID-SensitiveGroupMod` | Adds then removes a member from a SENSITIVE-tagged group | `[ ]` | | | `[ ]` | | |

### Group 2 — Credential & Authentication Manipulation

| # | Detection Rule | Morgana Script | What It Does | State | AI Review | Effective Status | Sentinel Alert | Executed At | Notes |
|---|---|---|---|---|---|---|---|---|---|
| 5 | ACN-ST-EntraID-Authentication Methods Changed for Privileged Accounts | `Morgana-EntraID-ChangeAuthMethod` | Registers a phone MFA method then removes it | `[ ]` | | | `[ ]` | | |
| 9 | ACN-ST-EntraID-MFA disabled for a user | `Morgana-EntraID-MFADisabled` | Registers phone MFA, then removes it (MFA disabled) | `[ ]` | | | `[ ]` | | |
| 10 | ACN-ST-TH-UEBA-Anomalous Password Reset | `Morgana-EntraID-AnomalousPasswordReset` | Resets password on a test user | `[ ]` | | | `[ ]` | | UEBA — higher latency expected |
| 11 | ACN-ST-UEBA-Anomalous Microsoft Entra ID Account Manipulation | `Morgana-EntraID-AnomalousAccountManip` | 4 rapid property changes on a test user (job title, dept, display name) | `[ ]` | | | `[ ]` | | UEBA — higher latency expected |

### Group 3 — Privileged Role & PIM

| # | Detection Rule | Morgana Script | What It Does | State | AI Review | Effective Status | Sentinel Alert | Executed At | Notes |
|---|---|---|---|---|---|---|---|---|---|
| 6 | ACN-ST-EntraID-Privileged Role Assigned Outside PIM | `Morgana-EntraID-RoleOutsidePIM` | Assigns Reports Reader role directly (not via PIM) | `[ ]` | | | `[ ]` | | |
| 7 | ACN-ST-EntraID-Changes to PIM Settings | `Morgana-EntraID-ChangePIMSettings` | Inspects PIM policies (read-only baseline) | `[ ]` | | | `[ ]` | | See note below — read-only script |
| 8 | ACN-ST-EntraID-User Added to Admin Role | `Morgana-EntraID-AddUserAdminRole` | Adds test user to Helpdesk Administrator role | `[ ]` | | | `[ ]` | | |
| 12 | ACN-ST-Auditlogs-Entra ID Role Assignment Permanent | `Morgana-EntraID-PermanentRoleAssign` | Assigns Directory Readers permanently (no expiry, no PIM) | `[ ]` | | | `[ ]` | | Requires Entra ID P2 |
| 13 | ACN-ST-Auditlogs-Create new PIM role Assignment | `Morgana-EntraID-CreatePIMAssignment` | Creates eligible PIM assignment for test user | `[ ]` | | | `[ ]` | | Requires P2 + PIM enabled |
| 14 | ACN-ST-Auditlogs-Entra ID Role Management Permission Grant | `Morgana-EntraID-RoleMgmtPermGrant` | Grants RoleManagement.Read.Directory to a test service principal | `[ ]` | | | `[ ]` | | |

### Group 4 — App Registration & OAuth Abuse

| # | Detection Rule | Morgana Script | What It Does | State | AI Review | Effective Status | Sentinel Alert | Executed At | Notes |
|---|---|---|---|---|---|---|---|---|---|
| 15 | ACN-ST-EntraID-Consent Phishing - Admin Consent | `Morgana-EntraID-ConsentPhishing` | Creates multi-tenant test app, grants admin consent for User.Read.All | `[ ]` | | | `[ ]` | | |

### Group 5 — Sign-in Anomalies & Brute Force

| # | Detection Rule | Morgana Script | What It Does | State | AI Review | Effective Status | Sentinel Alert | Executed At | Notes |
|---|---|---|---|---|---|---|---|---|---|
| 17 | ACN-ST-EntraID-Attempts to sign in to disabled accounts | `Morgana-EntraID-SignInDisabledAcct` | Creates disabled user, attempts ROPC auth | `[ ]` | | | `[ ]` | | |
| 18 | ACN-ST-EntraID-Anomaly Sign In Event from an IP | `Morgana-EntraID-AnomalousSignInIP` | Queries risk baseline + guidance for anomalous IP test | `[ ]` | | | `[ ]` | | Requires login from different IP — see note |
| 19 | ACN-ST-EntraID-Auth-Brute force attack against Azure Portal | `Morgana-EntraID-BruteForceAzurePortal` | 5 consecutive failed auth attempts against token endpoint | `[ ]` | | | `[ ]` | | |
| 20 | ACN-ST-SigninLogs-Nimbus Logging in Outside The VPN | `Morgana-EntraID-NimbusOutsideVPN` | Creates svc-nimbus-* account, authenticates from non-VPN IP | `[ ]` | | | `[ ]` | | Requires Named Location configured in Sentinel |

### Group 6 — Entra ID Protection

| # | Detection Rule | Morgana Script | What It Does | State | AI Review | Effective Status | Sentinel Alert | Executed At | Notes |
|---|---|---|---|---|---|---|---|---|---|
| 21 | ACN-ST-EntraIDProtection-Anonymous IP address | `Morgana-EntraID-AnonymousIP` | Queries existing risk detections + guidance for Tor/proxy simulation | `[ ]` | | | `[ ]` | | Manual simulation from Tor/anonymizing proxy required |
| 22 | Create incidents based on Microsoft Entra ID Protection alerts | `Morgana-EntraID-IDProtectionIncident` | Verifies risky users and active risk detections, validates Sentinel incident creation | `[ ]` | | | `[ ]` | | Run LAST — relies on risk events from previous tests |

---

## Notes for Specific Tests

### UC#7 — Changes to PIM Settings (`Morgana-EntraID-ChangePIMSettings`)
The script is **read-only** — it inspects PIM policies but does not modify them. For a test that generates an actual audit log entry:
- Use `Update-MgPolicyRoleManagementPolicyRule` to change a notification threshold on a PIM policy
- Document the original value before changing
- Restore it immediately after Sentinel confirms the alert

### UC#18 — Anomalous Sign-In from IP (`Morgana-EntraID-AnomalousSignInIP`)
The script provides guidance only. To trigger the detection:
1. Sign in with a test account from the standard SGN network (trusted IP)
2. Connect via a different VPN or proxy
3. Sign in again with the same account from that IP
4. Sentinel correlates the IP change and anomaly score

### UC#20 — Nimbus Outside VPN (`Morgana-EntraID-NimbusOutsideVPN`)
Requires a **Named Location** in Sentinel/Conditional Access configured for the SGN VPN IP range. Verify that the Named Location exists before running this test.

### UC#21 — Anonymous IP (`Morgana-EntraID-AnonymousIP`)
Cannot be simulated via standard PowerShell. Options:
1. Authenticate to `https://myapps.microsoft.com` using Tor Browser
2. Use a known anonymizing VPN/proxy flagged by Entra ID Protection
3. Check if existing risk events of this type are already present in the tenant

### UC#22 — ID Protection Incident (`Morgana-EntraID-IDProtectionIncident`)
Run **last**. This test validates that Sentinel is correctly creating incidents from Entra ID Protection alerts — it relies on risk events generated by the earlier tests.

---

## Sentinel Verification Queries (KQL)

Use these queries in Log Analytics to verify audit events independently of the analytics rules.

```kql
// All Morgana test audit events in the last hour
AuditLogs
| where TimeGenerated > ago(1h)
| where TargetResources[0].displayName startswith "MorganaTest-"
    or InitiatedBy.user.userPrincipalName startswith "morganatest-"
| project TimeGenerated, ActivityDisplayName, TargetResources[0].displayName, Result

// Group Deleted (UC#1)
AuditLogs
| where TimeGenerated > ago(30m)
| where ActivityDisplayName == "Delete group"
| where TargetResources[0].displayName startswith "MorganaTest-GroupDeleted-"
| project TimeGenerated, ActivityDisplayName, TargetResources, InitiatedBy

// Brute Force sign-in attempts (UC#19)
SigninLogs
| where TimeGenerated > ago(1h)
| where UserPrincipalName startswith "morganatest-bf-"
| summarize Attempts=count() by UserPrincipalName, ResultType, bin(TimeGenerated, 5m)

// Nimbus / disabled account sign-in attempts (UC#17, UC#20)
SigninLogs
| where TimeGenerated > ago(1h)
| where UserPrincipalName startswith "morganatest-dis-"
    or UserPrincipalName startswith "svc-nimbus-morganatest-"
| project TimeGenerated, UserPrincipalName, IPAddress, ResultType, RiskLevelDuringSignIn

// PIM and role assignments (UC#6, #8, #12, #13, #14)
AuditLogs
| where TimeGenerated > ago(1h)
| where Category in ("RoleManagement", "Policy")
| where InitiatedBy.user.userPrincipalName startswith "morganatest-"
    or TargetResources[0].displayName startswith "MorganaTest-"
| project TimeGenerated, ActivityDisplayName, Category, TargetResources[0].displayName, Result
```

---

## Results Summary

| Group | Total | FINISHED | BLOCKED | INTERCEPTED | FAILED | ERROR | Sentinel YES | Sentinel NO | N/A / Skip | Pending |
|---|---|---|---|---|---|---|---|---|---|---|
| Identity & Group | 6 | | | | | | | | | |
| Credential & Auth | 4 | | | | | | | | | |
| Privileged Role & PIM | 6 | | | | | | | | | |
| App & OAuth | 1 | | | | | | | | | |
| Sign-in Anomalies | 4 | | | | | | | | | |
| Entra ID Protection | 2 | | | | | | | | | |
| **Total** | **23** | | | | | | | | | |

---

## Findings & Recommendations

> Document each missed detection and the recommended remediation action.

| # | Detection Rule | Sentinel Alert | AI Review | Alert Latency | Finding | Recommendation |
|---|---|---|---|---|---|---|
| | | | | | | |
