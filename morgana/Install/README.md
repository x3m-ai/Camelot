# Morgana - Installation Guide

> **Current release: v0.2.4** (23 April 2026) — fix: console window closes immediately on VM (Windows Defender was terminating PowerShell in C:\Windows\Temp; PS1 now written to Defender-excluded C:\ProgramData\Morgana\temp\)

> **Morgana** is the X3M.AI Red Team execution platform for Purple Teaming.  
> Free, open-source, Windows-native. Tightly integrated with [Merlino](https://merlino.x3m.ai).

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

The installer generates a unique API key stored at:

```
C:\ProgramData\Morgana\config\master-api-key.txt
```

You will need this key to connect Merlino and to install agents.

---

## Agent Installation

The Morgana Agent is a lightweight Windows service you install on target machines.  
It polls the server for jobs and executes scripts locally.

### Windows (run as Administrator on the target machine)

```powershell
# Download and install the agent - replace with your server IP and API key
$serverUrl = "https://YOUR_MORGANA_SERVER:8888"
$apiKey    = "YOUR_API_KEY"

Invoke-RestMethod "$serverUrl/ui/install.ps1" | Invoke-Expression
```

Or manually:

```powershell
.\install-agent-windows.ps1 -ServerUrl https://192.168.1.10:8888 -Token YOUR_API_KEY
```

After installation the agent appears in the **Agents** page of the web UI within seconds.

---

## Merlino Integration

Morgana is designed as a drop-in replacement for Caldera in Merlino.

1. In Merlino, open **Settings**
2. Under **Caldera / Morgana**, enter:
   - **URL:** `https://YOUR_MORGANA_SERVER:8888`
   - **API Key:** contents of `C:\ProgramData\Morgana\config\master-api-key.txt`
3. Click **Save**

That is all. No other changes are needed in Merlino.  
All existing Merlino workflows (Synchronize, Tests & Operations, Agents view) work identically.

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

1. Download the new `Morgana-Server-Setup.exe`
2. Run it - the installer stops the existing service, replaces the binary and restarts
3. Your database, API key and settings are **preserved automatically**

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

- **Merlino (Excel Add-in):** https://merlino.x3m.ai
- **Merlino Add-in:** https://merlino-addin.pages.dev
- **Community (Camelot):** https://github.com/x3m-ai/Camelot
- **Support:** open an issue on the [Camelot community repo](https://github.com/x3m-ai/Camelot/issues)

---

> Morgana is developed by [X3M.AI Ltd](https://merlino.x3m.ai) (UK).  
> Free to use. No registration, no telemetry, no data collection.
