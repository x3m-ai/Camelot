# Morgana - Installation Guide

> **Current release: morgana-v0.4.3** (02 November 2026) - installation-test candidate, directory distribution, clean installation database, optional local AI Pack. VM acceptance pending.

> **Morgana** is the X3M.AI Red Team execution and Test Intelligence platform for
> Purple Teaming - adversary emulation, penetration testing and Purple Team
> automation with an optional local AI capability.
> Free to download. Tightly integrated with [Merlino](https://x3m.ai/merlino/).

> **This build is an installation-test candidate.** It has been built, signed and
> published, but it has **not yet been accepted on a clean Windows VM**. Treat it
> as a candidate, not as a production-accepted release.

> **Responsible use:** Morgana must only be used for authorised Red Team and
> Purple Team operations within environments where testing has been formally
> approved. It must not be used for unauthorised access, offensive activity, or
> testing against systems without explicit written permission.

---

## What is in this folder

| File | Purpose | Size | SHA-256 |
|------|---------|------|---------|
| `Morgana-Server-Setup.exe` | Windows installer. Contains the application, its runtime and a clean installation database. | 52.5 MB | `da24d879b56c9a5a438a763473dfa5872ba1c6b20a6a16c642a5a19186a41e74` |
| `morgana-ai-runtime-0.3.35.zip` | Optional inference runtime for the local AI Pack. Only needed if you install the AI Pack. | 2.4 MB | `a86665c628fec26707c78a7f88733d0a09c15a3dffe234f465030c295d241b7d` |
| `release-manifest.json` | Machine-readable release manifest: version, status, URLs, sizes, hashes, signature state. | - | - |
| `SHA256SUMS.txt` | Checksums of the downloadable files. | - | - |
| `THIRD-PARTY-NOTICES.md` | Licence and attribution notices for redistributed components. | - | - |
| `release.json` | Release feed polled by the Morgana in-app update check. | - | - |
| `version.json` | **Legacy** feed for already-installed older clients. Not part of this release. | - | - |

The installer does **NOT** contain model weights, operational data, demo records
or credentials. The optional AI model is downloaded separately when you install
the AI Pack.

---

## Download

Both files are public and require no authentication and no GitHub account:

- Installer: https://github.com/x3m-ai/Camelot/raw/main/morgana/Install/Morgana-Server-Setup.exe
- AI runtime: https://github.com/x3m-ai/Camelot/raw/main/morgana/Install/morgana-ai-runtime-0.3.35.zip

Pinned to this exact release: `https://github.com/x3m-ai/Camelot/raw/morgana-v0.4.3/morgana/Install/...`

Verify what you downloaded before running it:

```powershell
Get-FileHash .\Morgana-Server-Setup.exe -Algorithm SHA256
# expected: da24d879b56c9a5a438a763473dfa5872ba1c6b20a6a16c642a5a19186a41e74

Get-FileHash .\morgana-ai-runtime-0.3.35.zip -Algorithm SHA256
# expected: a86665c628fec26707c78a7f88733d0a09c15a3dffe234f465030c295d241b7d
```

---

## Requirements

| Component | Requirement |
|-----------|-------------|
| Server OS | Windows 10 / 11 / Server 2019 or later (64-bit) |
| RAM | 512 MB minimum, 1 GB recommended (plus ~4 GB more for the local AI Pack) |
| Disk | 500 MB minimum, plus ~6 GB if you install the local AI Pack |
| Network | Agent machines must reach the server on **TCP 8888** |
| Browser | Chrome 120+ or Edge 120+ (for the web UI) |
| Python / Go / Visual Studio | **None.** The installer is self-contained. |

> **Antivirus note:** validation scripts intentionally trigger AV by design.
> Add a Windows Defender exclusion for `C:\ProgramData\Morgana\` on both the
> server and any agent machine. This is expected and required.

---

## Installation on a clean Windows VM

### Step 1 - Run the installer

Right-click `Morgana-Server-Setup.exe` and choose **Run as Administrator**, or
use the silent form:

```powershell
Start-Process -FilePath ".\Morgana-Server-Setup.exe" `
    -ArgumentList "/VERYSILENT", "/NORESTART", "/LOG=C:\morgana-install.log" `
    -Verb RunAs -Wait
```

The installer:

1. Copies the complete application tree to `C:\Program Files\Morgana Server`
2. Initializes `C:\ProgramData\Morgana\db\morgana.db` from the shipped clean
   seed - **only if no database exists there already**
3. Installs and starts the Windows NT Service `Morgana`
4. Generates a self-signed TLS certificate and trusts it locally
5. Opens TCP 8888 inbound

Expected database after a fresh install: schema at the current version with two
bootstrap records only - the break-glass administrator and the ad-hoc script
placeholder. **No tests, chains, campaigns, agents or customer data.**

### Step 2 - Open the web UI

```
https://localhost:8888/ui/
```

| Field | Value |
|-------|-------|
| Username | `admin@admin.com` |
| Password | `admin` |

> **Change this password immediately** in the web UI after first sign-in.

### Step 3 - Add the Defender exclusion

```powershell
Add-MpPreference -ExclusionPath "C:\ProgramData\Morgana"
```

### Step 4 - Load an Excalibur script pack

The script library is empty after a fresh install. Morgana uses **Excalibur
Packs**, not Atomic Red Team.

1. Go to **Execution -> Scripts**
2. Click **Refresh catalog**
3. Choose a pack (for example `excalibur-execution-v1`) and click **Install**

### Step 5 - Generate an API key

1. Go to **Administration -> Admin**
2. Click **Generate API Key**
3. Copy it immediately - it is not shown again

This key connects Merlino and installs agents.

---

## Installing the optional local AI Pack

The core product works fully without any AI model. Local inference is optional.

1. Sign in to the web UI
2. Go to **AI -> Local AI Pack**
3. Click **Install** on **Morgana Local AI - Qwen3.5-4B**

The install uses the AI runtime archive **already shipped inside the installer**
(`<install dir>\ai-runtime\`), so no internet access is needed for the runtime.
The model weights (~2.7 GB) are downloaded from the pinned upstream location, or
imported offline:

- **Online:** click Install and wait for the download and verification
- **Air-gapped:** download `Qwen3.5-4B-Q4_K_M.gguf` from
  `https://huggingface.co/unsloth/Qwen3.5-4B-GGUF` at revision
  `e87f176479d0855a907a41277aca2f8ee7a09523`, then use **Import from file** and
  optionally supply `morgana-ai-runtime-0.3.35.zip` as the runtime archive

Every artifact is SHA-256 verified against the pinned digest **before**
activation. `INSTALLED` only means the files are in place and verified.

### Self-test

After the pack reports `INSTALLED`, click **Run self-test**. A healthy result
returns a structured verdict from the model (`BLOCKED` / `INCONCLUSIVE` /
`ATTACK_DETECTED` with evidence). A model that returns no detection evidence is
deterministically downgraded to `INCONCLUSIVE` rather than being trusted.

The self-test is the only proof that inference works. Installation on its own is
not.

**Hardware:** CPU inference only. ~4 GB of RAM for the model, ~6 GB free disk.
The weights are memory-mapped, so the full size does not need to be resident in
RAM.

---

## Rerun preservation check

Prove that reinstalling does not destroy your data, using a harmless record:

1. In the web UI create a campaign named `vm-preservation-check`
2. Run the installer again (same version is fine)
3. Refresh the web UI and confirm `vm-preservation-check` still exists

The installer preserves an existing `C:\ProgramData\Morgana\db\morgana.db`
byte-for-byte. It refuses to overwrite it, and a database that appears during
seeding is also preserved.

---

## Agent installation

The agent is a lightweight OS service installed on target machines. It beacons to
the server, receives jobs, executes scripts and reports results.

1. Go to **Intelligence -> Agents**
2. Click **Deploy Agent**
3. Copy the one-liner PowerShell command and run it **as Administrator** on the
   target machine

The server pre-configures the command with its own URL and API key. The agent
appears in the **Agents** page within one beacon interval (default 30 s).

The server delivers the agent binary itself at `/download/morgana-agent.exe` and
`/download/morgana-worker.exe`, so no separate agent download is needed.

---

## Merlino integration

Morgana is a drop-in replacement for Caldera in Merlino.

1. In Merlino open **Settings**
2. Under **Caldera / Morgana** enter:
   - **URL:** `https://YOUR_MORGANA_SERVER:8888`
   - **API Key:** the key from **Administration -> Admin**
3. Click **Save**

No other change is required. Merlino's existing Synchronize, Tests & Operations
and Agents views work unchanged.

---

## Silent / unattended installation

```powershell
Start-Process -FilePath ".\Morgana-Server-Setup.exe" `
    -ArgumentList "/VERYSILENT", "/NORESTART", "/LOG=C:\morgana-install.log" `
    -Verb RunAs -Wait
```

---

## Upgrading

1. Download the new installer from this folder
2. Run it - it stops the service, replaces the application and restarts it
3. Your database, API key and settings are preserved automatically
4. Reboot afterwards to be sure the new service version loads cleanly

> The in-app **Check Update** banner links to the installer. This release is a
> directory distribution, so the in-app updater deliberately **will not** replace
> your installation in place - download and run the installer.

---

## AI Review Engine

Morgana includes a review engine that analyses completed test results: what ran,
what was detected, what was missed, and recommended detections.

The default provider is **GitHub Models**, authenticated through the GitHub CLI
already on the machine. Install https://cli.github.com/ and run `gh auth login`
once. Alternative providers (Azure OpenAI, OpenAI, Anthropic, Ollama, custom) are
configured under **AI -> Settings**.

The local AI Pack above is a separate, fully offline capability.

---

## Uninstalling

Use **Apps & features -> Morgana Server -> Uninstall**, or:

```powershell
& "C:\Program Files\Morgana Server\unins000.exe" /VERYSILENT
```

`C:\ProgramData\Morgana\` (database, certificates, logs, AI packs) is preserved
deliberately. Delete it manually for a complete removal.

---

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| Browser warns about the certificate | The self-signed cert was not trusted | Open `https://localhost:8888` once and accept, or reinstall |
| `ERR_CONNECTION_REFUSED` on 8888 | Service not running | `sc query Morgana` then `sc start Morgana` |
| UI loads, API calls fail | API key missing in the browser | Sign in again |
| Agent never appears | Port 8888 blocked, or agent not installed as Administrator | Check firewall and run the deploy command elevated |
| AI Pack stuck in `DOWNLOADING` | No route to the model host | Use the offline import path |
| AI Pack `INSTALLED` but self-test fails | Backend or memory problem | Check `C:\ProgramData\Morgana\logs\server.log` |

Service logs: Windows Event Viewer, source `Morgana`.
Application log: `C:\ProgramData\Morgana\logs\server.log`.

---

## Links

- Community repository and packs: https://github.com/x3m-ai/Camelot
- This Install folder: https://github.com/x3m-ai/Camelot/tree/main/morgana/Install
- Licensing and product terms: see the `LICENSE` file in the repositories
