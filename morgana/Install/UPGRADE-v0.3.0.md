# Morgana Server — Upgrade Guide to v0.3.0

> **Release:** v0.3.0 — 18 May 2026  
> **From version:** any previous version (v0.2.x)

---

## What's new in v0.3.0

- **AI Review engine** — automated AI-powered analysis of test results with configurable LLM providers (Ollama, OpenAI, Mistral, Anthropic, AWS Bedrock)
- **Purple Team intel reports** — 4-card structured intelligence output per row (Threat, Detection, Remediation, Context) integrated directly into Merlino AI Review Reports
- **Version alignment with Merlino 0.3.0** — both platforms share the same version number from this release onward
- **Improved diagnostics** — verbose console logging for headless and service environments
- **Auto-update banner** — the Morgana UI now notifies you when a newer version is available

---

## Before you upgrade

1. **Your data is safe** — the database (`C:\ProgramData\Morgana\db\morgana.db`), API key (`C:\ProgramData\Morgana\data\master.key`), and TLS certificate are **never touched by the installer**. They survive upgrades and reinstalls.
2. **No reconfiguration needed in Merlino** — URL and API key remain the same.
3. No manual backup is required, but you can optionally copy `C:\ProgramData\Morgana\` before proceeding.

---

## Upgrade steps (Windows)

### Standard upgrade — run the installer

This is the recommended method for all desktop and server installations.

1. Download **`Morgana-Server-Setup.exe`** (v0.3.0) from this folder or from [GitHub Releases](https://github.com/x3m-ai/Morgana/releases/latest)
2. Right-click the file and choose **Run as Administrator**
3. The installer will automatically:
   - Stop the existing Morgana Windows service
   - Replace the server binary (`morgana-server.exe`)
   - Replace the agent binary (`morgana-agent.exe`)
   - Restart the service
4. Open your browser and confirm the version:

```
https://localhost:8888/ui/
```

The version number is shown in the top-right corner of the web UI.

---

### Silent upgrade (unattended / scripted)

```powershell
Start-Process -FilePath ".\Morgana-Server-Setup.exe" `
    -ArgumentList "/VERYSILENT", "/NORESTART", "/LOG=C:\morgana-upgrade.log" `
    -Verb RunAs -Wait
```

To verify the upgrade completed:

```powershell
(Invoke-WebRequest -Uri "https://localhost:8888/api/v2/version" -SkipCertificateCheck).Content
```

Expected response: `{"version":"0.3.0", ...}`

---

## After the upgrade

### Re-enable AI Review (if using the AI engine)

The AI engine `ai_review_enabled` flag resets to `true` by default in v0.3.0.  
No manual re-enable step is needed after a clean installer upgrade.

If you started the server directly from source (dev mode), re-enable manually via the **Admin** panel in the web UI → **AI Configuration**.

### Verify agent connectivity

Existing agents continue to work without reinstallation. After the server upgrades, verify agents are still checking in:

1. Open `https://localhost:8888/ui/`
2. Go to **Agents** — all previously registered agents should show as active within one beacon interval (default 30 seconds)

### Update agents (optional)

v0.3.0 ships an updated agent binary. Existing agents will continue to function.  
If you want to upgrade agents to the latest binary:

1. In the Morgana web UI, go to **Agents**
2. Click **Deploy Agent** to get an updated one-liner for the target machine
3. Run the one-liner as Administrator on the target — it will replace the installed binary in-place

---

## Clean reinstall (uninstall + reinstall from scratch)

Use this procedure when you want a completely fresh installation — empty database, new API key, new TLS certificate. Useful when upgrading across major schema changes or when troubleshooting a broken installation.

> **Warning:** this deletes all data — scripts, agents, tests, chains, campaigns, API key. There is no undo.

### Step 1 — Stop and uninstall the service

Run as Administrator:

```powershell
# Stop the service
Stop-Service Morgana -Force -ErrorAction SilentlyContinue

# Uninstall via the standard uninstaller
Start-Process -FilePath "C:\Program Files\Morgana Server\unins000.exe" `
    -ArgumentList "/VERYSILENT" -Verb RunAs -Wait
```

If the uninstaller is not found (e.g. previous install was damaged):

```powershell
sc.exe stop Morgana
sc.exe delete Morgana
```

### Step 2 — Delete all runtime data

```powershell
# Remove the installation folder
Remove-Item "C:\Program Files\Morgana Server" -Recurse -Force -ErrorAction SilentlyContinue

# Remove ALL persistent data (database, key, certs, logs, atomics cache)
Remove-Item "C:\ProgramData\Morgana" -Recurse -Force -ErrorAction SilentlyContinue
```

### Step 3 — Verify nothing remains

```powershell
Get-Service Morgana -ErrorAction SilentlyContinue
Test-Path "C:\Program Files\Morgana Server"
Test-Path "C:\ProgramData\Morgana"
```

All three should return nothing / `False`.

### Step 4 — Install v0.3.0

```powershell
Start-Process -FilePath ".\Morgana-Server-Setup.exe" `
    -ArgumentList "/VERYSILENT", "/NORESTART", "/LOG=C:\morgana-install.log" `
    -Verb RunAs -Wait
```

The installer creates a fresh database, generates a new TLS certificate and a new API key.

### Step 5 — Get the new API key

1. Open `https://localhost:8888/ui/`
2. Go to **Admin** → **Generate API Key**
3. Copy the key and update it in **Merlino Settings** (Caldera/Morgana section)

### Step 6 — Reload Atomic Red Team scripts

1. Go to **Scripts** in the left sidebar
2. Click **Refresh Canary Scripts**
3. Wait ~30 seconds

---

## Rollback

If you need to roll back to a previous version:

1. Download the previous `Morgana-Server-Setup.exe` from the [Camelot release history](https://github.com/x3m-ai/Camelot/commits/main/morgana/Install) or [GitHub Releases](https://github.com/x3m-ai/Morgana/releases)
2. Run it as Administrator — the older installer will replace the current binary and restart the service
3. Your data is preserved

---

## Troubleshooting upgrade issues

| Problem | Fix |
|---------|-----|
| Service fails to start after upgrade | Check `C:\ProgramData\Morgana\logs\server.log` for startup errors |
| Web UI shows old version number | Hard-refresh browser: `Ctrl+Shift+R` |
| "Access Denied" running the installer | Ensure you right-clicked and chose **Run as Administrator** |
| Port 8888 in use after upgrade | Run `netstat -ano \| findstr :8888` to identify the conflicting process |
| AI Review not working after upgrade | Go to Admin → AI Configuration in the web UI and verify the AI provider settings |

---

## Links

- **Full installation guide:** [README.md](./README.md)
- **Latest release:** https://github.com/x3m-ai/Morgana/releases/latest
- **Community support:** https://github.com/x3m-ai/Camelot/issues
- **Merlino (Excel Add-in):** https://merlino.x3m.ai
