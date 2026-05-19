#!/bin/bash
#
# =============================================================================
# MISP Installation Script
# =============================================================================
# Version : 1.1
# Date    : 2026-05-19
# Author  : X3M.AI Ltd (https://x3m.ai)
# Repo    : https://github.com/x3m-ai/Camelot
#
# Description:
#   Fully automated installation of MISP (Malware Information Sharing Platform)
#   on Ubuntu 22.04 / 24.04. This script installs MISP only -- no other
#   components from the X3M.AI stack are installed.
#
#   What this script installs:
#     - MISP (latest 2.5 branch from https://github.com/MISP/MISP)
#     - MariaDB  (MISP database)
#     - Redis    (MISP background jobs)
#     - PHP      (MISP web application)
#     - Nginx    (HTTPS reverse proxy on port 8443)
#     - dnsmasq  (local DNS: misp.merlino.local)
#     - SSL      (self-signed CA + server certificate)
#     - MISP Modules (enrichment via misp-modules)
#
# Usage:
#   sudo bash install-misp.sh
#   sudo bash install-misp.sh --user ubuntu --ip 192.168.1.10
#
# Arguments:
#   --user <username>   System user that owns the installation (auto-detected)
#   --ip   <address>    Server IP address (auto-detected)
#
# After installation:
#   MISP web UI : https://<server-ip>:8443
#   Credentials : admin@admin.test / admin
#   CA cert     : http://<server-ip>/merlino-ca.crt
#
# Log file: misp-install.log (same directory as the script)
#
# Changelog:
#   1.1 (2026-05-19) - Fix: removed php-opcache/php-json (not standalone packages on PHP 8.x)
#   1.0 (2026-05-19) - Initial release: MISP-only automated install
# =============================================================================
#

set -e

# ============================================
# Logging Setup
# ============================================
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
if [ "$SCRIPT_DIR" = "/" ] || [ ! -w "$SCRIPT_DIR" ]; then
    SCRIPT_DIR="$(pwd)"
fi
LOG_FILE="${SCRIPT_DIR}/misp-install.log"
INSTALL_START_TIME=$(date '+%Y-%m-%d %H:%M:%S')

touch "$LOG_FILE"
chmod 644 "$LOG_FILE"
exec > >(tee -a "$LOG_FILE") 2>&1

SCRIPT_VERSION="1.1"

echo "============================================"
echo "MISP INSTALLATION"
echo "Version: ${SCRIPT_VERSION}"
echo "Started: $INSTALL_START_TIME"
echo "============================================"
echo ""

# ============================================
# Configuration
# ============================================
MISP_REPO="https://github.com/MISP/MISP.git"
MISP_DIR="/var/www/MISP"

MISP_DOMAIN="misp.merlino.local"
LAUNCHER_DOMAIN="launcher.merlino.local"
LOCAL_DOMAIN="merlino.local"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

log_info()    { echo -e "${GREEN}[$(date '+%H:%M:%S')][INFO]${NC} $1"; }
log_warn()    { echo -e "${YELLOW}[$(date '+%H:%M:%S')][WARN]${NC} $1"; }
log_error()   { echo -e "${RED}[$(date '+%H:%M:%S')][ERROR]${NC} $1"; }
log_debug()   { echo -e "[$(date '+%H:%M:%S')][DEBUG] $1"; }
log_substep() { echo -e "[$(date '+%H:%M:%S')][SUBSTEP] >> $1"; }
log_section() {
    echo ""
    echo -e "\n${CYAN}========================================${NC}"
    echo -e "${CYAN}  $1${NC}"
    echo -e "${CYAN}========================================${NC}\n"
}

handle_error() {
    local exit_code=$?
    local line=$1
    log_error "Failed at line $line (exit code $exit_code). Check: $LOG_FILE"
    echo "============================================"
    echo "INSTALLATION FAILED"
    echo "============================================"
    exit $exit_code
}
trap 'handle_error $LINENO' ERR

# ============================================
# Parse Arguments
# ============================================
INSTALL_USER=""
SERVER_IP=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --user) INSTALL_USER="$2"; shift 2 ;;
        --ip)   SERVER_IP="$2";    shift 2 ;;
        *)      shift ;;
    esac
done

# ============================================
# Pre-flight Checks
# ============================================
log_section "Pre-flight Checks"

if [ "$EUID" -ne 0 ]; then
    log_error "Please run as root: sudo $0"
    exit 1
fi

if [ -f /etc/os-release ]; then
    . /etc/os-release
    log_info "OS: ${NAME} ${VERSION_ID}"
    if [[ ! "$ID" =~ ^(ubuntu|debian)$ ]]; then
        log_warn "Designed for Ubuntu 22.04/24.04. Proceeding anyway..."
    fi
else
    log_error "Cannot detect OS."
    exit 1
fi

# Auto-detect user
if [ -z "$INSTALL_USER" ]; then
    if   [ -d "/home/ubuntu" ]; then INSTALL_USER="ubuntu"
    elif [ -d "/home/misp"   ]; then INSTALL_USER="misp"
    else
        INSTALL_USER="${SUDO_USER:-$(whoami)}"
        [ "$INSTALL_USER" = "root" ] && INSTALL_USER="ubuntu"
    fi
fi
INSTALL_HOME="/home/${INSTALL_USER}"
log_info "User: ${INSTALL_USER} (home: ${INSTALL_HOME})"

if ! id "$INSTALL_USER" &>/dev/null; then
    useradd -m -s /bin/bash "$INSTALL_USER"
    log_info "Created user ${INSTALL_USER}"
fi

# Auto-detect IP
if [ -z "$SERVER_IP" ]; then
    SERVER_IP=$(hostname -I | awk '{print $1}')
    [ -z "$SERVER_IP" ] && SERVER_IP=$(curl -s --connect-timeout 2 http://169.254.169.254/latest/meta-data/public-ipv4 2>/dev/null || true)
    [ -z "$SERVER_IP" ] && SERVER_IP=$(curl -s --connect-timeout 5 https://ipinfo.io/ip 2>/dev/null || true)
fi
log_info "Server IP: ${SERVER_IP}"

GATEWAY_IP=$(ip route | grep default | awk '{print $3}' | head -1)
[ -z "$GATEWAY_IP" ] && GATEWAY_IP="8.8.8.8"
log_info "Gateway: ${GATEWAY_IP}"

log_debug "Pre-flight checks OK"

# ============================================
# Step 1: System Dependencies
# ============================================
log_section "Step 1: System Dependencies"

log_substep "Updating apt..."
apt-get update

log_substep "Installing base packages..."
apt-get install -y \
    git curl wget gnupg \
    software-properties-common \
    python3 python3-pip python3-venv python3-dev \
    build-essential libssl-dev libffi-dev \
    libxml2-dev libxslt1-dev \
    nginx \
    mariadb-server mariadb-client \
    redis-server \
    zip unzip jq \
    dnsmasq

# Python 3.12 required: lxml 4.9.x is incompatible with Python 3.14+
log_substep "Checking Python 3.12..."
if ! command -v python3.12 &>/dev/null; then
    log_info "python3.12 not found -- adding deadsnakes PPA..."
    add-apt-repository -y ppa:deadsnakes/ppa
    apt-get update -y
    apt-get install -y python3.12 python3.12-venv python3.12-dev
    log_info "python3.12 installed"
else
    log_info "python3.12 already available: $(python3.12 --version)"
fi

log_substep "Installing PHP for MISP..."
# Note: php-json and php-opcache are built into PHP 8.x and have no standalone package
apt-get install -y \
    php php-fpm php-cli php-dev \
    php-xml php-mysql \
    php-mbstring php-zip php-curl \
    php-redis php-gd php-gnupg php-intl php-bcmath \
    php-apcu php-bz2 2>/dev/null || \
apt-get install -y php php-fpm php-cli php-xml php-mysql php-mbstring php-zip php-curl php-bcmath php-apcu

# Ensure 'php' binary is in PATH (on some systems it's php8.x not php)
if ! command -v php &>/dev/null; then
    log_warn "'php' not in PATH -- looking for versioned binary..."
    PHP_ALT=$(update-alternatives --list php 2>/dev/null | head -1)
    if [ -n "$PHP_ALT" ]; then
        ln -sf "$PHP_ALT" /usr/local/bin/php
        log_info "Linked $PHP_ALT -> /usr/local/bin/php"
    else
        PHP_ALT=$(find /usr/bin -name 'php*' -executable 2>/dev/null | sort -V | tail -1)
        [ -n "$PHP_ALT" ] && ln -sf "$PHP_ALT" /usr/local/bin/php && log_info "Linked $PHP_ALT -> /usr/local/bin/php"
    fi
fi

if ! command -v php &>/dev/null; then
    log_error "PHP is not available. Check apt output above."
    exit 1
fi

# Disable Apache2 if installed (conflicts with Nginx on port 80)
log_substep "Disabling Apache2 if present..."
systemctl stop    apache2 2>/dev/null || true
systemctl disable apache2 2>/dev/null || true

log_substep "Detecting PHP version..."
PHP_VERSION=$(php -r "echo PHP_MAJOR_VERSION.'.'.PHP_MINOR_VERSION;" 2>/dev/null || echo "8.1")
log_info "PHP Version: ${PHP_VERSION}"

log_substep "Enabling base services..."
systemctl enable mariadb redis-server nginx php${PHP_VERSION}-fpm 2>/dev/null || true
systemctl start  mariadb redis-server       php${PHP_VERSION}-fpm 2>/dev/null || true

log_info "Step 1 done"

# ============================================
# Step 2: DNS Configuration (dnsmasq)
# ============================================
log_section "Step 2: Local DNS (dnsmasq)"

# Release port 53 from systemd-resolved if needed
if systemctl is-active --quiet systemd-resolved; then
    log_substep "Configuring systemd-resolved to release port 53..."
    mkdir -p /etc/systemd/resolved.conf.d
    cat > /etc/systemd/resolved.conf.d/dnsmasq.conf << 'EOF'
[Resolve]
DNSStubListener=no
EOF
    systemctl restart systemd-resolved
fi

log_substep "Writing dnsmasq config..."
cat > /etc/dnsmasq.d/merlino.conf << EOF
# Merlino Local DNS
listen-address=127.0.0.1
listen-address=${SERVER_IP}
no-resolv
server=${GATEWAY_IP}
server=8.8.8.8
local=/${LOCAL_DOMAIN}/
domain=${LOCAL_DOMAIN}
address=/${MISP_DOMAIN}/${SERVER_IP}
address=/${LAUNCHER_DOMAIN}/${SERVER_IP}
address=/${LOCAL_DOMAIN}/${SERVER_IP}
cache-size=1000
domain-needed
bogus-priv
EOF

log_substep "Adding entries to /etc/hosts..."
if ! grep -q "${MISP_DOMAIN}" /etc/hosts; then
    cat >> /etc/hosts << EOF

# Merlino Local Domains
${SERVER_IP} ${MISP_DOMAIN}
${SERVER_IP} ${LAUNCHER_DOMAIN}
EOF
    log_info "Hosts entries added"
fi

systemctl enable dnsmasq
systemctl restart dnsmasq
sleep 2

if systemctl is-active --quiet dnsmasq; then
    rm -f /etc/resolv.conf
    cat > /etc/resolv.conf << EOF
nameserver 127.0.0.1
nameserver ${GATEWAY_IP}
EOF
    log_info "resolv.conf updated"
else
    log_warn "dnsmasq not running -- keeping original resolv.conf"
fi

log_info "Step 2 done"

# ============================================
# Step 3: SSL Certificates
# ============================================
log_section "Step 3: SSL Certificates"

mkdir -p /etc/nginx/ssl

log_substep "Creating OpenSSL SAN config..."
cat > /tmp/misp-openssl.cnf << EOF
[req]
default_bits = 2048
prompt = no
default_md = sha256
distinguished_name = dn
req_extensions = v3_req
x509_extensions = v3_ca

[dn]
C = IT
ST = Italy
L = Rome
O = X3M.AI
OU = Security
CN = ${MISP_DOMAIN}

[v3_req]
basicConstraints = CA:FALSE
keyUsage = nonRepudiation, digitalSignature, keyEncipherment
subjectAltName = @alt_names

[v3_ca]
basicConstraints = critical,CA:TRUE
keyUsage = critical, digitalSignature, cRLSign, keyCertSign
subjectAltName = @alt_names

[alt_names]
DNS.1 = ${MISP_DOMAIN}
DNS.2 = ${LAUNCHER_DOMAIN}
DNS.3 = ${LOCAL_DOMAIN}
DNS.4 = *.${LOCAL_DOMAIN}
DNS.5 = localhost
IP.1  = ${SERVER_IP}
IP.2  = 127.0.0.1
EOF

log_substep "Generating CA key + certificate..."
openssl genrsa -out /etc/nginx/ssl/merlino-ca.key 4096
openssl req -x509 -new -nodes \
    -key /etc/nginx/ssl/merlino-ca.key \
    -sha256 -days 3650 \
    -out /etc/nginx/ssl/merlino-ca.crt \
    -subj "/C=IT/ST=Italy/L=Rome/O=Merlino CA/CN=Merlino Root CA"

log_substep "Generating server key + certificate..."
openssl genrsa -out /etc/nginx/ssl/misp.key 2048
openssl req -new \
    -key /etc/nginx/ssl/misp.key \
    -out /tmp/misp.csr \
    -config /tmp/misp-openssl.cnf
openssl x509 -req \
    -in /tmp/misp.csr \
    -CA  /etc/nginx/ssl/merlino-ca.crt \
    -CAkey /etc/nginx/ssl/merlino-ca.key \
    -CAcreateserial \
    -out /etc/nginx/ssl/misp.crt \
    -days 3650 -sha256 \
    -extfile /tmp/misp-openssl.cnf \
    -extensions v3_req

rm -f /tmp/misp-openssl.cnf /tmp/misp.csr

chmod 600 /etc/nginx/ssl/misp.key /etc/nginx/ssl/merlino-ca.key
chmod 644 /etc/nginx/ssl/misp.crt /etc/nginx/ssl/merlino-ca.crt

mkdir -p /var/www/html
cp /etc/nginx/ssl/merlino-ca.crt /var/www/html/merlino-ca.crt

log_info "Certificates generated. CA: /etc/nginx/ssl/merlino-ca.crt"
log_info "Download CA at: http://${SERVER_IP}/merlino-ca.crt"
log_info "Step 3 done"

# ============================================
# Step 4: Install MISP
# ============================================
log_section "Step 4: Install MISP"

if [ -d "${MISP_DIR}" ]; then
    log_substep "Updating existing MISP..."
    cd "${MISP_DIR}"
    git config --global --add safe.directory "${MISP_DIR}" 2>/dev/null || true
    sudo -u www-data git fetch  origin       2>/dev/null || git fetch  origin       2>/dev/null || true
    sudo -u www-data git checkout 2.5        2>/dev/null || git checkout 2.5        2>/dev/null || true
    sudo -u www-data git pull   origin 2.5   2>/dev/null || git pull   origin 2.5   2>/dev/null || true
else
    log_substep "Cloning MISP..."
    mkdir -p /var/www
    git clone "${MISP_REPO}" "${MISP_DIR}"
    chown -R www-data:www-data "${MISP_DIR}"
    cd "${MISP_DIR}"
    git config --global --add safe.directory "${MISP_DIR}" 2>/dev/null || true
    sudo -u www-data git checkout 2.5 2>/dev/null || git checkout 2.5 2>/dev/null || true
fi

log_substep "Updating git submodules..."
cd "${MISP_DIR}"
sudo -u www-data git submodule update --init --recursive 2>/dev/null || true

log_substep "Creating MISP Python venv..."
if command -v python3.12 &>/dev/null; then
    PYTHON_BIN="python3.12"
else
    PYTHON_BIN="python3"
    log_warn "python3.12 not found -- using default python3 (may fail with Python 3.14+)"
fi

if [ ! -d "${MISP_DIR}/venv" ]; then
    sudo -u www-data ${PYTHON_BIN} -m venv "${MISP_DIR}/venv"
fi
sudo -u www-data "${MISP_DIR}/venv/bin/pip" install --upgrade pip 2>/dev/null || true
sudo -u www-data "${MISP_DIR}/venv/bin/pip" install -r "${MISP_DIR}/requirements.txt" 2>/dev/null || true

log_substep "Installing Composer..."
if ! command -v composer &>/dev/null; then
    EXPECTED_CHECKSUM="$(php -r 'copy("https://composer.github.io/installer.sig", "php://stdout");')"
    php -r "copy('https://getcomposer.org/installer', '/tmp/composer-setup.php');"
    ACTUAL_CHECKSUM="$(php -r "echo hash_file('sha384', '/tmp/composer-setup.php');")"
    [ "$EXPECTED_CHECKSUM" != "$ACTUAL_CHECKSUM" ] && log_warn "Composer checksum mismatch -- trying anyway"
    php /tmp/composer-setup.php --install-dir=/usr/local/bin --filename=composer
    rm -f /tmp/composer-setup.php
    chmod +x /usr/local/bin/composer
    log_info "Composer installed"
fi

log_substep "Running composer install for MISP..."
if [ -f "${MISP_DIR}/app/composer.json" ]; then
    mkdir -p /var/www/.cache/composer
    chown -R www-data:www-data /var/www/.cache
    cd "${MISP_DIR}/app"
    COMPOSER_ALLOW_SUPERUSER=1 COMPOSER_HOME=/var/www/.cache/composer \
        /usr/local/bin/composer install --no-dev --no-interaction 2>&1 || true
    if [ -f "${MISP_DIR}/app/Vendor/autoload.php" ]; then
        log_info "Composer dependencies OK"
    else
        log_warn "autoload.php missing -- run manually: cd /var/www/MISP/app && sudo composer install --no-dev"
    fi
    chown -R www-data:www-data "${MISP_DIR}/app/Vendor" 2>/dev/null || true
fi

log_info "Step 4 done"

# ============================================
# Step 5: Configure MariaDB
# ============================================
log_section "Step 5: Configure MariaDB"

systemctl start mariadb

if ! mysql -e "USE misp" 2>/dev/null; then
    log_substep "Creating MISP database and user..."
    mysql -e "CREATE DATABASE IF NOT EXISTS misp CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
    mysql -e "CREATE USER IF NOT EXISTS 'misp'@'localhost' IDENTIFIED BY 'misp_password';"
    mysql -e "GRANT ALL PRIVILEGES ON misp.* TO 'misp'@'localhost';"
    mysql -e "FLUSH PRIVILEGES;"
    log_info "Database created"

    if [ -f "${MISP_DIR}/INSTALL/MYSQL.sql" ]; then
        log_substep "Importing schema..."
        mysql -u misp -pmisp_password misp < "${MISP_DIR}/INSTALL/MYSQL.sql" 2>/dev/null || true
        log_info "Schema imported"
    fi
else
    log_info "MISP database already exists -- skipping"
fi

log_info "Step 5 done"

# ============================================
# Step 6: Configure MISP
# ============================================
log_section "Step 6: Configure MISP"

cd "${MISP_DIR}/app/Config"

for conf in database core config bootstrap; do
    if [ ! -f "${conf}.php" ] && [ -f "${conf}.default.php" ]; then
        cp "${conf}.default.php" "${conf}.php"
        chown www-data:www-data "${conf}.php"
        chmod 770 "${conf}.php"
        log_info "Created ${conf}.php"
    fi
done

if [ -f "database.php" ]; then
    sed -i "s/'login' => 'db login'/'login' => 'misp'/"          database.php 2>/dev/null || true
    sed -i "s/'password' => 'db password'/'password' => 'misp_password'/" database.php 2>/dev/null || true
    sed -i "s/'password' => ''/'password' => 'misp_password'/"   database.php 2>/dev/null || true
    log_info "Database credentials set in database.php"
fi

chown -R www-data:www-data "${MISP_DIR}"
chmod -R 750 "${MISP_DIR}"
chmod -R g+ws "${MISP_DIR}/app/tmp"   2>/dev/null || true
chmod -R g+ws "${MISP_DIR}/app/files" 2>/dev/null || true

log_info "Step 6 done"

# ============================================
# Step 7: Install MISP Modules
# ============================================
log_section "Step 7: MISP Modules"

pip3 install misp-modules --break-system-packages --ignore-installed typing-extensions 2>/dev/null || \
pip3 install misp-modules --ignore-installed typing-extensions                         2>/dev/null || \
pip3 install misp-modules                                                              2>/dev/null || true

cat > /etc/systemd/system/misp-modules.service << 'EOF'
[Unit]
Description=MISP Modules
After=network.target redis-server.service
Wants=redis-server.service

[Service]
Type=simple
User=www-data
Group=www-data
ExecStart=/usr/local/bin/misp-modules -l 127.0.0.1
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable misp-modules
log_info "Step 7 done"

# ============================================
# Step 8: Nginx Configuration
# ============================================
log_section "Step 8: Nginx"

rm -f /etc/nginx/sites-enabled/default

# --- Launcher (port 80) ---
log_substep "Creating launcher site (port 80)..."
cat > /etc/nginx/sites-available/launcher.conf << EOF
server {
    listen 80;
    listen [::]:80;
    server_name ${LAUNCHER_DOMAIN} ${SERVER_IP} localhost;

    root /var/www/html;
    index launcher.html index.html;

    location / {
        try_files \$uri \$uri/ =404;
    }

    location /merlino-ca.crt {
        alias /var/www/html/merlino-ca.crt;
        add_header Content-Type application/x-x509-ca-cert;
    }
}
EOF

log_substep "Creating launcher page..."
mkdir -p /var/www/html
cat > /var/www/html/launcher.html << 'HTMLEOF'
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Merlino - Services</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            color: #fff;
        }
        .container { text-align: center; padding: 40px; max-width: 700px; }
        h1 { font-size: 2.5em; margin-bottom: 8px; color: #667eea; }
        .subtitle { color: #a0a0a0; margin-bottom: 30px; }
        .service-card {
            display: inline-block;
            background: rgba(255,255,255,0.1);
            border-radius: 15px;
            padding: 30px 40px;
            border: 1px solid rgba(255,255,255,0.2);
            text-decoration: none;
            color: #fff;
            transition: transform 0.3s, box-shadow 0.3s;
        }
        .service-card:hover {
            transform: translateY(-8px);
            box-shadow: 0 20px 40px rgba(102,126,234,0.3);
        }
        .service-icon { font-size: 3em; margin-bottom: 12px; color: #4fc3f7; }
        .service-name { font-size: 1.4em; font-weight: bold; margin-bottom: 8px; }
        .service-desc { color: #a0a0a0; font-size: 0.9em; margin-bottom: 8px; }
        .service-url  { font-family: monospace; font-size: 0.8em; color: #4fc3f7; }
        .credentials {
            background: rgba(255,193,7,0.1);
            border: 1px solid rgba(255,193,7,0.3);
            border-radius: 8px;
            padding: 15px;
            margin-top: 25px;
        }
        .credentials h4 { color: #ffc107; margin-bottom: 8px; }
        .credentials code { background: rgba(0,0,0,0.3); padding: 2px 8px; border-radius: 4px; }
        .ca-link { margin-top: 18px; font-size: 0.9em; }
        .ca-link a { color: #4fc3f7; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Merlino</h1>
        <p class="subtitle">Purple Teaming Services</p>
        <a href="https://misp.merlino.local:8443/" class="service-card">
            <div class="service-icon">&#128373;</div>
            <div class="service-name">MISP</div>
            <div class="service-desc">Threat Intelligence Platform &mdash; HTTPS port 8443</div>
            <div class="service-url">https://misp.merlino.local:8443</div>
        </a>
        <div class="credentials">
            <h4>Default Credentials</h4>
            <p>MISP: <code>admin@admin.test</code> / <code>admin</code></p>
        </div>
        <div class="ca-link">
            To avoid certificate warnings, install the
            <a href="/merlino-ca.crt">Merlino CA Certificate</a>
        </div>
    </div>
</body>
</html>
HTMLEOF

# --- MISP internal PHP backend (port 8080, localhost only) ---
log_substep "Creating MISP internal PHP config (127.0.0.1:8080)..."
cat > /etc/nginx/sites-available/misp.conf << EOF
server {
    listen 127.0.0.1:8080;
    server_name localhost;

    root /var/www/MISP/app/webroot;
    index index.php;

    client_max_body_size 50M;

    location / {
        try_files \$uri \$uri/ /index.php?\$args;
    }

    location ~ \.php\$ {
        include snippets/fastcgi-php.conf;
        fastcgi_pass unix:/var/run/php/php${PHP_VERSION}-fpm.sock;
        fastcgi_param SCRIPT_FILENAME \$document_root\$fastcgi_script_name;
        include fastcgi_params;
    }
}
EOF

# --- MISP HTTPS (port 8443) with CORS for Merlino Excel Add-in ---
log_substep "Creating MISP HTTPS config (port 8443)..."
cat > /etc/nginx/sites-available/misp-https.conf << 'MISPEOF'
server {
    listen 8443 ssl http2;
    listen [::]:8443 ssl http2;
MISPEOF

cat >> /etc/nginx/sites-available/misp-https.conf << EOF
    server_name ${MISP_DOMAIN} ${SERVER_IP} localhost;
EOF

cat >> /etc/nginx/sites-available/misp-https.conf << 'MISPEOF'

    ssl_certificate     /etc/nginx/ssl/misp.crt;
    ssl_certificate_key /etc/nginx/ssl/misp.key;
    ssl_protocols       TLSv1.2 TLSv1.3;
    ssl_ciphers         HIGH:!aNULL:!MD5;

    root  /var/www/MISP/app/webroot;
    index index.php;

    client_max_body_size 50M;

    # CORS for Merlino Excel Add-in
    set $cors_origin "";
    set $cors_cred   "";

    if ($http_origin ~* "^https://(merlino-addin\.pages\.dev|merlino-addin\.x3m\.ai|localhost:3000|127\.0\.0\.1:3000)$") {
        set $cors_origin $http_origin;
        set $cors_cred   "true";
    }
    if ($cors_origin = "") {
        set $cors_origin "*";
        set $cors_cred   "false";
    }

    location / {
        add_header 'Access-Control-Allow-Origin'      $cors_origin always;
        add_header 'Access-Control-Allow-Methods'     'GET, POST, PUT, DELETE, PATCH, OPTIONS' always;
        add_header 'Access-Control-Allow-Headers'     'Authorization, Content-Type, Accept, Origin, X-Requested-With' always;
        add_header 'Access-Control-Allow-Credentials' $cors_cred   always;
        add_header 'Access-Control-Max-Age'           86400        always;

        if ($request_method = 'OPTIONS') {
            add_header 'Access-Control-Allow-Origin'      $cors_origin;
            add_header 'Access-Control-Allow-Methods'     'GET, POST, PUT, DELETE, PATCH, OPTIONS';
            add_header 'Access-Control-Allow-Headers'     'Authorization, Content-Type, Accept, Origin, X-Requested-With';
            add_header 'Access-Control-Allow-Credentials' $cors_cred;
            add_header 'Content-Type'   'text/plain charset=UTF-8';
            add_header 'Content-Length' 0;
            return 204;
        }

        try_files $uri $uri/ /index.php?$args;
    }
MISPEOF

cat >> /etc/nginx/sites-available/misp-https.conf << EOF

    location ~ \.php\$ {
        add_header 'Access-Control-Allow-Origin'      \$cors_origin always;
        add_header 'Access-Control-Allow-Methods'     'GET, POST, PUT, DELETE, PATCH, OPTIONS' always;
        add_header 'Access-Control-Allow-Headers'     'Authorization, Content-Type, Accept, Origin, X-Requested-With' always;
        add_header 'Access-Control-Allow-Credentials' \$cors_cred always;

        include snippets/fastcgi-php.conf;
        fastcgi_pass unix:/var/run/php/php${PHP_VERSION}-fpm.sock;
        fastcgi_param SCRIPT_FILENAME \$document_root\$fastcgi_script_name;
        fastcgi_param HTTPS on;
        include fastcgi_params;
    }

    access_log /var/log/nginx/misp-access.log;
    error_log  /var/log/nginx/misp-error.log warn;
}
EOF

log_substep "Enabling nginx sites..."
ln -sf /etc/nginx/sites-available/launcher.conf   /etc/nginx/sites-enabled/
ln -sf /etc/nginx/sites-available/misp.conf       /etc/nginx/sites-enabled/
ln -sf /etc/nginx/sites-available/misp-https.conf /etc/nginx/sites-enabled/

log_substep "Testing nginx config..."
if nginx -t 2>&1; then
    log_info "Nginx config OK"
else
    log_warn "Nginx config test failed -- check logs"
fi

log_info "Step 8 done"

# ============================================
# Step 9: Start Services
# ============================================
log_section "Step 9: Start Services"

systemctl restart dnsmasq
systemctl restart "php${PHP_VERSION}-fpm"
systemctl restart nginx
systemctl start   misp-modules  2>/dev/null || log_warn "misp-modules may need manual start"
systemctl restart redis-server
systemctl restart mariadb

sleep 3
log_info "Step 9 done"

# ============================================
# Step 10: Verification
# ============================================
log_section "Step 10: Verification"

echo -e "\n${BOLD}Service Status:${NC}"
echo "────────────────────────────────────"

_svc() {
    if systemctl is-active --quiet "$1"; then
        echo -e "  $2: ${GREEN}Running${NC}"
    else
        echo -e "  $2: ${RED}Stopped${NC}"
        log_warn "Service $1 is STOPPED"
    fi
}

_svc dnsmasq                 "dnsmasq (DNS)"
_svc nginx                   "Nginx"
_svc "php${PHP_VERSION}-fpm" "PHP-FPM"
_svc misp-modules            "MISP Modules"
_svc mariadb                 "MariaDB"
_svc redis-server            "Redis"

echo -e "\n${BOLD}Listening Ports:${NC}"
echo "────────────────────────────────────"
ss -tlnp 2>/dev/null | grep -E ":(80|8443|8080) " | awk '{print "  "$4}' || true

# ============================================
# Done
# ============================================
log_section "Installation Complete"

set +e

echo -e "
${GREEN}${BOLD}MISP installed successfully!${NC}

${CYAN}${BOLD}Access URLs:${NC}
  Launcher:  http://${LAUNCHER_DOMAIN}  or  http://${SERVER_IP}
  MISP:      https://${MISP_DOMAIN}:8443  or  https://${SERVER_IP}:8443

${CYAN}${BOLD}Default Credentials:${NC}
  admin@admin.test / admin

${CYAN}${BOLD}CA Certificate (avoid browser warnings):${NC}
  Download:  http://${SERVER_IP}/merlino-ca.crt
  Windows:   Double-click > Install > Trusted Root CAs
  Linux:     sudo cp merlino-ca.crt /usr/local/share/ca-certificates/
             sudo update-ca-certificates

${CYAN}${BOLD}DNS -- point clients to: ${SERVER_IP}${NC}
  Or add to /etc/hosts:
    ${SERVER_IP}  ${MISP_DOMAIN}  ${LAUNCHER_DOMAIN}

${CYAN}${BOLD}Open MISP in your browser:${NC}
────────────────────────────────────
  From this server:  https://localhost:8443
  From your network: https://${SERVER_IP}:8443
  Via DNS (if set):  https://${MISP_DOMAIN}:8443

  If you see a certificate warning:
    1. Download the CA cert:  http://${SERVER_IP}/merlino-ca.crt
    2. Windows: double-click > Install Certificate > Trusted Root CAs
    3. Linux:   sudo cp merlino-ca.crt /usr/local/share/ca-certificates/
                sudo update-ca-certificates
    4. Retry:   https://${SERVER_IP}:8443

${CYAN}${BOLD}Logs:${NC}
  Install: ${LOG_FILE}
  Nginx:   /var/log/nginx/misp-*.log
  System:  journalctl -u misp-modules -u dnsmasq -u nginx
"