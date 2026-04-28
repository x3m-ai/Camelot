# Morgana Agent — Source Code

> **Version:** 0.2.0 | **Publisher:** X3M.AI Ltd (UK)  
> **Platform:** Windows (NT Service) / Linux (systemd)  
> **Language:** Go 1.22  

The Morgana Agent is a lightweight OS service installed on **target machines**.  
It beacons to the Morgana Server, receives jobs, executes scripts, and reports results — forming the execution layer of the Purple Team platform.

This folder contains the **full source code** of the agent, published here for transparency.  
You are free to inspect it, build it yourself, and install your own binary.

---

## Agent Installation — Three Options

### Option 1 — Morgana UI (recommended, easiest)

1. Open the Morgana web UI: `https://YOUR_MORGANA_SERVER:8888/ui/`
2. Go to **Agents** in the left sidebar
3. Click **Deploy Agent**
4. Copy the one-liner PowerShell command and run it **as Administrator** on the target machine

The server generates and serves the install script automatically, pre-configured with your server URL and API key.

---

### Option 2 — Pre-built binary

The compiled agent binary is bundled inside the Morgana Server installer.  
After installing Morgana Server, the agent binary is available at:

```
C:\Program Files\Morgana Server\morgana-agent.exe
```

To deploy it on a target machine:

```powershell
# Run as Administrator on the target machine
.\morgana-agent.exe install --server https://YOUR_MORGANA_SERVER:8888 --token YOUR_API_KEY
```

The agent installs itself as a Windows NT Service (`MorganaAgent`) and starts automatically.

---

### Option 3 — Build from source (this folder)

Use this if you want to audit the code, make customisations, or avoid running pre-built binaries.

#### Prerequisites

- [Go 1.22+](https://go.dev/dl/) installed on your build machine
- Git

#### Build (Windows)

```powershell
git clone https://github.com/x3m-ai/Camelot.git
cd Camelot\morgana\morgana-agent

go mod download
go build -o morgana-agent.exe .\cmd\agent\
```

#### Build (Linux)

```bash
git clone https://github.com/x3m-ai/Camelot.git
cd Camelot/morgana/morgana-agent

go mod download
go build -o morgana-agent ./cmd/agent/
```

#### Install after building

```powershell
# Windows — run as Administrator on the target machine
.\morgana-agent.exe install --server https://YOUR_MORGANA_SERVER:8888 --token YOUR_API_KEY

# Optional: set check-in interval (seconds, default 30)
.\morgana-agent.exe install --server https://YOUR_MORGANA_SERVER:8888 --token YOUR_API_KEY --interval 15
```

```bash
# Linux — run as root on the target machine
sudo ./morgana-agent install --server https://YOUR_MORGANA_SERVER:8888 --token YOUR_API_KEY
```

#### Verify the agent is running

```powershell
# Windows
.\morgana-agent.exe status

# Linux
sudo ./morgana-agent status
```

The agent should appear in the **Agents** page of the Morgana web UI within one beacon interval.

---

## Agent Commands

```
morgana-agent install   --server <url> --token <api_key> [--interval <seconds>]
morgana-agent uninstall [--purge]
morgana-agent run                   (foreground / debug mode)
morgana-agent status
morgana-agent version
```

---

## Architecture

```
Morgana Server (port 8888)
        |
        | HTTPS polling (beacon loop)
        |
Morgana Agent (NT Service / systemd)
        |
        | executes
        |
PowerShell / cmd / bash / Python scripts
```

- The agent **polls** the server — no inbound connections needed on the agent machine
- All communication is HTTPS (TLS 1.2+)
- Jobs are verified with HMAC before execution
- Results are posted back to the server immediately after execution

---

## Source Code Structure

```
cmd/agent/main.go          Entry point — CLI parsing (install/run/status/version)
internal/
  beacon/beacon.go         Polling loop — poll, receive job, execute, report result
  config/                  Configuration (server URL, token, interval)
  executor/                Script executors: PowerShell, cmd, bash, python
  service/windows.go       NT Service installation and lifecycle
  service/linux.go         systemd unit generation and lifecycle
  logger/                  Structured logger
  version/version.go       Single source of truth for agent version
go.mod / go.sum            Go module dependencies
```

---

## Note on this folder

This source code is automatically synced from the `x3m-ai/Morgana` repository  
every time the agent code changes. You are always looking at the latest released version.
