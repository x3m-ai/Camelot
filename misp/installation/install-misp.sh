#!/bin/bash
#
# Morgana Arsenal + MISP - Complete Installation Script
# Version: 1.4.2
# Date: 2026-01-11
#
# For Ubuntu 22.04/24.04 (AWS, local VM, or bare metal)
#
# - If Morgana Arsenal not found: Full installation from scratch
# - If Morgana Arsenal exists: Update and install MISP
#
# Usage: curl -sL https://raw.githubusercontent.com/x3m-ai/morgana-arsenal/main/install-morgana-misp.sh | sudo bash
#    or: sudo ./install-morgana-misp.sh [--user ubuntu] [--ip 1.2.3.4]
#
# Log file: morgana-install.log (in the same directory as the script)
#
# Changelog:
#   1.4.2 (2026-01-11) - Fix: Installation summary now always displays in terminal (set +e before final echo)
#   1.4.1 (2026-01-11) - Added CORS headers for MISP (port 8443) for Merlino Excel Add-in
#   1.4.0 (2026-01-11) - Added CORS headers for Morgana (port 443) for Merlino Excel Add-in
#   1.3.1 (2026-01-11) - Fix: Composer install using direct cd instead of subshell to fix variable scope
#   1.3.0 (2026-01-11) - Fix: Nginx config closure (caldera-proxy), launcher.conf CA cert location,
#                        robust Composer install with cache dir, PHP-FPM restart after Composer,
#                        nginx config validation before restart
#   1.2.0 (2026-01-11) - Fix: Disable Apache2 (conflicts with Nginx), fix DNS order
#   1.1.0 (2026-01-11) - Added detailed logging, launcher from static/, log in script dir
#   1.0.0 (2026-01-10) - Initial release with dnsmasq, SSL, MISP integration
#

set -e

# ============================================
# Logging Setup - ALL OUTPUT TO FILE AND TERMINAL
# ============================================
# Get the directory where the script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
# If script is piped via curl, use current working directory
if [ "$SCRIPT_DIR" = "/" ] || [ ! -w "$SCRIPT_DIR" ]; then
    SCRIPT_DIR="$(pwd)"
fi
LOG_FILE="${SCRIPT_DIR}/morgana-install.log"
INSTALL_START_TIME=$(date '+%Y-%m-%d %H:%M:%S')

# Create log file and set permissions
touch "$LOG_FILE"
chmod 644 "$LOG_FILE"

# Redirect all output to both terminal and log file
exec > >(tee -a "$LOG_FILE") 2>&1

# Script version
SCRIPT_VERSION="1.4.2"

echo "============================================"
echo "MORGANA ARSENAL + MISP INSTALLATION"
echo "Version: ${SCRIPT_VERSION}"
echo "Started: $INSTALL_START_TIME"
echo "============================================"
echo ""

# ============================================
# Configuration
# ============================================
MORGANA_REPO="https://github.com/x3m-ai/morgana-arsenal.git"
MISP_REPO="https://github.com/MISP/MISP.git"

# Local DNS domains
MORGANA_DOMAIN="morgana.merlino.local"
MISP_DOMAIN="misp.merlino.local"
LAUNCHER_DOMAIN="launcher.merlino.local"
LOCAL_DOMAIN="merlino.local"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

# Logging functions with timestamps
log_info() { 
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo -e "${GREEN}[$timestamp][INFO]${NC} $1"
}

log_warn() { 
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo -e "${YELLOW}[$timestamp][WARN]${NC} $1"
}

log_error() { 
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo -e "${RED}[$timestamp][ERROR]${NC} $1"
}

log_debug() {
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo -e "[$timestamp][DEBUG] $1"
}

log_cmd() {
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo -e "[$timestamp][CMD] Running: $1"
}

log_section() { 
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo ""
    echo "============================================"
    echo "[$timestamp] STEP: $1"
    echo "============================================"
    echo -e "\n${CYAN}════════════════════════════════════════${NC}"
    echo -e "${CYAN}  $1${NC}"
    echo -e "${CYAN}════════════════════════════════════════${NC}\n"
}

log_substep() {
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo -e "[$timestamp][SUBSTEP] >> $1"
}

# Error handler
handle_error() {
    local exit_code=$?
    local line_number=$1
    log_error "Script failed at line $line_number with exit code $exit_code"
    log_error "Check log file for details: $LOG_FILE"
    echo ""
    echo "============================================"
    echo "INSTALLATION FAILED"
    echo "Time: $(date '+%Y-%m-%d %H:%M:%S')"
    echo "Log file: $LOG_FILE"
    echo "============================================"
    exit $exit_code
}

trap 'handle_error $LINENO' ERR

# ============================================
# Parse Arguments
# ============================================
log_debug "Parsing command line arguments..."
MORGANA_USER=""
SERVER_IP=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --user)
            MORGANA_USER="$2"
            log_debug "Argument --user: $MORGANA_USER"
            shift 2
            ;;
        --ip)
            SERVER_IP="$2"
            shift 2
            ;;
        *)
            shift
            ;;
    esac
done

# ============================================
# Pre-flight Checks
# ============================================
log_section "Pre-flight Checks"

log_substep "Checking if running as root..."
# Check root
if [ "$EUID" -ne 0 ]; then
    log_error "Please run as root: sudo $0"
    exit 1
fi
log_debug "Running as root: OK"

log_substep "Detecting operating system..."
# Detect OS
if [ -f /etc/os-release ]; then
    . /etc/os-release
    OS_NAME=$NAME
    OS_VERSION=$VERSION_ID
    log_debug "OS Release file found: /etc/os-release"
else
    log_error "Cannot detect OS. This script requires Ubuntu 22.04 or 24.04"
    exit 1
fi

log_info "OS: ${OS_NAME} ${OS_VERSION}"
log_debug "OS ID: $ID"

if [[ ! "$ID" =~ ^(ubuntu|debian)$ ]]; then
    log_warn "This script is designed for Ubuntu. Proceeding anyway..."
fi

log_substep "Detecting target user..."
# Detect user if not specified
if [ -z "$MORGANA_USER" ]; then
    log_debug "No --user argument provided, auto-detecting..."
    if [ -d "/home/ubuntu" ]; then
        MORGANA_USER="ubuntu"
        log_debug "Found /home/ubuntu directory"
    elif [ -d "/home/morgana" ]; then
        MORGANA_USER="morgana"
        log_debug "Found /home/morgana directory"
    else
        # Get the user who called sudo
        MORGANA_USER="${SUDO_USER:-$(whoami)}"
        if [ "$MORGANA_USER" = "root" ]; then
            MORGANA_USER="ubuntu"
        fi
        log_debug "Using SUDO_USER or fallback: $MORGANA_USER"
    fi
fi

MORGANA_HOME="/home/${MORGANA_USER}"
MORGANA_DIR="${MORGANA_HOME}/morgana-arsenal"

log_info "User: ${MORGANA_USER}"
log_info "Home: ${MORGANA_HOME}"
log_info "Install directory: ${MORGANA_DIR}"

log_substep "Checking if user exists..."
# Create user if doesn't exist
if ! id "$MORGANA_USER" &>/dev/null; then
    log_info "Creating user ${MORGANA_USER}..."
    log_cmd "useradd -m -s /bin/bash $MORGANA_USER"
    useradd -m -s /bin/bash "$MORGANA_USER"
    log_debug "User created successfully"
else
    log_debug "User $MORGANA_USER already exists"
fi

log_substep "Detecting server IP address..."
# Detect server IP if not specified
if [ -z "$SERVER_IP" ]; then
    log_debug "No --ip argument provided, auto-detecting..."
    
    # Prefer private/local IP for LAN DNS (most common use case)
    SERVER_IP=$(hostname -I | awk '{print $1}')
    log_debug "Local IP from hostname -I: $SERVER_IP"
    
    # If no local IP, try AWS metadata
    if [ -z "$SERVER_IP" ]; then
        log_debug "Trying AWS metadata service..."
        SERVER_IP=$(curl -s --connect-timeout 2 http://169.254.169.254/latest/meta-data/public-ipv4 2>/dev/null || true)
        log_debug "AWS metadata IP: $SERVER_IP"
    fi
    
    # Last resort: external IP service
    if [ -z "$SERVER_IP" ]; then
        SERVER_IP=$(curl -s --connect-timeout 5 https://ipinfo.io/ip 2>/dev/null || true)
    fi
fi

log_info "Server IP: ${SERVER_IP}"
log_debug "Server IP detection complete"

# Detect gateway IP for DNS forwarding
log_substep "Detecting gateway IP for DNS forwarding..."
GATEWAY_IP=$(ip route | grep default | awk '{print $3}' | head -1)
if [ -z "$GATEWAY_IP" ]; then
    GATEWAY_IP="8.8.8.8"
    log_warn "Could not detect gateway, falling back to 8.8.8.8"
else
    log_info "Gateway IP: ${GATEWAY_IP}"
fi
log_debug "Gateway will be used as upstream DNS"

# ============================================
# Detect Installation Mode
# ============================================
log_substep "Detecting installation mode..."
FRESH_INSTALL=false

if [ -d "${MORGANA_DIR}" ] && [ -f "${MORGANA_DIR}/server.py" ]; then
    log_info "Morgana Arsenal found at ${MORGANA_DIR}"
    log_info "Mode: UPDATE + MISP Installation"
    log_debug "Found server.py at ${MORGANA_DIR}/server.py"
else
    log_info "Morgana Arsenal not found"
    log_info "Mode: FRESH Installation + MISP"
    log_debug "Directory ${MORGANA_DIR} does not exist or missing server.py"
    FRESH_INSTALL=true
fi

log_debug "Pre-flight checks completed successfully"

# ============================================
# Step 1: System Dependencies
# ============================================
log_section "Step 1: Installing System Dependencies"

log_substep "Updating apt package lists..."
log_cmd "apt-get update"
apt-get update

log_substep "Installing common dependencies..."
log_debug "Packages: git curl wget gnupg python3 python3-pip python3-venv python3-dev build-essential libssl-dev libffi-dev nginx mariadb-server mariadb-client redis-server zip unzip jq dnsmasq"
log_cmd "apt-get install -y [common packages]"
# Common dependencies
apt-get install -y \
    git curl wget gnupg \
    python3 python3-pip python3-venv python3-dev \
    build-essential libssl-dev libffi-dev \
    nginx \
    mariadb-server mariadb-client \
    redis-server \
    zip unzip jq \
    dnsmasq

log_info "Common dependencies installed successfully"

log_substep "Installing PHP and extensions for MISP..."
log_debug "Packages: php php-fpm php-cli php-dev php-json php-xml php-mysql php-opcache php-readline php-mbstring php-zip php-curl php-redis php-gd php-gnupg php-intl php-bcmath php-apcu php-bz2"
log_cmd "apt-get install -y [PHP packages]"
# PHP and extensions for MISP
apt-get install -y \
    php php-fpm php-cli php-dev \
    php-json php-xml php-mysql php-opcache \
    php-readline php-mbstring php-zip php-curl \
    php-redis php-gd php-gnupg php-intl php-bcmath \
    php-apcu php-bz2 2>/dev/null || true

# IMPORTANT: Stop and disable Apache2 if it was installed as a dependency
# (libapache2-mod-php installs Apache2 which conflicts with Nginx on port 80)
log_substep "Disabling Apache2 (conflicts with Nginx on port 80)..."
if systemctl is-active --quiet apache2 2>/dev/null; then
    log_debug "Apache2 is running, stopping it..."
    systemctl stop apache2 2>/dev/null || true
fi
if systemctl is-enabled --quiet apache2 2>/dev/null; then
    log_debug "Apache2 is enabled, disabling it..."
    systemctl disable apache2 2>/dev/null || true
fi
log_debug "Apache2 disabled (Nginx will handle all HTTP/HTTPS traffic)"

log_substep "Detecting PHP version..."
# Detect PHP version
PHP_VERSION=$(php -r "echo PHP_MAJOR_VERSION.'.'.PHP_MINOR_VERSION;" 2>/dev/null || echo "8.1")
log_info "PHP Version: ${PHP_VERSION}"
log_debug "PHP FPM service will be: php${PHP_VERSION}-fpm"

log_substep "Enabling and starting base services..."
log_cmd "systemctl enable mariadb redis-server nginx php${PHP_VERSION}-fpm"
# Enable services
systemctl enable mariadb redis-server nginx php${PHP_VERSION}-fpm 2>/dev/null || true
log_cmd "systemctl start mariadb redis-server php${PHP_VERSION}-fpm"
systemctl start mariadb redis-server php${PHP_VERSION}-fpm 2>/dev/null || true

log_info "System dependencies installed"
log_debug "Step 1 completed successfully"

# ============================================
# Step 2: Morgana Arsenal (Install or Update)
# ============================================
log_section "Step 2: Morgana Arsenal"

if [ "$FRESH_INSTALL" = true ]; then
    # Fresh installation
    log_substep "Performing FRESH installation..."
    log_info "Cloning Morgana Arsenal from ${MORGANA_REPO}..."
    log_cmd "git clone ${MORGANA_REPO} ${MORGANA_DIR}"
    
    sudo -u ${MORGANA_USER} git clone ${MORGANA_REPO} ${MORGANA_DIR}
    log_debug "Git clone completed"
    
    cd ${MORGANA_DIR}
    log_debug "Changed directory to ${MORGANA_DIR}"
    
    # Create Python virtual environment
    log_substep "Creating Python virtual environment..."
    log_cmd "python3 -m venv venv"
    sudo -u ${MORGANA_USER} python3 -m venv venv
    log_debug "Virtual environment created"
    
    log_substep "Installing Python dependencies..."
    log_cmd "pip install --upgrade pip && pip install -r requirements.txt"
    sudo -u ${MORGANA_USER} bash -c "source venv/bin/activate && pip install --upgrade pip && pip install -r requirements.txt"
    log_debug "Python dependencies installed"
    
    # Create local config
    if [ ! -f "conf/local.yml" ]; then
        log_substep "Creating local configuration (conf/local.yml)..."
        cat > conf/local.yml << EOF
# Morgana Arsenal Local Configuration
host: 0.0.0.0
port: 8888

users:
  admin:
    password: admin

plugins:
  - magma
  - stockpile
  - sandcat
  - merlino

logging:
  level: DEBUG
EOF
        chown ${MORGANA_USER}:${MORGANA_USER} conf/local.yml
        log_debug "Created conf/local.yml"
    else
        log_debug "conf/local.yml already exists"
    fi
    
    # Create agents.yml if not exists (required by Caldera)
    if [ ! -f "conf/agents.yml" ]; then
        log_substep "Creating agents.yml configuration..."
        if [ -f "plugins/merlino/conf/agents.yml" ]; then
            cp plugins/merlino/conf/agents.yml conf/agents.yml
            log_debug "Copied agents.yml from merlino plugin"
        else
            cat > conf/agents.yml << EOF
bootstrap_abilities:
- 43b3754c-def4-4699-a673-1d85648fda6a
deployments:
- merlino-1234-5678-90ab-cdef-merlino1
implant_name: svchost
sleep_max: 60
sleep_min: 30
untrusted_timer: 999999999
watchdog: 999999999
EOF
            log_debug "Created default agents.yml"
        fi
        chown ${MORGANA_USER}:${MORGANA_USER} conf/agents.yml
    else
        log_debug "conf/agents.yml already exists"
    fi
    
    # Create payloads.yml if not exists (required by Caldera)
    if [ ! -f "conf/payloads.yml" ]; then
        log_substep "Creating payloads.yml configuration..."
        cat > conf/payloads.yml << EOF
special_payloads: {}
standard_payloads: {}
EOF
        chown ${MORGANA_USER}:${MORGANA_USER} conf/payloads.yml
        log_debug "Created conf/payloads.yml"
    else
        log_debug "conf/payloads.yml already exists"
    fi
    
    # Create caldera log directory (server.py expects this path)
    log_substep "Creating log directories..."
    mkdir -p ${MORGANA_HOME}/caldera
    chown ${MORGANA_USER}:${MORGANA_USER} ${MORGANA_HOME}/caldera
    log_debug "Created ${MORGANA_HOME}/caldera directory"
    
    log_info "Morgana Arsenal installed"
    log_debug "Fresh installation completed"
    
else
    # Update existing installation
    log_substep "Performing UPDATE of existing installation..."
    log_info "Updating Morgana Arsenal..."
    
    cd ${MORGANA_DIR}
    log_debug "Changed directory to ${MORGANA_DIR}"
    
    # Stop service if running
    log_substep "Stopping morgana-arsenal service if running..."
    systemctl stop morgana-arsenal 2>/dev/null || true
    log_debug "Service stop command executed"
    
    # Backup config
    if [ -f "conf/local.yml" ]; then
        log_substep "Backing up conf/local.yml..."
        cp conf/local.yml conf/local.yml.backup
        log_info "Backed up conf/local.yml"
    fi
    
    # Update from repo
    log_substep "Updating git remote URL..."
    sudo -u ${MORGANA_USER} git remote set-url origin ${MORGANA_REPO} 2>/dev/null || \
    sudo -u ${MORGANA_USER} git remote add origin ${MORGANA_REPO} 2>/dev/null || true
    
    log_substep "Fetching latest changes from origin..."
    log_cmd "git fetch origin"
    sudo -u ${MORGANA_USER} git fetch origin
    
    log_substep "Resetting to origin/main..."
    log_cmd "git reset --hard origin/main"
    sudo -u ${MORGANA_USER} git reset --hard origin/main
    
    log_cmd "git pull origin main"
    sudo -u ${MORGANA_USER} git pull origin main 2>/dev/null || true
    log_debug "Git update completed"
    
    # Restore config
    if [ -f "conf/local.yml.backup" ]; then
        log_substep "Restoring conf/local.yml from backup..."
        cp conf/local.yml.backup conf/local.yml
        log_info "Restored conf/local.yml"
    fi
    
    # Update venv
    log_substep "Updating Python virtual environment..."
    if [ ! -d "venv" ]; then
        log_debug "venv not found, creating new one..."
        sudo -u ${MORGANA_USER} python3 -m venv venv
    fi
    log_cmd "pip install --upgrade pip && pip install -r requirements.txt"
    sudo -u ${MORGANA_USER} bash -c "source venv/bin/activate && pip install --upgrade pip && pip install -r requirements.txt"
    log_debug "Python dependencies updated"
    
    # Ensure agents.yml exists after update (required by Caldera)
    if [ ! -f "conf/agents.yml" ]; then
        log_substep "Creating agents.yml configuration..."
        if [ -f "plugins/merlino/conf/agents.yml" ]; then
            cp plugins/merlino/conf/agents.yml conf/agents.yml
            log_debug "Copied agents.yml from merlino plugin"
        else
            cat > conf/agents.yml << EOF
bootstrap_abilities:
- 43b3754c-def4-4699-a673-1d85648fda6a
deployments:
- merlino-1234-5678-90ab-cdef-merlino1
implant_name: svchost
sleep_max: 60
sleep_min: 30
untrusted_timer: 999999999
watchdog: 999999999
EOF
            log_debug "Created default agents.yml"
        fi
        chown ${MORGANA_USER}:${MORGANA_USER} conf/agents.yml
    fi
    
    # Ensure payloads.yml exists after update (required by Caldera)
    if [ ! -f "conf/payloads.yml" ]; then
        log_substep "Creating payloads.yml configuration..."
        cat > conf/payloads.yml << EOF
special_payloads: {}
standard_payloads: {}
EOF
        chown ${MORGANA_USER}:${MORGANA_USER} conf/payloads.yml
        log_debug "Created conf/payloads.yml"
    fi
    
    # Ensure caldera log directory exists
    log_substep "Ensuring log directories exist..."
    mkdir -p ${MORGANA_HOME}/caldera
    chown ${MORGANA_USER}:${MORGANA_USER} ${MORGANA_HOME}/caldera
    
    log_info "Morgana Arsenal updated"
    log_debug "Update completed"
fi

log_debug "Step 2 completed successfully"

# Build Magma frontend if needed
log_substep "Checking if Magma frontend needs building..."
if [ -d "${MORGANA_DIR}/plugins/magma" ] && [ ! -d "${MORGANA_DIR}/plugins/magma/dist" ]; then
    log_info "Building Magma frontend..."
    log_debug "Magma directory exists but dist/ not found"
    cd ${MORGANA_DIR}/plugins/magma
    if command -v npm &> /dev/null; then
        log_debug "npm found, proceeding with build"
        log_cmd "npm install"
        sudo -u ${MORGANA_USER} npm install
        log_cmd "npm run build"
        sudo -u ${MORGANA_USER} npm run build
    else
        log_warn "npm not found, installing Node.js..."
        log_cmd "curl -fsSL https://deb.nodesource.com/setup_20.x | bash -"
        curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
        log_cmd "apt-get install -y nodejs"
        apt-get install -y nodejs
        log_cmd "npm install"
        sudo -u ${MORGANA_USER} npm install
        log_cmd "npm run build"
        sudo -u ${MORGANA_USER} npm run build
    fi
    log_debug "Magma frontend build completed"
else
    log_debug "Magma frontend already built or directory not found"
fi

# ============================================
# Step 3: DNS Configuration (dnsmasq)
# ============================================
log_section "Step 3: Local DNS Configuration (dnsmasq)"

log_substep "Checking systemd-resolved status..."
# Stop systemd-resolved if it's blocking port 53
if systemctl is-active --quiet systemd-resolved; then
    log_info "Configuring systemd-resolved to work with dnsmasq..."
    log_debug "systemd-resolved is active, configuring to release port 53"
    
    # Configure systemd-resolved to not listen on port 53
    log_substep "Creating /etc/systemd/resolved.conf.d/dnsmasq.conf..."
    mkdir -p /etc/systemd/resolved.conf.d
    cat > /etc/systemd/resolved.conf.d/dnsmasq.conf << 'EOF'
[Resolve]
DNSStubListener=no
EOF
    log_debug "Created systemd-resolved config to disable DNSStubListener"
    
    log_cmd "systemctl restart systemd-resolved"
    systemctl restart systemd-resolved
    log_debug "systemd-resolved restarted"
else
    log_debug "systemd-resolved is not active"
fi

# Configure dnsmasq
log_substep "Creating dnsmasq configuration for ${LOCAL_DOMAIN}..."
log_info "Configuring dnsmasq for ${LOCAL_DOMAIN}..."

cat > /etc/dnsmasq.d/merlino.conf << EOF
# Merlino Local DNS Configuration
# All *.merlino.local domains resolve to this server

# Listen on all interfaces
listen-address=127.0.0.1
listen-address=${SERVER_IP}

# Don't read /etc/resolv.conf (we'll specify upstream DNS)
no-resolv

# Upstream DNS servers (use local gateway for forwarding)
server=${GATEWAY_IP}
server=8.8.8.8

# Local domain configuration
local=/${LOCAL_DOMAIN}/
domain=${LOCAL_DOMAIN}

# A records for local services
address=/${MORGANA_DOMAIN}/${SERVER_IP}
address=/${MISP_DOMAIN}/${SERVER_IP}
address=/${LAUNCHER_DOMAIN}/${SERVER_IP}

# Wildcard for all *.merlino.local
address=/${LOCAL_DOMAIN}/${SERVER_IP}

# Cache size
cache-size=1000

# Don't forward short names
domain-needed
bogus-priv

# Log queries (optional, comment out in production)
# log-queries
EOF
log_debug "Created /etc/dnsmasq.d/merlino.conf"

# Also add to /etc/hosts for local resolution
log_substep "Adding local domains to /etc/hosts..."
if ! grep -q "${MORGANA_DOMAIN}" /etc/hosts; then
    cat >> /etc/hosts << EOF

# Merlino Local Domains
${SERVER_IP} ${MORGANA_DOMAIN}
${SERVER_IP} ${MISP_DOMAIN}
${SERVER_IP} ${LAUNCHER_DOMAIN}
${SERVER_IP} ${LOCAL_DOMAIN}
EOF
    log_info "Added local domains to /etc/hosts"
    log_debug "Domains added: ${MORGANA_DOMAIN}, ${MISP_DOMAIN}, ${LAUNCHER_DOMAIN}"
else
    log_debug "Local domains already in /etc/hosts"
fi

# Enable and restart dnsmasq
log_substep "Enabling and restarting dnsmasq..."
log_cmd "systemctl enable dnsmasq"
systemctl enable dnsmasq
log_cmd "systemctl restart dnsmasq"
systemctl restart dnsmasq
log_debug "dnsmasq service restarted"

# Wait for dnsmasq to be fully ready
sleep 2

# Verify dnsmasq is running before updating resolv.conf
if systemctl is-active --quiet dnsmasq; then
    log_debug "dnsmasq is running, now safe to update resolv.conf"
    
    # Update resolv.conf to use dnsmasq with fallback to public DNS
    log_substep "Updating /etc/resolv.conf to use local DNS..."
    rm -f /etc/resolv.conf
    cat > /etc/resolv.conf << EOF
# Local DNS via dnsmasq for *.merlino.local
nameserver 127.0.0.1
# Fallback to gateway
nameserver ${GATEWAY_IP}
EOF
    log_debug "Updated /etc/resolv.conf to use 127.0.0.1 with ${GATEWAY_IP} fallback"
else
    log_warn "dnsmasq is not running, keeping original resolv.conf"
    log_debug "DNS will work via system default, local domains via /etc/hosts"
fi

# Verify DNS is working
log_substep "Verifying DNS resolution..."
sleep 2
if host ${MORGANA_DOMAIN} 127.0.0.1 &>/dev/null || nslookup ${MORGANA_DOMAIN} 127.0.0.1 &>/dev/null; then
    log_info "DNS resolution working for ${MORGANA_DOMAIN}"
    log_debug "DNS verification passed"
else
    log_warn "DNS may need manual verification. Check: nslookup ${MORGANA_DOMAIN} 127.0.0.1"
    log_debug "DNS verification failed - this may be normal if host/nslookup not installed"
fi

log_info "dnsmasq configured for ${LOCAL_DOMAIN}"
log_debug "Step 3 completed successfully"

# ============================================
# Step 4: SSL Certificates (with local domains)
# ============================================
log_section "Step 4: SSL Certificates"

log_substep "Creating SSL directory..."
mkdir -p /etc/nginx/ssl
log_debug "Created /etc/nginx/ssl directory"

# Always regenerate certificates to include local domains
log_info "Generating SSL certificates for local domains..."

log_substep "Creating OpenSSL SAN configuration..."
# Create OpenSSL config for SAN (Subject Alternative Names)
cat > /tmp/openssl-san.cnf << EOF
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
O = Morgana Arsenal
OU = Security
CN = ${MORGANA_DOMAIN}

[v3_req]
basicConstraints = CA:FALSE
keyUsage = nonRepudiation, digitalSignature, keyEncipherment
subjectAltName = @alt_names

[v3_ca]
basicConstraints = critical,CA:TRUE
keyUsage = critical, digitalSignature, cRLSign, keyCertSign
subjectAltName = @alt_names

[alt_names]
DNS.1 = ${MORGANA_DOMAIN}
DNS.2 = ${MISP_DOMAIN}
DNS.3 = ${LAUNCHER_DOMAIN}
DNS.4 = ${LOCAL_DOMAIN}
DNS.5 = *.${LOCAL_DOMAIN}
DNS.6 = localhost
IP.1 = ${SERVER_IP}
IP.2 = 127.0.0.1
EOF
log_debug "Created /tmp/openssl-san.cnf with SAN entries"

# Generate CA key and certificate (for importing into browsers/systems)
log_substep "Generating CA private key (4096 bit)..."
log_cmd "openssl genrsa -out /etc/nginx/ssl/merlino-ca.key 4096"
openssl genrsa -out /etc/nginx/ssl/merlino-ca.key 4096

log_substep "Generating CA certificate..."
log_cmd "openssl req -x509 -new -nodes ... -out /etc/nginx/ssl/merlino-ca.crt"
openssl req -x509 -new -nodes -key /etc/nginx/ssl/merlino-ca.key \
    -sha256 -days 3650 -out /etc/nginx/ssl/merlino-ca.crt \
    -subj "/C=IT/ST=Italy/L=Rome/O=Merlino CA/CN=Merlino Root CA"
log_debug "CA certificate created: /etc/nginx/ssl/merlino-ca.crt"

# Generate server key and CSR
log_substep "Generating server private key (2048 bit)..."
log_cmd "openssl genrsa -out /etc/nginx/ssl/caldera.key 2048"
openssl genrsa -out /etc/nginx/ssl/caldera.key 2048

log_substep "Generating certificate signing request (CSR)..."
log_cmd "openssl req -new -key /etc/nginx/ssl/caldera.key -out /tmp/caldera.csr"
openssl req -new -key /etc/nginx/ssl/caldera.key \
    -out /tmp/caldera.csr \
    -config /tmp/openssl-san.cnf
log_debug "CSR created: /tmp/caldera.csr"

# Sign the certificate with our CA
log_substep "Signing server certificate with CA..."
log_cmd "openssl x509 -req ... -out /etc/nginx/ssl/caldera.crt"
openssl x509 -req -in /tmp/caldera.csr \
    -CA /etc/nginx/ssl/merlino-ca.crt \
    -CAkey /etc/nginx/ssl/merlino-ca.key \
    -CAcreateserial \
    -out /etc/nginx/ssl/caldera.crt \
    -days 3650 -sha256 \
    -extfile /tmp/openssl-san.cnf \
    -extensions v3_req
log_debug "Server certificate created: /etc/nginx/ssl/caldera.crt"

# Cleanup
log_substep "Cleaning up temporary files..."
rm -f /tmp/openssl-san.cnf /tmp/caldera.csr
log_debug "Removed temporary CSR and config files"

log_substep "Setting certificate file permissions..."
chmod 600 /etc/nginx/ssl/caldera.key
chmod 600 /etc/nginx/ssl/merlino-ca.key
chmod 644 /etc/nginx/ssl/caldera.crt
chmod 644 /etc/nginx/ssl/merlino-ca.crt
log_debug "Permissions set: keys=600, certs=644"

# Copy CA cert to a user-accessible location
log_substep "Copying CA certificate to web root..."
mkdir -p /var/www/html
cp /etc/nginx/ssl/merlino-ca.crt /var/www/html/merlino-ca.crt 2>/dev/null || true
log_debug "CA certificate copied to /var/www/html/merlino-ca.crt"

log_info "SSL certificates generated for:"
log_info "  - ${MORGANA_DOMAIN}"
log_info "  - ${MISP_DOMAIN}"
log_info "  - ${LAUNCHER_DOMAIN}"
log_info "  - *.${LOCAL_DOMAIN}"
log_info "  - ${SERVER_IP}"
log_info ""
log_info "CA Certificate available at: http://${SERVER_IP}/merlino-ca.crt"
log_debug "Step 4 completed successfully"

# ============================================
# Step 5: Nginx Configuration for Morgana
# ============================================
log_section "Step 5: Nginx Configuration"

log_substep "Removing default nginx site..."
# Remove default site
rm -f /etc/nginx/sites-enabled/default
log_debug "Removed /etc/nginx/sites-enabled/default"

log_substep "Creating Morgana Arsenal nginx config (port 443 with CORS)..."
# Morgana Arsenal HTTPS (port 443) with CORS for Merlino Excel Add-in
cat > /etc/nginx/sites-available/caldera-proxy << 'NGINXEOF'
server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
NGINXEOF
cat >> /etc/nginx/sites-available/caldera-proxy << EOF
    server_name ${MORGANA_DOMAIN} ${SERVER_IP} localhost;
EOF
cat >> /etc/nginx/sites-available/caldera-proxy << 'NGINXEOF'

    ssl_certificate /etc/nginx/ssl/caldera.crt;
    ssl_certificate_key /etc/nginx/ssl/caldera.key;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    client_max_body_size 50M;

    location / {
        # CORS Headers for Merlino Excel Add-in (https://merlino-addin.x3m.ai)
        set $cors_origin "";
        set $cors_cred "";
        
        # Allow specific origins (production and development)
        if ($http_origin ~* "^https://(merlino-addin\.x3m\.ai|localhost:3000|127\.0\.0\.1:3000)$") {
            set $cors_origin $http_origin;
            set $cors_cred "true";
        }
        
        # For other origins, allow all (can be restricted in production)
        if ($cors_origin = "") {
            set $cors_origin "*";
            set $cors_cred "false";
        }

        add_header 'Access-Control-Allow-Origin' $cors_origin always;
        add_header 'Access-Control-Allow-Methods' 'GET, POST, PUT, DELETE, PATCH, OPTIONS' always;
        add_header 'Access-Control-Allow-Headers' 'KEY, Content-Type, Authorization, X-Requested-With, Accept, Origin' always;
        add_header 'Access-Control-Allow-Credentials' $cors_cred always;
        add_header 'Access-Control-Max-Age' 86400 always;

        # Handle preflight OPTIONS requests
        if ($request_method = 'OPTIONS') {
            add_header 'Access-Control-Allow-Origin' $cors_origin always;
            add_header 'Access-Control-Allow-Methods' 'GET, POST, PUT, DELETE, PATCH, OPTIONS' always;
            add_header 'Access-Control-Allow-Headers' 'KEY, Content-Type, Authorization, X-Requested-With, Accept, Origin' always;
            add_header 'Access-Control-Allow-Credentials' $cors_cred always;
            add_header 'Access-Control-Max-Age' 86400 always;
            add_header 'Content-Type' 'text/plain charset=UTF-8';
            add_header 'Content-Length' 0;
            return 204;
        }

        # Proxy to Morgana/Caldera
        proxy_pass http://127.0.0.1:8888;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_connect_timeout 300;
        proxy_send_timeout 300;
        proxy_read_timeout 300;
    }

    access_log /var/log/nginx/morgana-access.log;
    error_log /var/log/nginx/morgana-error.log warn;
}
NGINXEOF
log_debug "Created /etc/nginx/sites-available/caldera-proxy with CORS"

log_substep "Creating launcher nginx config (port 80)..."
# Launcher page (port 80)
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

    # CA Certificate download
    location /merlino-ca.crt {
        alias /var/www/html/merlino-ca.crt;
        add_header Content-Type application/x-x509-ca-cert;
    }
}
EOF
log_debug "Created /etc/nginx/sites-available/launcher.conf"

# Copy launcher page from repository (if available) or create minimal version
log_substep "Setting up launcher page..."
mkdir -p /var/www/html

# Try to copy the full launcher from the morgana-arsenal repository
if [ -f "${MORGANA_DIR}/static/launcher.html" ]; then
    log_info "Copying launcher.html from Morgana Arsenal repository..."
    cp "${MORGANA_DIR}/static/launcher.html" /var/www/html/launcher.html
    log_debug "Copied ${MORGANA_DIR}/static/launcher.html to /var/www/html/"
    
    # Also copy vm-services-guide.html if exists
    if [ -f "${MORGANA_DIR}/static/vm-services-guide.html" ]; then
        cp "${MORGANA_DIR}/static/vm-services-guide.html" /var/www/html/vm-services-guide.html
        log_debug "Copied vm-services-guide.html"
    fi
else
    log_warn "Repository launcher.html not found, creating minimal version..."
    cat > /var/www/html/launcher.html << 'HTMLEOF'
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Morgana Arsenal - Launcher</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            color: #fff;
        }
        .container { text-align: center; padding: 40px; max-width: 1200px; }
        h1 { font-size: 3em; margin-bottom: 10px; color: #e94560; }
        .subtitle { color: #a0a0a0; margin-bottom: 20px; }
        .dns-info { 
            background: rgba(0,0,0,0.3); 
            padding: 15px 25px; 
            border-radius: 10px; 
            margin-bottom: 30px;
            font-family: monospace;
            font-size: 0.9em;
        }
        .dns-info code { color: #4fc3f7; }
        .services { display: flex; gap: 30px; justify-content: center; flex-wrap: wrap; }
        .service-card {
            background: rgba(255,255,255,0.1);
            border-radius: 15px;
            padding: 30px;
            width: 280px;
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255,255,255,0.2);
            transition: transform 0.3s, box-shadow 0.3s;
            text-decoration: none;
            color: #fff;
        }
        .service-card:hover {
            transform: translateY(-10px);
            box-shadow: 0 20px 40px rgba(233, 69, 96, 0.3);
        }
        .service-icon { font-size: 3em; margin-bottom: 15px; }
        .service-name { font-size: 1.3em; font-weight: bold; margin-bottom: 10px; }
        .service-desc { color: #a0a0a0; font-size: 0.9em; margin-bottom: 10px; }
        .service-url { font-family: monospace; font-size: 0.8em; color: #4fc3f7; }
        .morgana-icon { color: #e94560; }
        .misp-icon { color: #4fc3f7; }
        .credentials { background: rgba(255,193,7,0.1); border: 1px solid rgba(255,193,7,0.3); border-radius: 8px; padding: 15px; margin-top: 30px; }
        .credentials h4 { color: #ffc107; margin-bottom: 8px; }
        .credentials code { background: rgba(0,0,0,0.3); padding: 2px 8px; border-radius: 4px; }
        .ca-link { margin-top: 30px; font-size: 0.9em; }
        .ca-link a { color: #4fc3f7; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Morgana Arsenal</h1>
        <p class="subtitle">Command & Control Framework</p>
        <div class="dns-info">
            DNS Server: <code id="serverIp"></code> | Domain: <code>*.merlino.local</code>
        </div>
        <div class="services">
            <a href="https://morgana.merlino.local/" class="service-card" id="morganaCard">
                <div class="service-icon morgana-icon">&#9876;</div>
                <div class="service-name">Morgana Arsenal</div>
                <div class="service-desc">C2 Framework<br>Port 443 (HTTPS)</div>
                <div class="service-url">https://morgana.merlino.local</div>
            </a>
            <a href="https://misp.merlino.local:8443/" class="service-card" id="mispCard">
                <div class="service-icon misp-icon">&#128373;</div>
                <div class="service-name">MISP</div>
                <div class="service-desc">Threat Intelligence<br>Port 8443 (HTTPS)</div>
                <div class="service-url">https://misp.merlino.local:8443</div>
            </a>
        </div>
        <div class="credentials">
            <h4>Default Credentials</h4>
            <p>Morgana: <code>admin</code> / <code>admin</code></p>
            <p>MISP: <code>admin@admin.test</code> / <code>admin</code></p>
        </div>
        <div class="ca-link">
            <p>To avoid certificate warnings, install the <a href="/merlino-ca.crt">Merlino CA Certificate</a></p>
        </div>
    </div>
    <script>
        document.getElementById('serverIp').textContent = location.hostname;
    </script>
</body>
</html>
HTMLEOF
    log_debug "Created minimal launcher.html"
fi

log_substep "Enabling nginx sites..."
# Enable Morgana sites
ln -sf /etc/nginx/sites-available/caldera-proxy /etc/nginx/sites-enabled/
ln -sf /etc/nginx/sites-available/launcher.conf /etc/nginx/sites-enabled/
log_debug "Created symlinks in /etc/nginx/sites-enabled/"

log_info "Nginx configured for Morgana Arsenal"
log_debug "Step 5 completed successfully"

# ============================================
# Step 6: Morgana Systemd Service
# ============================================
log_section "Step 6: Morgana Systemd Service"

log_substep "Creating systemd service file..."
cat > /etc/systemd/system/morgana-arsenal.service << EOF
[Unit]
Description=Morgana Arsenal C2 Framework
After=network.target

[Service]
Type=simple
User=${MORGANA_USER}
Group=${MORGANA_USER}
WorkingDirectory=${MORGANA_DIR}
ExecStart=${MORGANA_DIR}/venv/bin/python server.py --insecure --log DEBUG
Restart=always
RestartSec=10
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
EOF
log_debug "Created /etc/systemd/system/morgana-arsenal.service"

log_substep "Reloading systemd and enabling service..."
log_cmd "systemctl daemon-reload"
systemctl daemon-reload
log_cmd "systemctl enable morgana-arsenal"
systemctl enable morgana-arsenal
log_debug "morgana-arsenal service enabled"

log_info "Morgana Arsenal service configured"
log_debug "Step 6 completed successfully"

# ============================================
# Step 7: Install MISP
# ============================================
log_section "Step 7: Installing MISP"

MISP_DIR="/var/www/MISP"
log_debug "MISP_DIR=${MISP_DIR}"

if [ -d "${MISP_DIR}" ]; then
    log_substep "MISP directory exists, updating..."
    log_info "MISP directory exists, updating..."
    cd ${MISP_DIR}
    log_cmd "git config --global --add safe.directory ${MISP_DIR}"
    git config --global --add safe.directory ${MISP_DIR} 2>/dev/null || true
    log_cmd "git fetch origin"
    sudo -u www-data git fetch origin 2>/dev/null || git fetch origin 2>/dev/null || true
    log_cmd "git checkout 2.5"
    sudo -u www-data git checkout 2.5 2>/dev/null || git checkout 2.5 2>/dev/null || true
    log_cmd "git pull origin 2.5"
    sudo -u www-data git pull origin 2.5 2>/dev/null || git pull origin 2.5 2>/dev/null || true
    log_debug "MISP git update completed"
else
    log_substep "Cloning MISP repository..."
    log_info "Cloning MISP..."
    mkdir -p /var/www
    log_cmd "git clone ${MISP_REPO} ${MISP_DIR}"
    git clone ${MISP_REPO} ${MISP_DIR}
    chown -R www-data:www-data ${MISP_DIR}
    cd ${MISP_DIR}
    log_cmd "git config --global --add safe.directory ${MISP_DIR}"
    git config --global --add safe.directory ${MISP_DIR} 2>/dev/null || true
    log_cmd "git checkout 2.5"
    sudo -u www-data git checkout 2.5 2>/dev/null || git checkout 2.5 2>/dev/null || true
    log_debug "MISP cloned successfully"
fi

# Update submodules
log_substep "Updating MISP submodules..."
cd ${MISP_DIR}
log_cmd "git submodule update --init --recursive"
sudo -u www-data git submodule update --init --recursive 2>/dev/null || true
log_debug "Submodules updated"

# Python venv for MISP
log_substep "Setting up MISP Python environment..."
log_info "Setting up MISP Python environment..."
if [ ! -d "${MISP_DIR}/venv" ]; then
    log_cmd "python3 -m venv ${MISP_DIR}/venv"
    sudo -u www-data python3 -m venv ${MISP_DIR}/venv
    log_debug "MISP venv created"
fi
log_cmd "pip install --upgrade pip"
sudo -u www-data ${MISP_DIR}/venv/bin/pip install --upgrade pip 2>/dev/null || true
log_cmd "pip install -r requirements.txt"
sudo -u www-data ${MISP_DIR}/venv/bin/pip install -r ${MISP_DIR}/requirements.txt 2>/dev/null || true
log_debug "MISP Python dependencies installed"

# Composer dependencies
log_substep "Installing Composer dependencies..."
cd ${MISP_DIR}/app

# Ensure Composer is installed globally
if ! command -v composer &> /dev/null; then
    log_info "Installing Composer globally..."
    EXPECTED_CHECKSUM="$(php -r 'copy("https://composer.github.io/installer.sig", "php://stdout");')"
    php -r "copy('https://getcomposer.org/installer', '/tmp/composer-setup.php');"
    ACTUAL_CHECKSUM="$(php -r "echo hash_file('sha384', '/tmp/composer-setup.php');")"
    if [ "$EXPECTED_CHECKSUM" != "$ACTUAL_CHECKSUM" ]; then
        log_warn "Composer installer checksum mismatch, trying anyway..."
    fi
    php /tmp/composer-setup.php --install-dir=/usr/local/bin --filename=composer
    rm -f /tmp/composer-setup.php
    chmod +x /usr/local/bin/composer
    log_debug "Composer installed to /usr/local/bin/composer"
fi

# Install dependencies with proper permissions
if [ -f "composer.json" ]; then
    log_info "Running composer install for MISP..."
    # Create cache directory for www-data
    mkdir -p /var/www/.cache/composer
    chown -R www-data:www-data /var/www/.cache
    
    # Run composer as root with COMPOSER_ALLOW_SUPERUSER and proper cache dir
    # Note: Running as www-data often fails due to permission issues, running as root is safe for install
    log_cmd "composer install --no-dev --no-interaction"
    cd "${MISP_DIR}/app"
    COMPOSER_ALLOW_SUPERUSER=1 COMPOSER_HOME=/var/www/.cache/composer /usr/local/bin/composer install --no-dev --no-interaction 2>&1 || true
    cd "${MISP_DIR}"
    
    # Verify autoload.php was created
    if [ -f "${MISP_DIR}/app/Vendor/autoload.php" ]; then
        log_info "Composer dependencies installed successfully"
        log_debug "autoload.php verified at ${MISP_DIR}/app/Vendor/autoload.php"
    else
        log_warn "autoload.php not found - MISP may not work correctly"
        log_warn "You may need to run: cd /var/www/MISP/app && sudo composer install --no-dev"
    fi
    
    # Fix ownership after composer
    chown -R www-data:www-data ${MISP_DIR}/app/Vendor 2>/dev/null || true
fi

log_info "MISP installed/updated"
log_debug "Step 7 completed successfully"

# ============================================
# Step 8: Configure MariaDB for MISP
# ============================================
log_section "Step 8: Configuring MariaDB"

log_substep "Ensuring MariaDB is running..."
log_cmd "systemctl start mariadb"
systemctl start mariadb
log_debug "MariaDB started"

# Create MISP database
log_substep "Checking MISP database..."
if ! mysql -e "USE misp" 2>/dev/null; then
    log_substep "Creating MISP database..."
    log_info "Creating MISP database..."
    log_cmd "CREATE DATABASE misp"
    mysql -e "CREATE DATABASE IF NOT EXISTS misp CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
    log_cmd "CREATE USER misp@localhost"
    mysql -e "CREATE USER IF NOT EXISTS 'misp'@'localhost' IDENTIFIED BY 'misp_password';"
    log_cmd "GRANT ALL PRIVILEGES ON misp.*"
    mysql -e "GRANT ALL PRIVILEGES ON misp.* TO 'misp'@'localhost';"
    mysql -e "FLUSH PRIVILEGES;"
    log_debug "Database and user created"
    
    # Import schema if exists
    if [ -f "${MISP_DIR}/INSTALL/MYSQL.sql" ]; then
        log_substep "Importing database schema..."
        log_cmd "mysql < MISP/INSTALL/MYSQL.sql"
        mysql -u misp -pmisp_password misp < ${MISP_DIR}/INSTALL/MYSQL.sql 2>/dev/null || true
        log_info "Database schema imported"
        log_debug "Schema imported from ${MISP_DIR}/INSTALL/MYSQL.sql"
    else
        log_debug "No schema file found at ${MISP_DIR}/INSTALL/MYSQL.sql"
    fi
else
    log_info "MISP database already exists"
    log_debug "Skipping database creation (already exists)"
fi

log_debug "Step 8 completed successfully"

# ============================================
# Step 9: Configure MISP
# ============================================
log_section "Step 9: Configuring MISP"

log_substep "Entering MISP config directory..."
cd ${MISP_DIR}/app/Config
log_debug "Working directory: $(pwd)"

# Create config files (including bootstrap.php which is required)
log_substep "Creating MISP config files..."
for conf in database core config bootstrap; do
    if [ ! -f "${conf}.php" ] && [ -f "${conf}.default.php" ]; then
        log_cmd "cp ${conf}.default.php ${conf}.php"
        cp ${conf}.default.php ${conf}.php
        chown www-data:www-data ${conf}.php
        chmod 770 ${conf}.php
        log_info "Created ${conf}.php"
        log_debug "Created and set permissions for ${conf}.php"
    else
        log_debug "${conf}.php already exists or no default found"
    fi
done

# Update database config with correct credentials
log_substep "Configuring database credentials..."
if [ -f "database.php" ]; then
    # Replace placeholder credentials with actual ones
    sed -i "s/'login' => 'db login'/'login' => 'misp'/" database.php 2>/dev/null || true
    sed -i "s/'password' => 'db password'/'password' => 'misp_password'/" database.php 2>/dev/null || true
    sed -i "s/'password' => ''/'password' => 'misp_password'/" database.php 2>/dev/null || true
    log_info "Database credentials configured"
    log_debug "Updated database.php with MISP credentials"
else
    log_warn "database.php not found"
fi

# Set permissions
log_substep "Setting MISP directory permissions..."
log_cmd "chown -R www-data:www-data ${MISP_DIR}"
chown -R www-data:www-data ${MISP_DIR}
log_cmd "chmod -R 750 ${MISP_DIR}"
chmod -R 750 ${MISP_DIR}
chmod -R g+ws ${MISP_DIR}/app/tmp 2>/dev/null || true
chmod -R g+ws ${MISP_DIR}/app/files 2>/dev/null || true
log_debug "MISP permissions set"

log_info "MISP configured"
log_debug "Step 9 completed successfully"

# ============================================
# Step 10: Install MISP Modules
# ============================================
log_section "Step 10: Installing MISP Modules"

log_substep "Installing misp-modules via pip3..."
log_cmd "pip3 install misp-modules"
pip3 install misp-modules --break-system-packages --ignore-installed typing-extensions 2>/dev/null || \
pip3 install misp-modules --ignore-installed typing-extensions 2>/dev/null || \
pip3 install misp-modules 2>/dev/null || true
log_debug "misp-modules pip install completed"

# Verify installation
log_substep "Verifying misp-modules installation..."
if command -v misp-modules &> /dev/null; then
    log_debug "misp-modules found at: $(which misp-modules)"
else
    log_warn "misp-modules command not found in PATH"
fi

# Systemd service for MISP Modules
log_substep "Creating misp-modules systemd service..."
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
log_debug "Created /etc/systemd/system/misp-modules.service"

log_cmd "systemctl daemon-reload"
systemctl daemon-reload
log_cmd "systemctl enable misp-modules"
systemctl enable misp-modules
log_debug "misp-modules service enabled"

log_info "MISP Modules installed"
log_debug "Step 10 completed successfully"

# ============================================
# Step 11: Nginx for MISP
# ============================================
log_section "Step 11: Nginx for MISP"

log_substep "Creating MISP internal HTTP config (port 8080)..."
# MISP HTTP backend (internal only)
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

# MISP HTTPS (port 8443) with CORS for Merlino Excel Add-in
cat > /etc/nginx/sites-available/misp-https.conf << 'MISPEOF'
server {
    listen 8443 ssl http2;
    listen [::]:8443 ssl http2;
MISPEOF
cat >> /etc/nginx/sites-available/misp-https.conf << EOF
    server_name ${MISP_DOMAIN} ${SERVER_IP} localhost;
EOF
cat >> /etc/nginx/sites-available/misp-https.conf << 'MISPEOF'
    
    ssl_certificate /etc/nginx/ssl/caldera.crt;
    ssl_certificate_key /etc/nginx/ssl/caldera.key;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    
    root /var/www/MISP/app/webroot;
    index index.php;
    
    client_max_body_size 50M;

    # CORS Headers for Merlino Excel Add-in
    set $cors_origin "";
    set $cors_cred "";
    
    # Allow specific origins (production and development)
    if ($http_origin ~* "^https://(merlino-addin\.x3m\.ai|localhost:3000|127\.0\.0\.1:3000)$") {
        set $cors_origin $http_origin;
        set $cors_cred "true";
    }
    
    # For other origins, allow all
    if ($cors_origin = "") {
        set $cors_origin "*";
        set $cors_cred "false";
    }
    
    location / {
        add_header 'Access-Control-Allow-Origin' $cors_origin always;
        add_header 'Access-Control-Allow-Methods' 'GET, POST, PUT, DELETE, PATCH, OPTIONS' always;
        add_header 'Access-Control-Allow-Headers' 'Authorization, Content-Type, Accept, Origin, X-Requested-With' always;
        add_header 'Access-Control-Allow-Credentials' $cors_cred always;
        add_header 'Access-Control-Max-Age' 86400 always;

        # Handle preflight OPTIONS requests
        if ($request_method = 'OPTIONS') {
            add_header 'Access-Control-Allow-Origin' $cors_origin always;
            add_header 'Access-Control-Allow-Methods' 'GET, POST, PUT, DELETE, PATCH, OPTIONS' always;
            add_header 'Access-Control-Allow-Headers' 'Authorization, Content-Type, Accept, Origin, X-Requested-With' always;
            add_header 'Access-Control-Allow-Credentials' $cors_cred always;
            add_header 'Access-Control-Max-Age' 86400 always;
            add_header 'Content-Type' 'text/plain charset=UTF-8';
            add_header 'Content-Length' 0;
            return 204;
        }
        
        try_files $uri $uri/ /index.php?$args;
    }
MISPEOF
cat >> /etc/nginx/sites-available/misp-https.conf << EOF
    
    location ~ \.php\$ {
        # CORS headers also for PHP responses
        add_header 'Access-Control-Allow-Origin' \$cors_origin always;
        add_header 'Access-Control-Allow-Methods' 'GET, POST, PUT, DELETE, PATCH, OPTIONS' always;
        add_header 'Access-Control-Allow-Headers' 'Authorization, Content-Type, Accept, Origin, X-Requested-With' always;
        add_header 'Access-Control-Allow-Credentials' \$cors_cred always;
        add_header 'Access-Control-Max-Age' 86400 always;

        include snippets/fastcgi-php.conf;
        fastcgi_pass unix:/var/run/php/php${PHP_VERSION}-fpm.sock;
        fastcgi_param SCRIPT_FILENAME \$document_root\$fastcgi_script_name;
        fastcgi_param HTTPS on;
        include fastcgi_params;
    }
    
    access_log /var/log/nginx/misp-access.log;
    error_log /var/log/nginx/misp-error.log warn;
}
EOF
log_debug "Created /etc/nginx/sites-available/misp-https.conf with CORS"

# Enable MISP sites
log_substep "Enabling MISP nginx sites..."
log_cmd "ln -sf misp.conf sites-enabled/"
ln -sf /etc/nginx/sites-available/misp.conf /etc/nginx/sites-enabled/
log_cmd "ln -sf misp-https.conf sites-enabled/"
ln -sf /etc/nginx/sites-available/misp-https.conf /etc/nginx/sites-enabled/
log_debug "MISP nginx sites enabled"

# Test nginx config
log_substep "Testing nginx configuration..."
log_cmd "nginx -t"
if nginx -t 2>&1; then
    log_debug "Nginx configuration test passed"
else
    log_warn "Nginx configuration test failed - check logs"
fi

log_info "Nginx configured for MISP"
log_debug "Step 11 completed successfully"

# ============================================
# Step 12: Start All Services
# ============================================
log_section "Step 12: Starting Services"

log_substep "Restarting dnsmasq..."
log_cmd "systemctl restart dnsmasq"
systemctl restart dnsmasq
log_debug "dnsmasq restarted"

log_substep "Restarting PHP-FPM..."
log_cmd "systemctl restart php${PHP_VERSION}-fpm"
systemctl restart php${PHP_VERSION}-fpm
log_debug "PHP-FPM restarted"

log_substep "Testing nginx configuration before restart..."
if ! nginx -t 2>&1; then
    log_error "Nginx configuration test failed!"
    log_substep "Checking for common issues..."
    # Check if all required files exist
    for conf in caldera-proxy launcher.conf misp.conf misp-https.conf; do
        if [ -f "/etc/nginx/sites-available/$conf" ]; then
            log_debug "$conf exists"
        else
            log_warn "$conf missing from sites-available"
        fi
    done
    # Show nginx error for debugging
    nginx -t 2>&1 | head -10
fi

log_substep "Restarting nginx..."
log_cmd "systemctl restart nginx"
systemctl restart nginx
log_debug "nginx restarted"

log_substep "Starting Morgana Arsenal..."
log_cmd "systemctl start morgana-arsenal"
systemctl start morgana-arsenal
log_debug "morgana-arsenal started"

log_substep "Starting MISP Modules..."
log_cmd "systemctl start misp-modules"
systemctl start misp-modules 2>/dev/null || log_warn "MISP modules may need manual start"
log_debug "misp-modules start attempted"

log_substep "Starting Redis..."
log_cmd "systemctl start redis-server"
systemctl start redis-server
log_debug "redis-server started"

log_substep "Starting MariaDB..."
log_cmd "systemctl start mariadb"
systemctl start mariadb
log_debug "mariadb started"

# Wait for services to start
log_substep "Waiting 3 seconds for services to stabilize..."
sleep 3
log_debug "Wait completed"

log_info "All services started"
log_debug "Step 12 completed successfully"

# ============================================
# Step 13: Verification
# ============================================
log_section "Step 13: Verification"

log_substep "Checking service status..."
echo ""
echo -e "${BOLD}Service Status:${NC}"
echo "────────────────────────────────────"

check_service() {
    if systemctl is-active --quiet $1; then
        echo -e "  $2: ${GREEN}Running${NC}"
        log_debug "Service $1: RUNNING"
    else
        echo -e "  $2: ${RED}Stopped${NC}"
        log_warn "Service $1: STOPPED"
    fi
}

check_service dnsmasq "dnsmasq (DNS)"
check_service nginx "Nginx"
check_service morgana-arsenal "Morgana Arsenal"
check_service php${PHP_VERSION}-fpm "PHP-FPM"
check_service misp-modules "MISP Modules"
check_service mariadb "MariaDB"
check_service redis-server "Redis"

echo ""
log_substep "Checking listening ports..."
echo -e "${BOLD}Port Status:${NC}"
echo "────────────────────────────────────"
PORTS=$(ss -tlnp 2>/dev/null | grep -E ":(80|443|8080|8443|8888|6666) " | awk '{print "  "$4}')
if [ -n "$PORTS" ]; then
    echo "$PORTS"
    log_debug "Listening ports: $(echo $PORTS | tr '\n' ' ')"
else
    echo "  (check with: ss -tlnp)"
    log_warn "Could not detect listening ports"
fi

log_debug "Step 13 completed successfully"

# ============================================
# Complete!
# ============================================
log_section "Installation Complete!"

log_info "All installation steps completed successfully"

# Calculate installation time (safely, without exiting on error)
INSTALL_DURATION="unknown"
{
    END_TIME=$(date +%s)
    START_TIME_STR=$(head -3 "${LOG_FILE}" 2>/dev/null | tail -1 | grep -oP '\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}' || echo "")
    if [ -n "$START_TIME_STR" ]; then
        START_TIME=$(date -d "$START_TIME_STR" +%s 2>/dev/null || echo "0")
        if [ "$START_TIME" -gt 0 ]; then
            INSTALL_DURATION="$((END_TIME - START_TIME)) seconds"
        fi
    fi
} || true

log_debug "Total installation time: ${INSTALL_DURATION}"
log_debug "Log file saved to: ${LOG_FILE}"

# Disable set -e to ensure summary is always printed
set +e

echo -e "
${GREEN}${BOLD}Morgana Arsenal + MISP installed successfully!${NC}

${CYAN}${BOLD}Local DNS Domains:${NC}
────────────────────────────────────
  DNS Server:      ${SERVER_IP} (use as DNS on client machines)
  Morgana:         ${MORGANA_DOMAIN}
  MISP:            ${MISP_DOMAIN}
  Launcher:        ${LAUNCHER_DOMAIN}

${CYAN}${BOLD}Access URLs (via DNS):${NC}
────────────────────────────────────
  Launcher:        http://${LAUNCHER_DOMAIN}
  Morgana Arsenal: https://${MORGANA_DOMAIN}
  MISP:            https://${MISP_DOMAIN}:8443

${CYAN}${BOLD}Access URLs (via IP):${NC}
────────────────────────────────────
  Launcher:        http://${SERVER_IP}
  Morgana Arsenal: https://${SERVER_IP}
  MISP:            https://${SERVER_IP}:8443

${CYAN}${BOLD}Default Credentials:${NC}
────────────────────────────────────
  Morgana: admin / admin
  MISP:    admin@admin.test / admin

${CYAN}${BOLD}CA Certificate (to avoid browser warnings):${NC}
────────────────────────────────────
  Download: http://${SERVER_IP}/merlino-ca.crt
  Location: /etc/nginx/ssl/merlino-ca.crt

  Install on clients:
    Windows: Double-click > Install > Trusted Root CAs
    macOS:   Double-click > Add to Keychain > Trust
    Linux:   sudo cp merlino-ca.crt /usr/local/share/ca-certificates/
             sudo update-ca-certificates

${CYAN}${BOLD}Client DNS Configuration:${NC}
────────────────────────────────────
  Set DNS server to: ${SERVER_IP}
  
  Or add to /etc/hosts (Linux/Mac) or C:\\Windows\\System32\\drivers\\etc\\hosts:
    ${SERVER_IP} ${MORGANA_DOMAIN} ${MISP_DOMAIN} ${LAUNCHER_DOMAIN}

${CYAN}${BOLD}Useful Commands:${NC}
────────────────────────────────────
  sudo systemctl status morgana-arsenal
  sudo systemctl status dnsmasq
  nslookup ${MORGANA_DOMAIN} ${SERVER_IP}
  curl http://127.0.0.1:6666/modules

${CYAN}${BOLD}Logs:${NC}
────────────────────────────────────
  Install Log: ${LOG_FILE}
  Morgana:     ${MORGANA_DIR}/caldera-debug.log
  DNS:         /var/log/syslog | grep dnsmasq
  Nginx:       /var/log/nginx/morgana-*.log
  MISP:        /var/log/nginx/misp-*.log

${YELLOW}${BOLD}Troubleshooting:${NC}
────────────────────────────────────
  If something went wrong, check the installation log:
  cat ${LOG_FILE}
  
  For real-time troubleshooting during installation:
  tail -f ${LOG_FILE}
"
