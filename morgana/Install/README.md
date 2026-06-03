# Morgana - Installation Guide

> **Current release: v0.3.6** (03 June 2026) - auto-update, SHA256 verification, rollback

> **Morgana** is the X3M.AI Red Team execution platform for Purple Teaming.  
> Free, Windows-native, zero dependencies. Tightly integrated with [Merlino](https://x3m.ai/merlino/).

---

## What is Morgana?

Morgana is a lightweight Red Team platform built from the ground up by X3M.AI.  
It replaces Caldera and is designed specifically for Purple Teaming workflows with Merlino.

**Key concepts:**

| Term | Meaning |
|------|---------|
| **Script** | Atomic execution unit (PowerShell / cmd / bash / Python) |
| **Chain** | Ordered sequence of scripts forming a kill chain |
| **Test** | Single execution run, linked to a Merlino row |
| **Campaign** | Named exercise grouping multiple tests |
| **Agent** | Lightweight OS service installed on the target machine |

Script library is powered by **Red Canary Atomic Red Team** (4,500+ techniques).

---

## Requirements

| Component | Requirement |
|-----------|-------------|
| Server OS | Windows 10 / 11 / Server 2019 or later |
| Agent OS | Windows 10 / 11 / Server 2019 or later (Linux support coming) |
| RAM | 512 MB minimum, 1 GB recommended |
| Disk | 500 MB minimum (more for Atomic scripts cache) |
| Network | Agent machines must reach the server on **TCP 8888** |
| Browser | Chrome 120+ or Edge 120+ (for the web UI) |

> **Antivirus note:** Atomic Red Team scripts intentionally trigger AV.  
> You must add a Windows Defender exclusion for `C:\ProgramData\Morgana\` on both  
> the server and any agent machine. This is expected and required by design.

---

## Download

Download the latest Windows installer directly:

**[Download Morgana-Server-Setup.exe](https://github.com/x3m-ai/Camelot/raw/main/morgana/Install/Morgana-Server-Setup.exe)**

> The installer is self-contained (~25 MB). No internet connection required after download.  
> Always use the latest version from this folder.

> **Browser / SmartScreen warning:** Your browser or Windows SmartScreen may flag the download with a security warning. This is expected for new software — the executable is **digitally signed by X3M.AI Ltd** and is safe to run. Click **Keep** (browser) or **Run anyway** (SmartScreen) to proceed.

---

## Installation (Windows - Recommended)

### Step 1 - Run the installer

1. Right-click **`Morgana-Server-Setup.exe`** and choose **Run as Administrator**
2. Follow the wizard (or use `/VERYSILENT` for silent install)
3. The installer will:
   - Install the Morgana Server as a Windows NT Service (`Morgana`)
   - Auto-start the service on boot
   - Generate a self-signed TLS certificate
   - **Install the certificate into the Windows Trusted Root store** (so your browser shows a padlock, not a warning)
   - Open firewall port 8888 (TCP Inbound)
   - Optionally create a **desktop shortcut** (if selected during setup) — double-click it to open the Morgana web UI directly

### Step 2 - Open the web UI

After installation, open your browser and go to:

```
https://localhost:8888/ui/
```

Default credentials:

| Field | Value |
|-------|-------|
| Username | `admin@admin.com` |
| Password | `admin` |

> **Change the password** in Settings after first login.

### Step 3 - Load Atomic Red Team scripts

On first run the script database is empty. To load the full Atomic Red Team library:

1. Go to **Scripts** in the left sidebar
2. Click **Refresh Canary Scripts**
3. Wait ~30 seconds while 4,500+ scripts are indexed

### Step 4 - Add Windows Defender exclusion (important)

Red Team scripts trigger Defender by design. Add the Morgana data directory to exclusions:

1. Open **Windows Security** > **Virus & threat protection** > **Manage settings**
2. Scroll to **Exclusions** > **Add or remove exclusions**
3. Add folder: `C:\ProgramData\Morgana\`

Do the same on every machine where you install the Morgana Agent.

---

## API Key

To get the API key needed to connect Merlino (or to install agents):

1. Open the Morgana web UI: `https://localhost:8888/ui/`
2. Go to **Admin** in the left sidebar
3. Click **Generate API Key**
4. **Copy the key immediately** and save it somewhere safe — it will not be shown again

> **Keep this key secret. Treat it like a password.**

---

## Agent Installation

The Morgana Agent is a lightweight OS service installed on **target machines**.  
It beacons to the server, receives jobs, executes scripts, and reports results.

---

### Morgana UI — Deploy Agent button (recommended)

1. Open the Morgana web UI: `https://YOUR_MORGANA_SERVER:8888/ui/`
2. Go to **Agents** in the left sidebar
3. Click **Deploy Agent**
4. Copy the one-liner PowerShell command and run it **as Administrator** on the target machine

The server generates the install script automatically, pre-configured with your URL and API key.

After installation the agent appears in the **Agents** page of the web UI within one beacon interval (default 30 seconds).

---

## Merlino Integration

Morgana is designed as a drop-in replacement for Caldera in Merlino.

1. In Merlino, open **Settings**
2. Under **Caldera / Morgana**, enter:
   - **URL:** `https://YOUR_MORGANA_SERVER:8888`
   - **API Key:** the key generated from the Morgana web UI (Admin → Generate API Key)
3. Click **Save**

That is all. No other changes are needed in Merlino.  
All existing Merlino workflows (Synchronize, Tests & Operations, Agents view) work identically.
### Merlino AI Assistant

Merlino has its own built-in AI assistant that can analyze your threat coverage, generate Red Team scenarios, and correlate Morgana test results with MITRE ATT&CK data. Configure it in Merlino under **Settings → AI**:

| Provider | Notes |
|----------|-------|
| **GitHub Copilot** | Free with a GitHub Copilot subscription — no extra API key |
| **OpenAI** | Requires an OpenAI API key |
| **Mistral** | Requires a Mistral API key |
| **Ollama** | Local inference — zero data egress |
| **Anthropic** | Requires an Anthropic API key |
| **AWS Bedrock** | Requires AWS credentials |

Once configured, the AI assistant is available in the **AI Assistant** taskpane inside Excel.
---

## Silent / Unattended Installation

```powershell
# Silent install with log
Start-Process -FilePath ".\Morgana-Server-Setup.exe" `
    -ArgumentList "/VERYSILENT", "/NORESTART", "/LOG=C:\morgana-install.log" `
    -Verb RunAs -Wait
```

---

## Upgrading

1. Download the new installer from the **[Morgana Install page](https://github.com/x3m-ai/Camelot/tree/main/morgana/Install)**
2. Run it — the installer stops the existing service, replaces the binary and restarts
3. Your database, API key and settings are **preserved automatically**
4. **Restart the machine** after upgrading — recommended to ensure the new NT Service version loads cleanly

---

## AI Review Engine

Morgana includes a built-in AI engine that automatically reviews completed test results and generates a structured analysis: what ran, what was detected, what was missed, and recommended detections.

### How it works

After a test finishes, the AI engine analyses the execution output against MITRE ATT&CK context and returns a structured review visible in the **Tests** page of the web UI.

### Default provider — GitHub Models (recommended, no API key needed)

Morgana uses the **GitHub Models** API by default, authenticated via the GitHub CLI (`gh`) OAuth token already on your machine.

**Prerequisites:**
1. Install the [GitHub CLI](https://cli.github.com/) (`winget install GitHub.cli`)
2. Log in once: `gh auth login`

That is all — no API keys, no extra accounts. The AI engine activates automatically.

### Alternative providers

If you prefer a different model, go to the Morgana web UI → **Settings → AI** and select one of:

| Provider | What you need |
|----------|---------------|
| **GitHub Models** | GitHub CLI logged in (default) |
| **GitHub Copilot** | GitHub Copilot subscription + `gh auth login` |
| **OpenAI** | OpenAI API key |
| **Ollama** | Ollama running locally (`ollama serve`) |
| **Anthropic** | Anthropic API key |
| **Azure OpenAI** | Azure OpenAI resource + API key |

### Enable / disable

The AI review engine is enabled by default. Toggle it in the web UI under **Settings → AI → Enable AI Review**.

---

## Uninstalling

```
Control Panel > Programs > Morgana Server > Uninstall
```

Or silently:
```powershell
Start-Process -FilePath "C:\Program Files\Morgana Server\unins000.exe" `
    -ArgumentList "/VERYSILENT" -Verb RunAs -Wait
```

The data directory (`C:\ProgramData\Morgana\`) is **not** removed on uninstall.  
Delete it manually if you want a complete clean removal.

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| Browser shows "Not secure" | Close all tabs and reopen. If it persists, run: `certutil -addstore -f Root "C:\ProgramData\Morgana\certs\server.crt"` as Administrator |
| Service does not start | Check `C:\ProgramData\Morgana\logs\service.log` and `server.log` |
| Port 8888 already in use | Edit `MORGANA_PORT` in the service environment (NSSM) or change port during install |
| Scripts not loading | Click **Refresh Canary Scripts** in the Scripts page. Requires internet access on first run |
| Agent not appearing | Verify firewall allows TCP 8888 from the agent machine to the server |
| Defender quarantines scripts | Add `C:\ProgramData\Morgana\` to Windows Defender exclusions |

**Log files:**

| File | Content |
|------|---------|
| `C:\ProgramData\Morgana\logs\server.log` | Application log (JSONL format) |
| `C:\ProgramData\Morgana\logs\service.log` | NSSM service stdout |
| `C:\ProgramData\Morgana\logs\service_error.log` | NSSM service stderr |

---

## Links

- **Merlino (Excel Add-in):** https://x3m.ai/merlino/
- **Community (Camelot):** https://github.com/x3m-ai/Camelot
- **Support:** open an issue on the [Camelot community repo](https://github.com/x3m-ai/Camelot/issues)

---

> Morgana is developed by [X3M.AI Ltd](https://x3m.ai) (UK).  
> Free to use. No registration, no telemetry, no data collection.
