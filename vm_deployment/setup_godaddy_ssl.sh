#!/bin/bash
# Setup Nginx with GoDaddy wildcard certificate

set +e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo "=========================================="
echo "Nginx + GoDaddy SSL Configuration"
echo "=========================================="
echo ""

# Check if running as root
if [ "$EUID" -eq 0 ]; then 
   echo -e "${RED}Please do not run as root.${NC}"
   exit 1
fi

# Step 1: Check if backend is running
echo -e "${YELLOW}[1] Checking backend service...${NC}"
if ! sudo systemctl is-active --quiet noc-configmaker; then
    echo -e "${YELLOW}Starting backend...${NC}"
    sudo systemctl start noc-configmaker
    sleep 2
fi

# Step 2: Create directory for certificates
echo -e "${YELLOW}[2] Setting up certificate directory...${NC}"
sudo mkdir -p /etc/nginx/ssl/noc-configmaker
echo -e "${GREEN}✓${NC} Directory created: /etc/nginx/ssl/noc-configmaker"
echo ""
echo -e "${YELLOW}You need to place your GoDaddy certificate files here:${NC}"
echo "  /etc/nginx/ssl/noc-configmaker/fullchain.pem (or cert.pem)"
echo "  /etc/nginx/ssl/noc-configmaker/privkey.pem (or key.pem)"
echo ""
echo -e "${YELLOW}Do you have the certificate files ready? (y/n)${NC}"
read -r response
if [[ ! "$response" =~ ^[Yy]$ ]]; then
    echo -e "${YELLOW}Setting up HTTP-only config for now. You can add SSL later.${NC}"
    SSL_READY=false
else
    SSL_READY=true
fi

# Step 3: Create Nginx config
echo -e "${YELLOW}[3] Creating Nginx configuration...${NC}"

if [ "$SSL_READY" = true ] && [ -f "/etc/nginx/ssl/noc-configmaker/fullchain.pem" ] && [ -f "/etc/nginx/ssl/noc-configmaker/privkey.pem" ]; then
    # Config WITH SSL
    sudo tee /etc/nginx/sites-available/noc-configmaker-domain > /dev/null <<'EOF'
server {
    listen 80;
    listen [::]:80;
    server_name noc-configmaker.nxlink.com 192.168.11.118;
    
    location /.well-known/acme-challenge/ {
        root /var/www/html;
    }
    
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name noc-configmaker.nxlink.com;
    
    ssl_certificate /etc/nginx/ssl/noc-configmaker/fullchain.pem;
    ssl_certificate_key /etc/nginx/ssl/noc-configmaker/privkey.pem;
    
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;
    
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    
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
}
EOF
    echo -e "${GREEN}✓${NC} HTTPS configuration created"
else
    # Config WITHOUT SSL - HTTP only (no redirect)
    sudo tee /etc/nginx/sites-available/noc-configmaker-domain > /dev/null <<'EOF'
server {
    listen 80 default_server;
    listen [::]:80 default_server;
    server_name noc-configmaker.nxlink.com 192.168.11.118 _;
    
    location /.well-known/acme-challenge/ {
        root /var/www/html;
    }
    
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
}
EOF
    echo -e "${GREEN}✓${NC} HTTP-only configuration created (no SSL redirect)"
fi

# Step 4: Enable and test
echo -e "${YELLOW}[4] Enabling and testing Nginx...${NC}"
sudo rm -f /etc/nginx/sites-enabled/default
sudo ln -sf /etc/nginx/sites-available/noc-configmaker-domain /etc/nginx/sites-enabled/

if sudo nginx -t; then
    echo -e "${GREEN}✓${NC} Nginx config is valid"
    sudo systemctl reload nginx
    echo -e "${GREEN}✓${NC} Nginx reloaded"
else
    echo -e "${RED}✗${NC} Nginx config error!"
    exit 1
fi

echo ""
echo "=========================================="
echo -e "${GREEN}Configuration Complete!${NC}"
echo "=========================================="
echo ""

if [ "$SSL_READY" = true ] && [ -f "/etc/nginx/ssl/noc-configmaker/fullchain.pem" ]; then
    echo "Your application is accessible at:"
    echo -e "  ${GREEN}https://noc-configmaker.nxlink.com${NC}"
else
    echo "Your application is accessible at:"
    echo -e "  ${GREEN}http://noc-configmaker.nxlink.com${NC}"
    echo -e "  ${GREEN}http://192.168.11.118${NC}"
    echo ""
    echo -e "${YELLOW}To enable HTTPS:${NC}"
    echo "1. Copy your GoDaddy certificate files to:"
    echo "   /etc/nginx/ssl/noc-configmaker/fullchain.pem"
    echo "   /etc/nginx/ssl/noc-configmaker/privkey.pem"
    echo "2. Run this script again"
fi

echo ""
echo "Backend status:"
sudo systemctl status noc-configmaker --no-pager -l | head -5
echo ""
echo "=========================================="
