# MISP Installation for Merlino

This folder contains the automated installation script for **MISP** (Malware Information Sharing Platform) on Ubuntu, pre-configured to work with the **Merlino Excel Add-in**.

---

## What the script installs

- **MISP** — latest release, served on port **8443** via nginx
- **nginx** — reverse proxy with self-signed SSL certificate (auto-generated CA)
- **CORS headers** — pre-configured for Merlino Excel Add-in bidirectional integration
- **dnsmasq** — local DNS so `misp.merlino.local` resolves on the same machine
- Log file: `misp-install.log` in the same directory as the script

## Requirements

| | |
|---|---|
| OS | Ubuntu 22.04 or 24.04 (bare metal, VMware, AWS) |
| RAM | 8 GB minimum (16 GB recommended) |
| Disk | 60 GB minimum |
| Network | Bridged or routable from the Merlino client machine |

---

## Quick start

```bash
# 1. Update package lists
sudo apt update

# 2. Install curl if not already present
sudo apt install -y curl

# 3. Download the script from Camelot
curl -O https://raw.githubusercontent.com/x3m-ai/Camelot/main/misp/installation/install-misp.sh

# 4. Run the installation script
sudo bash install-misp.sh
```

The script auto-detects the machine IP and the Linux user. No arguments required in most cases.

Installation takes approximately **15–30 minutes** depending on internet speed.

---

## Optional arguments

| Argument | Description | Default |
|---|---|---|
| `--user <name>` | Linux user that will own the installation | Auto-detected (`ubuntu`, `morgana`, or `$SUDO_USER`) |
| `--ip <address>` | IP address of this machine | Auto-detected via `hostname -I` or AWS metadata |

Use `--ip` only if the machine has multiple network interfaces and you want to force a specific one (e.g. a public AWS IP).

```bash
sudo bash install-misp.sh --user ubuntu --ip 192.168.1.50
```

---

## After installation

At the end of the script you will see a summary like this:

```
  DNS Server:      192.168.1.50  (set this as DNS on client machines)
  MISP:            https://192.168.1.50:8443
  CA Certificate:  http://192.168.1.50/merlino-ca.crt
```

### Install the CA certificate on Windows (to avoid browser warnings)

1. Open `http://<SERVER_IP>/merlino-ca.crt` in your browser and download the file.
2. Double-click the `.crt` file → **Install Certificate** → **Local Machine** → **Trusted Root Certification Authorities**.

Or via PowerShell (Administrator):

```powershell
# Remove any old Merlino certificate first
Get-ChildItem Cert:\LocalMachine\Root |
  Where-Object { $_.Subject -like "*Merlino*" } |
  Remove-Item -Force

# Install the new certificate
certutil -addstore Root merlino-ca.crt
```

---

## Connect Merlino to MISP

1. In Excel, open the **Settings** taskpane.
2. Under **MISP**, enter:
   - **URL:** `https://<SERVER_IP>:8443`
   - **API Key:** generated from MISP → Administration → Auth Keys
3. Click **Test Connection** — it should turn green.

---

## Script version

`install-misp.sh` — v1.2 (2026-05-19)

Changelog:
- v1.2 — Fix: CA cert uses explicit v3_ca extensions (basicConstraints, keyUsage) for WebView2/Chrome compatibility
- v1.1 — Fix: removed php-opcache/php-json (built into PHP 8.x, not standalone packages)
- v1.0 — Initial release: MISP-only install (removed Morgana Arsenal legacy component)
