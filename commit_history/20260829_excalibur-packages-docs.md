# Excalibur Packages — Complete Documentation + ACN-ST Rename

**Date:** 2026-08-29
**Repository:** Camelot
**Commit:** See git log

## Purpose

1. Remove all `ACN-ST-` prefixes from the Entra ID Excalibur pack (replaced with `Excalibur-`).
2. Create the authoritative `PACKAGES.md` package reference documentation.
3. Update `README.md` to link to `PACKAGES.md` and remove the hardcoded detection rule list.
4. Update the Morgana manual (`morgana/README.md`) to link to `PACKAGES.md`.

---

## 1. ACN-ST- → Excalibur- rename

**File:** `morgana/excalibur/technology/excalibur-entraid-emulation-pack.json`

- Replaced all 220 occurrences of `ACN-ST-` with `Excalibur-` across all script names, chain names, and references.
- The `ACN-ST-` prefix was a client-specific naming convention (Accenture) that should not be in the public repository.
- All 23 scripts and 22 chains now use the `Excalibur-` prefix consistently.

**File:** `morgana/excalibur/entraid-emulation-pack-test-execution-log.md`
- Remaining `ACN-ST-` references replaced with `Excalibur-`.

**Result:** Zero `ACN-ST-` references remain anywhere in the Camelot repository.

### Script names after rename (sample)

```
Excalibur - Excalibur-EntraID-Group Deleted (Create)
Excalibur - Excalibur-EntraID-Bulk Changes to Privileged Account Permissions
Excalibur - Excalibur-EntraID-Privileged Role Assigned Outside PIM
Excalibur - Excalibur-EntraID-MFA disabled for a user
Excalibur - Excalibur-TH-UEBA-Anomalous Password Reset
Excalibur - Excalibur-UEBA-Anomalous Microsoft Entra ID Account Manipulation
Excalibur - Excalibur-Auditlogs-Entra ID Role Assignment Permanent
Excalibur - Excalibur-EntraID-Consent Phishing - Admin Consent
Excalibur - Excalibur-AuditLogs-EntraID-Sensitive Group Modification Detection
Excalibur - Excalibur-EntraID-Attempts to sign in to disabled accounts
Excalibur - Excalibur-EntraID-Auth-Brute force attack against Azure Portal
Excalibur - Excalibur-SigninLogs-Nimbus Logging in Outside The VPN
Excalibur - Excalibur-EntraIDProtection-Anonymous IP address
```

---

## 2. New file: PACKAGES.md

`morgana/excalibur/PACKAGES.md` — authoritative package reference documentation.

**Contents:**
- Catalog summary table: 224 packages, 26,323 scripts, 2,121 chains across 11 providers
- Full section per provider:
  1. X3M.AI Excalibur Packs (2 packs)
  2. Red Canary — Atomic Red Team (13 packs, 1,603 scripts)
  3. MITRE CALDERA Stockpile (11 packs, 221 scripts)
  4. MITRE CTID Adversary Emulation (24 packs)
  5. LOLBAS & GTFOBins (49 packs, 4,057 scripts)
  6. LOLDrivers (58 packs, 18,766 scripts)
  7. Frida Mobile (40 packs, 830 scripts — Android, iOS, Flutter, React Native, Unity, Xamarin)
  8. MITRE CALDERA OT (15 packs, 223 scripts+chains)
  9. ICS-SCADA-Fuzzer (5 packs, 120 scripts)
  10. ANSSI FuzzySully (7 packs, 79 scripts)
- Per-package: Package ID, scripts, chains, ATT&CK domain, execution platform, target environment, prerequisites, tags, source references
- Package update workflow
- Source attribution table with licenses

---

## 3. README.md updates

`morgana/excalibur/README.md`:
- Added prominent link to `PACKAGES.md` at the top
- Replaced the hardcoded `### Detection Rules Covered` section (which listed all 22 `ACN-ST-EntraID-*` rules by name) with a brief `### Detection Coverage` note
- Updated Available Packages table to show all 11 providers with counts

---

## 4. Morgana manual link

`morgana/README.md` — Section 10 (Excalibur Packs):
- Added link to `PACKAGES.md` on GitHub for the full package reference

---

## Files Modified/Created

| File | Change |
|---|---|
| `morgana/excalibur/PACKAGES.md` | **NEW** — complete package reference documentation |
| `morgana/excalibur/technology/excalibur-entraid-emulation-pack.json` | ACN-ST- → Excalibur- rename (220 occurrences) |
| `morgana/excalibur/entraid-emulation-pack-test-execution-log.md` | ACN-ST- → Excalibur- rename |
| `morgana/excalibur/README.md` | Added PACKAGES.md link, removed hardcoded detection rule list, updated provider table |
| `morgana/README.md` | Added PACKAGES.md link in Section 10 |
| `commit_history/20260829_excalibur-packages-docs.md` | This record |
