# LOLRMM — Living Off the Land Remote Monitoring & Management

**Provider:** LOLRMM (MagicSword)  
**Source:** [magicsword-io/LOLRMM](https://github.com/magicsword-io/LOLRMM)  
**Commit:** `fa85960` | **License:** Apache-2.0  
**Website:** https://lolrmm.io/  
**Scripts:** 320 | **Packages:** 3 | **Tools:** 320  

---

## What is LOLRMM?

LOLRMM is a community-maintained catalog of legitimate Remote Monitoring and Management (RMM) and Remote Access Tool (RAT) software that may be abused by threat actors for persistence, lateral movement, and command-and-control.

It provides structured intelligence for:
- Threat hunting and endpoint investigation
- RMM discovery and detection engineering
- Application-control policy design
- Sigma detection rules and SIEM queries
- ATT&CK T1219 (Remote Access Software) coverage

---

## Packages

| Package | Scripts | Description |
|---|---|---|
| `lolrmm-windows-v1` | Windows tools | Read-only artifact-presence probes for Windows RMM/RAT tools |
| `lolrmm-multiplatform-v1` | Multi-platform tools | Cross-platform probes |
| `lolrmm-manual-v1` | Intelligence-only | Metadata profiles for tools without local artifact probes |

---

## Execution model

**Probe-capable (291 tools):** Bash read-only probe checks for known artifact presence:
- File paths and filenames
- Registry keys (Windows via PowerShell)
- Known file hashes
- Domain/network artifact metadata

**Manual profiles (29 tools):** Intelligence-only records where no safely probeable local artifact is available.

**All probes are read-only.** They do NOT install, modify, or remove software.

---

## Per-tool metadata preserved

- Tool name, category (RMM/RAT), description
- Supported OS, capabilities, privileges
- PE metadata (filenames, original filenames, description)
- Installation paths and disk artifact paths
- Registry keys
- Windows Event Log indicators (Event ID, Provider, Service)
- Known network domains and ports
- Code-signing metadata (signer, thumbprint)
- File hashes (SHA256/SHA1)
- Detections and Sigma rule links
- CVE/vulnerability references
- Source author, created/modified dates

---

## Important

LOLRMM tools are **legitimate software that can be abused**. Presence on an endpoint does not imply compromise — it requires context and investigation.

**Never acquire, install, or execute LOLRMM-cataloged tools without explicit authorization.**

See [LICENSE-NOTICE.md](LICENSE-NOTICE.md) for attribution.
