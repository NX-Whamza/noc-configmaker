#!/bin/bash
set -euo pipefail

DOMAIN="noc-configmaker.nxlink.com"
IP_ADDR="192.168.11.118"
CONFIG_PATH="/etc/nginx/sites-available/noc-configmaker-domain"
ENABLED_PATH="/etc/nginx/sites-enabled/noc-configmaker-domain"
CERT_DIR="/etc/letsencrypt/live/${DOMAIN}"
EMAIL="whamza@team.nxlink.com"
WEBROOT="/var/www/html"
MANUAL_CERT="/etc/nginx/ssl/nxlink-com.pem"
MANUAL_KEY="/etc/nginx/ssl/nxlink-com.key"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

info() {
    echo -e "${YELLOW}[INFO] $*${NC}"
}

ok() {
    echo -e "${GREEN}[OK] $*${NC}"
}

warn() {
    echo -e "${YELLOW}[WARN] $*${NC}"
}

error() {
    echo -e "${RED}[ERROR] $*${NC}"
}

write_proxy_block() {
    cat <<'BLOCK'
    proxy_connect_timeout 300s;
    proxy_send_timeout 300s;
    proxy_read_timeout 300s;
    send_timeout 300s;

    location /api/ {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_buffering off;
    }

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
BLOCK
}

generate_http_config() {
    sudo tee "$CONFIG_PATH" > /dev/null <<EOF
server {
    listen 80 default_server;
    listen [::]:80 default_server;
    server_name ${DOMAIN} ${IP_ADDR};

    location /.well-known/acme-challenge/ {
        root ${WEBROOT};
        try_files \$uri =404;
    }

$(write_proxy_block)
}
EOF
}

generate_https_config() {
    local cert_path="$1"
    local key_path="$2"

    sudo tee "$CONFIG_PATH" > /dev/null <<EOF
# Redirect HTTP to HTTPS so ACME/clients always reach SSL
server {
    listen 80 default_server;
    listen [::]:80 default_server;
    server_name ${DOMAIN} ${IP_ADDR};

    location /.well-known/acme-challenge/ {
        root ${WEBROOT};
        try_files \$uri =404;
    }

    location / {
        return 301 https://\$host\$request_uri;
    }
}

server {
    listen 443 ssl http2 default_server;
    listen [::]:443 ssl http2 default_server;
    server_name ${DOMAIN} ${IP_ADDR};

    ssl_certificate     ${cert_path};
    ssl_certificate_key ${key_path};
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;

    location /.well-known/acme-challenge/ {
        root ${WEBROOT};
        try_files \$uri =404;
    }

$(write_proxy_block)
}
EOF
}

attempt_certbot() {
    info "Requesting Let's Encrypt certificate for ${DOMAIN}..."

    if sudo certbot certonly --webroot -w "$WEBROOT" -d "$DOMAIN" --non-interactive --agree-tos --email "$EMAIL" >/tmp/certbot.log 2>&1; then
        ok "Certificate issued. Logs written to /tmp/certbot.log"
        return 0
    else
        warn "Certificate issuance failed (see /tmp/certbot.log). Ensure the A record points to this server."
        return 1
    fi
}

configure_firewall() {
    if command -v ufw &> /dev/null && sudo ufw status | grep -q "Status: active"; then
        info "Opening HTTP/HTTPS ports in ufw..."
        sudo ufw allow 80/tcp comment "HTTP - NOC Config Maker" >/dev/null 2>&1 || true
        sudo ufw allow 443/tcp comment "HTTPS - NOC Config Maker" >/dev/null 2>&1 || true
        ok "Firewall rules updated (ports 80 and 443)."
    fi
}

print_header() {
    echo "=========================================="
    echo "Nginx Domain Configuration"
    echo "Domain: ${DOMAIN}"
    echo "=========================================="
    echo ""
}

print_header

if [ "$EUID" -eq 0 ]; then 
   error "Please do not run as root. This script uses sudo when needed."
   exit 1
fi

info "Checking prerequisites..."

if ! command -v certbot &> /dev/null; then
    warn "Certbot not found. Installing..."
    sudo apt update
    sudo apt install -y certbot python3-certbot-nginx >/dev/null
    ok "Certbot installed."
else
    ok "Certbot already available."
fi

sudo mkdir -p "$WEBROOT"

CERT_PATH=""
KEY_PATH=""
MANUAL_USED=false

if [[ -f "$MANUAL_CERT" && -f "$MANUAL_KEY" ]]; then
    SSL_MODE="ssl"
    CERT_PATH="$MANUAL_CERT"
    KEY_PATH="$MANUAL_KEY"
    MANUAL_USED=true
    ok "Manual certificate found under /etc/nginx/ssl."
elif [[ -d "$CERT_DIR" ]]; then
    SSL_MODE="ssl"
    CERT_PATH="${CERT_DIR}/fullchain.pem"
    KEY_PATH="${CERT_DIR}/privkey.pem"
    ok "Let’s Encrypt certificate detected. HTTPS will be enabled."
else
    SSL_MODE="http"
    warn "No certificate found yet. Starting with HTTP-only proxy."
fi

info "Generating nginx configuration (${SSL_MODE} mode)..."
if [[ "$SSL_MODE" == "ssl" ]]; then
    generate_https_config "$CERT_PATH" "$KEY_PATH"
else
    generate_http_config
fi

info "Enabling site configuration..."
sudo ln -sf "$CONFIG_PATH" "$ENABLED_PATH"
sudo rm -f /etc/nginx/sites-enabled/default* >/dev/null 2>&1 || true

info "Testing nginx configuration..."
sudo nginx -t
ok "nginx configuration is valid."

info "Reloading nginx..."
sudo systemctl reload nginx

if [[ "$MANUAL_USED" == true ]]; then
    info "Manual certificate is in use; skipping Certbot."
elif [[ "$SSL_MODE" == "http" ]]; then
    if attempt_certbot; then
        SSL_MODE="ssl"
        CERT_PATH="${CERT_DIR}/fullchain.pem"
        KEY_PATH="${CERT_DIR}/privkey.pem"
        info "Regenerating nginx configuration with HTTPS enabled..."
        generate_https_config "$CERT_PATH" "$KEY_PATH"
        sudo nginx -t
        sudo systemctl reload nginx
        ok "HTTPS configuration active."
    else
        warn "Continuing with HTTP only. Run this script again after DNS propagation."
    fi
else
    info "Refreshing existing LetsEncrypt certificate (if due)..."
    sudo certbot renew --webroot -w "$WEBROOT" --quiet >/tmp/certbot-renew.log 2>&1 || warn "Certificate renewal log: /tmp/certbot-renew.log"
fi

configure_firewall

sudo systemctl reload nginx

echo ""
echo "=========================================="
echo "Configuration Complete!"
echo "=========================================="
echo ""

if [[ "$MANUAL_USED" == true || -d "$CERT_DIR" ]]; then
    ok "Your application is reachable via https://${DOMAIN}"
    info "HTTP requests are redirected to HTTPS."
else
    warn "HTTPS is not configured yet."
    info "Your application is currently reachable via:"
    echo "  http://${DOMAIN}"
    echo "  http://${IP_ADDR}"
fi

echo ""
info "Make sure the backend service is running:"
echo "  sudo systemctl status noc-configmaker"

if ! sudo systemctl is-active --quiet noc-configmaker; then
    warn "Backend is not running. Starting it..."
    sudo systemctl start noc-configmaker
    sleep 2
    sudo systemctl status noc-configmaker --no-pager -l
else
    ok "Backend service is running."
fi

echo ""
echo "=========================================="
