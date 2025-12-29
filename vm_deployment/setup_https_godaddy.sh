#!/bin/bash
# Setup HTTPS with GoDaddy wildcard certificate for noc-configmaker.nxlink.com

set +e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo "=========================================="
echo "HTTPS Setup with GoDaddy Certificate"
echo "Domain: noc-configmaker.nxlink.com"
echo "=========================================="
echo ""

if [ "$EUID" -eq 0 ]; then 
   echo -e "${RED}Please do not run as root.${NC}"
   exit 1
fi

# Step 1: Create SSL directory
echo -e "${YELLOW}[1] Creating SSL certificate directory...${NC}"
sudo mkdir -p /etc/nginx/ssl/noc-configmaker
sudo chmod 755 /etc/nginx/ssl/noc-configmaker
echo -e "${GREEN}✓${NC} Directory created: /etc/nginx/ssl/noc-configmaker"
echo ""

# Step 2: Instructions for certificate files
echo -e "${YELLOW}[2] Certificate Files Required:${NC}"
echo ""
echo "You need to place your GoDaddy certificate files in:"
echo -e "  ${GREEN}/etc/nginx/ssl/noc-configmaker/fullchain.pem${NC} (or cert.pem)"
echo -e "  ${GREEN}/etc/nginx/ssl/noc-configmaker/privkey.pem${NC} (or key.pem)"
echo ""
echo "If you have the certificate files, you can:"
echo "  1. Copy them via SCP from your local machine"
echo "  2. Or paste the contents directly"
echo ""
echo -e "${YELLOW}Do you have the certificate files ready to install? (y/n)${NC}"
read -r response

if [[ ! "$response" =~ ^[Yy]$ ]]; then
    echo ""
    echo -e "${YELLOW}To get your GoDaddy certificate files:${NC}"
    echo "1. Log into your GoDaddy account"
    echo "2. Go to SSL Certificates"
    echo "3. Download the certificate for *.nxlink.com"
    echo "4. You'll get files like:"
    echo "   - certificate.crt (or similar)"
    echo "   - private.key (or similar)"
    echo ""
    echo "Then run this script again and copy the files to:"
    echo "  /etc/nginx/ssl/noc-configmaker/"
    echo ""
    exit 0
fi

# Step 3: Check if certificate files exist
echo ""
echo -e "${YELLOW}[3] Checking for certificate files...${NC}"

CERT_FILE=""
KEY_FILE=""

# Check for common certificate file names
if [ -f "/etc/nginx/ssl/noc-configmaker/fullchain.pem" ]; then
    CERT_FILE="/etc/nginx/ssl/noc-configmaker/fullchain.pem"
elif [ -f "/etc/nginx/ssl/noc-configmaker/cert.pem" ]; then
    CERT_FILE="/etc/nginx/ssl/noc-configmaker/cert.pem"
elif [ -f "/etc/nginx/ssl/noc-configmaker/certificate.crt" ]; then
    CERT_FILE="/etc/nginx/ssl/noc-configmaker/certificate.crt"
fi

if [ -f "/etc/nginx/ssl/noc-configmaker/privkey.pem" ]; then
    KEY_FILE="/etc/nginx/ssl/noc-configmaker/privkey.pem"
elif [ -f "/etc/nginx/ssl/noc-configmaker/key.pem" ]; then
    KEY_FILE="/etc/nginx/ssl/noc-configmaker/key.pem"
elif [ -f "/etc/nginx/ssl/noc-configmaker/private.key" ]; then
    KEY_FILE="/etc/nginx/ssl/noc-configmaker/private.key"
fi

if [ -z "$CERT_FILE" ] || [ -z "$KEY_FILE" ]; then
    echo -e "${RED}✗${NC} Certificate files not found!"
    echo ""
    echo "Please copy your certificate files to:"
    echo "  /etc/nginx/ssl/noc-configmaker/"
    echo ""
    echo "Required files:"
    echo "  - Certificate file (fullchain.pem, cert.pem, or certificate.crt)"
    echo "  - Private key file (privkey.pem, key.pem, or private.key)"
    echo ""
    echo "You can copy files using SCP from your local machine:"
    echo "  scp certificate.crt <user>@<vm-ip>:/tmp/"
    echo "  scp private.key <user>@<vm-ip>:/tmp/"
    echo "  Then on VM: sudo mv /tmp/certificate.crt /etc/nginx/ssl/noc-configmaker/"
    echo "              sudo mv /tmp/private.key /etc/nginx/ssl/noc-configmaker/privkey.pem"
    exit 1
fi

echo -e "${GREEN}✓${NC} Found certificate: $CERT_FILE"
echo -e "${GREEN}✓${NC} Found private key: $KEY_FILE"

# Set proper permissions
sudo chmod 644 "$CERT_FILE"
sudo chmod 600 "$KEY_FILE"
echo -e "${GREEN}✓${NC} Permissions set"

# Step 4: Create Nginx config with HTTPS
echo ""
echo -e "${YELLOW}[4] Creating Nginx configuration with HTTPS...${NC}"

sudo tee /etc/nginx/sites-available/noc-configmaker-domain > /dev/null <<EOF
# HTTP server - redirect to HTTPS
server {
    listen 80;
    listen [::]:80;
    server_name noc-configmaker.nxlink.com 192.168.11.118;
    
    location /.well-known/acme-challenge/ {
        root /var/www/html;
    }
    
    # Redirect all HTTP to HTTPS (308 preserves method for API POSTs)
    return 308 https://\$host\$request_uri;
}

# HTTPS server
server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name noc-configmaker.nxlink.com;
    
    # SSL certificate paths
    ssl_certificate $CERT_FILE;
    ssl_certificate_key $KEY_FILE;
    
    # SSL configuration
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers 'ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384:ECDHE-ECDSA-CHACHA20-POLY1305:ECDHE-RSA-CHACHA20-POLY1305:DHE-RSA-AES128-GCM-SHA256:DHE-RSA-AES256-GCM-SHA384';
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;
    
    # Security headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    
    # Proxy timeouts for long-running requests
    proxy_connect_timeout 300s;
    proxy_send_timeout 300s;
    proxy_read_timeout 300s;
    send_timeout 300s;
    
    # API routes - proxy to Flask backend
    location /api/ {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_set_header X-Forwarded-Host \$host;
        proxy_set_header X-Forwarded-Port \$server_port;
        
        # WebSocket support
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        
        # Buffer settings
        proxy_buffering off;
        proxy_request_buffering off;
    }
    
    # All other routes - proxy to Flask backend
    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_set_header X-Forwarded-Host \$host;
        proxy_set_header X-Forwarded-Port \$server_port;
        
        # WebSocket support
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
EOF

echo -e "${GREEN}✓${NC} Nginx configuration created"

# Step 5: Enable and test
echo ""
echo -e "${YELLOW}[5] Enabling and testing Nginx...${NC}"

sudo rm -f /etc/nginx/sites-enabled/default
sudo ln -sf /etc/nginx/sites-available/noc-configmaker-domain /etc/nginx/sites-enabled/

if sudo nginx -t; then
    echo -e "${GREEN}✓${NC} Nginx configuration is valid"
    sudo systemctl reload nginx
    echo -e "${GREEN}✓${NC} Nginx reloaded"
else
    echo -e "${RED}✗${NC} Nginx configuration error!"
    sudo nginx -t
    exit 1
fi

# Step 6: Check backend
echo ""
echo -e "${YELLOW}[6] Checking backend service...${NC}"
if ! sudo systemctl is-active --quiet noc-configmaker; then
    echo -e "${YELLOW}Starting backend...${NC}"
    sudo systemctl start noc-configmaker
    sleep 2
fi

if sudo systemctl is-active --quiet noc-configmaker; then
    echo -e "${GREEN}✓${NC} Backend service is running"
else
    echo -e "${RED}✗${NC} Backend service failed to start"
    sudo systemctl status noc-configmaker --no-pager -l | head -10
fi

# Step 7: Test HTTPS
echo ""
echo -e "${YELLOW}[7] Testing HTTPS connection...${NC}"
sleep 2

if curl -k -s https://127.0.0.1/ | grep -q "NOC-configMaker\|login"; then
    echo -e "${GREEN}✓${NC} HTTPS is working!"
else
    echo -e "${YELLOW}⚠${NC} HTTPS test inconclusive (may need DNS to be configured)"
    echo "Testing HTTP redirect:"
    curl -I http://127.0.0.1/ 2>&1 | head -5
fi

echo ""
echo "=========================================="
echo -e "${GREEN}HTTPS Configuration Complete!${NC}"
echo "=========================================="
echo ""
echo "Your application is now accessible at:"
echo -e "  ${GREEN}https://noc-configmaker.nxlink.com${NC}"
echo -e "  ${YELLOW}http://noc-configmaker.nxlink.com${NC} (redirects to HTTPS)"
echo ""
echo "Note: Make sure DNS A record points noc-configmaker.nxlink.com to 192.168.11.118"
echo ""
echo "=========================================="
