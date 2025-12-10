#!/bin/bash
# Quick fix script - checks and fixes Nginx + Backend

set +e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo "=========================================="
echo "Quick Fix: Nginx + Backend"
echo "=========================================="
echo ""

# 1. Check if backend is running
echo -e "${YELLOW}[1] Checking backend service...${NC}"
if sudo systemctl is-active --quiet noc-configmaker; then
    echo -e "${GREEN}✓${NC} Backend service is running"
else
    echo -e "${RED}✗${NC} Backend service is NOT running. Starting it..."
    sudo systemctl start noc-configmaker
    sleep 3
    if sudo systemctl is-active --quiet noc-configmaker; then
        echo -e "${GREEN}✓${NC} Backend service started"
    else
        echo -e "${RED}✗${NC} Failed to start backend. Checking logs:"
        sudo journalctl -u noc-configmaker -n 20 --no-pager
        exit 1
    fi
fi

# 2. Check if Flask is responding
echo -e "${YELLOW}[2] Testing Flask backend on port 5000...${NC}"
if curl -s http://127.0.0.1:5000/ | grep -q "NOC-configMaker\|login"; then
    echo -e "${GREEN}✓${NC} Flask backend is responding"
else
    echo -e "${RED}✗${NC} Flask backend is not responding on port 5000"
    echo "Checking if port 5000 is listening:"
    sudo netstat -tlnp | grep 5000 || sudo ss -tlnp | grep 5000
    exit 1
fi

# 3. Remove default Nginx config
echo -e "${YELLOW}[3] Removing default Nginx config...${NC}"
sudo rm -f /etc/nginx/sites-enabled/default
echo -e "${GREEN}✓${NC} Default config removed"

# 4. Create correct Nginx config (HTTP only, no SSL)
echo -e "${YELLOW}[4] Creating Nginx config...${NC}"
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

# 5. Enable the config
echo -e "${YELLOW}[5] Enabling Nginx config...${NC}"
sudo ln -sf /etc/nginx/sites-available/noc-configmaker-domain /etc/nginx/sites-enabled/
echo -e "${GREEN}✓${NC} Config enabled"

# 6. Test and reload Nginx
echo -e "${YELLOW}[6] Testing Nginx config...${NC}"
if sudo nginx -t; then
    echo -e "${GREEN}✓${NC} Nginx config is valid"
    sudo systemctl reload nginx
    echo -e "${GREEN}✓${NC} Nginx reloaded"
else
    echo -e "${RED}✗${NC} Nginx config error!"
    sudo nginx -t
    exit 1
fi

# 7. Test the proxy
echo -e "${YELLOW}[7] Testing proxy...${NC}"
sleep 2
if curl -s http://127.0.0.1/ | grep -q "NOC-configMaker\|login"; then
    echo -e "${GREEN}✓${NC} Proxy is working!"
else
    echo -e "${RED}✗${NC} Proxy test failed"
    echo "Testing direct backend:"
    curl -s http://127.0.0.1:5000/ | head -20
    echo ""
    echo "Testing through Nginx:"
    curl -s http://127.0.0.1/ | head -20
fi

echo ""
echo "=========================================="
echo -e "${GREEN}Fix Complete!${NC}"
echo "=========================================="
echo ""
echo "Access your application at:"
echo -e "  ${GREEN}http://noc-configmaker.nxlink.com${NC}"
echo -e "  ${GREEN}http://192.168.11.118${NC}"
echo ""
echo "Backend status:"
sudo systemctl status noc-configmaker --no-pager -l | head -10
echo ""
echo "=========================================="
