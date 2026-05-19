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

---

## Step A: Add the DNS entry on the Windows (Merlino) machine

MISP redirects to `https://misp.merlino.local:8443` after login. You must tell Windows how to resolve that name.

Open **Notepad as Administrator**, then open `C:\Windows\System32\drivers\etc\hosts` and add this line at the bottom (replace with your server IP):

```
192.168.1.50    misp.merlino.local
```

Or via PowerShell (Administrator):

```powershell
Add-Content -Path "C:\Windows\System32\drivers\etc\hosts" -Value "192.168.1.50`tmisp.merlino.local"
ipconfig /flushdns
```

---

## Step B: Install the CA certificate on the Windows (Merlino) machine

The MISP server uses a self-signed certificate issued by the **Merlino Root CA**. You must install this CA certificate on the Windows machine so that Excel (WebView2), Chrome, and Edge trust it without warnings.

> This step is **required** — without it the Merlino Settings taskpane will get `ERR_CERT_AUTHORITY_INVALID` and the Test Connection will fail.

### Option 1 — via browser (manual)

1. Open `http://<SERVER_IP>/merlino-ca.crt` in Chrome or Edge (use HTTP, not HTTPS).
2. The browser will download `merlino-ca.crt`.
3. Double-click the downloaded file.
4. Click **Install Certificate**.
5. Select **Local Machine** → click **Next**.
6. Select **Place all certificates in the following store** → click **Browse**.
7. Choose **Trusted Root Certification Authorities** → **OK** → **Next** → **Finish**.
8. Confirm the security warning if prompted.

### Option 2 — via PowerShell (Administrator, one-liner)

```powershell
# Remove any old Merlino certs first
Get-ChildItem Cert:\LocalMachine\Root |
  Where-Object { $_.Subject -like "*Merlino*" -or $_.Subject -like "*misp.merlino*" } |
  ForEach-Object { certutil -delstore Root $_.Thumbprint }

# Download and install the new CA cert
(New-Object System.Net.WebClient).DownloadFile("http://<SERVER_IP>/merlino-ca.crt", "$env:TEMP\merlino-ca.crt")
certutil -addstore Root "$env:TEMP\merlino-ca.crt"
```

After installing the certificate, **close and reopen Excel** so WebView2 picks up the new trust.

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
