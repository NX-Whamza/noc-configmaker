#!/bin/bash
# Simple fix: Configure Nginx to proxy to Flask backend

set +e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo "=========================================="
echo "Fixing Nginx to Proxy to Flask"
echo "=========================================="
echo ""

# 1. Make sure backend is running
echo -e "${YELLOW}[1] Starting backend...${NC}"
sudo systemctl start noc-configmaker
sleep 2
if sudo systemctl is-active --quiet noc-configmaker; then
    echo -e "${GREEN}✓${NC} Backend running"
else
    echo -e "${RED}✗${NC} Backend failed to start"
    sudo systemctl status noc-configmaker --no-pager -l | head -10
    exit 1
fi

# 2. Remove default config
echo -e "${YELLOW}[2] Removing default Nginx config...${NC}"
sudo rm -f /etc/nginx/sites-enabled/default
echo -e "${GREEN}✓${NC} Default removed"

# 3. Create correct config
echo -e "${YELLOW}[3] Creating Nginx config...${NC}"
sudo tee /etc/nginx/sites-available/noc-configmaker-domain > /dev/null <<'EOF'
server {
    listen 80 default_server;
    listen [::]:80 default_server;
    server_name noc-configmaker.nxlink.com 192.168.11.118 _;
    
    proxy_connect_timeout 300s;
    proxy_send_timeout 300s;
    proxy_read_timeout 300s;
    
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

# 4. Enable and reload
echo -e "${YELLOW}[4] Enabling and reloading Nginx...${NC}"
sudo ln -sf /etc/nginx/sites-available/noc-configmaker-domain /etc/nginx/sites-enabled/

if sudo nginx -t; then
    sudo systemctl reload nginx
    echo -e "${GREEN}✓${NC} Nginx configured and reloaded"
else
    echo -e "${RED}✗${NC} Nginx config error"
    sudo nginx -t
    exit 1
fi

# 5. Test
echo -e "${YELLOW}[5] Testing...${NC}"
sleep 2
if curl -s http://127.0.0.1/ | grep -q "NOC-configMaker\|login"; then
    echo -e "${GREEN}✓${NC} Working!"
else
    echo -e "${YELLOW}Testing backend directly...${NC}"
    curl -s http://127.0.0.1:5000/ | head -5
fi

echo ""
echo "=========================================="
echo -e "${GREEN}Done!${NC}"
echo "Access: http://noc-configmaker.nxlink.com"
echo "=========================================="
