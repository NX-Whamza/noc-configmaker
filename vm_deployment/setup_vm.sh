#!/bin/bash
# NOC Config Maker - Ubuntu VM Setup Script
# This script sets up the NOC Config Maker on Ubuntu 24.04
# 
# USAGE:
#   1. Transfer files to VM: scp -r vm_deployment/* <user>@<vm-ip>:~/vm_deployment/
#   2. SSH into VM: ssh <user>@<vm-ip>
#   3. Run: cd ~/vm_deployment && bash setup_vm.sh
#   4. Start: sudo systemctl start noc-configmaker
#   5. Access: http://<vm-ip>:5000/NOC-configMaker.html

set -e  # Exit on error

echo "=========================================="
echo "NOC Config Maker - VM Setup"
echo "=========================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if running as root
if [ "$EUID" -eq 0 ]; then 
   echo -e "${RED}Please do not run as root. The script will use sudo when needed.${NC}"
   exit 1
fi

# Get current directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

echo -e "${GREEN}[1/7]${NC} Checking system requirements..."

# Check Python 3
if ! command -v python3 &> /dev/null; then
    echo -e "${YELLOW}Python 3 not found. Installing...${NC}"
    sudo apt update
    sudo apt install -y python3 python3-pip python3-venv
else
    echo -e "${GREEN}✓${NC} Python 3 found: $(python3 --version)"
fi

# Check pip
if ! command -v pip3 &> /dev/null; then
    echo -e "${YELLOW}pip3 not found. Installing...${NC}"
    sudo apt install -y python3-pip
else
    echo -e "${GREEN}✓${NC} pip3 found: $(pip3 --version)"
fi

echo -e "${GREEN}[2/7]${NC} Creating Python virtual environment..."

# Remove old venv if exists
if [ -d "venv" ]; then
    echo -e "${YELLOW}Removing existing virtual environment...${NC}"
    rm -rf venv
fi

# Create virtual environment
python3 -m venv venv
echo -e "${GREEN}✓${NC} Virtual environment created"

echo -e "${GREEN}[3/6]${NC} Installing Python dependencies..."

# Activate virtual environment
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip --quiet

# Install requirements
if [ -f "requirements.txt" ]; then
    echo "Installing packages from requirements.txt..."
    pip install -r requirements.txt
    echo -e "${GREEN}✓${NC} Dependencies installed"
else
    echo -e "${RED}✗${NC} requirements.txt not found!"
    exit 1
fi

# Verify critical packages
echo "Verifying installation..."
python3 -c "import flask; import paramiko; import requests; print('✓ Core packages verified')" || {
    echo -e "${RED}✗${NC} Package verification failed!"
    exit 1
}

echo -e "${GREEN}[4/7]${NC} Setting up configuration..."

# Create .env file (optional; loaded automatically if present)
if [ ! -f ".env" ]; then
    echo -e "${GREEN}✓${NC} Creating .env file..."
    cat > .env << EOF
ADMIN_EMAILS=netops@team.nxlink.com,whamza@team.nxlink.com
# JWT_SECRET=your-secret-here
# NEXTLINK_SSH_USERNAME=
# NEXTLINK_SSH_PASSWORD=
EOF
    echo -e "${GREEN}✓${NC} .env file created"
else
    echo -e "${GREEN}✓${NC} .env file already exists"
fi

# Secure .env file
chmod 600 .env
echo -e "${GREEN}✓${NC} Secured .env file permissions"

# Create secure_data directory if it doesn't exist
mkdir -p secure_data
chmod 700 secure_data
echo -e "${GREEN}✓${NC} Created secure_data directory"

echo -e "${GREEN}[5/7]${NC} Installing systemd service..."

# Check if service file exists
if [ ! -f "noc-configmaker.service" ]; then
    echo -e "${RED}✗${NC} noc-configmaker.service not found!"
    exit 1
fi

# Get absolute path for service file
ABS_PATH=$(pwd)
USER_NAME=$(whoami)

# Update service file with correct paths
sed "s|__INSTALL_DIR__|$ABS_PATH|g; s|__SERVICE_USER__|$USER_NAME|g" noc-configmaker.service > /tmp/noc-configmaker.service

# Copy service file
sudo cp /tmp/noc-configmaker.service /etc/systemd/system/noc-configmaker.service
sudo chmod 644 /etc/systemd/system/noc-configmaker.service

# Reload systemd
sudo systemctl daemon-reload
echo -e "${GREEN}✓${NC} Systemd service installed"

echo -e "${GREEN}[6/7]${NC} Finalizing service setup..."

# Enable service (but don't start yet - user will do that)
sudo systemctl enable noc-configmaker
echo -e "${GREEN}✓${NC} Service enabled (will start on boot)"

# Install and configure nginx reverse proxy
echo -e "${GREEN}[7/7]${NC} Setting up nginx reverse proxy..."

if ! command -v nginx &> /dev/null; then
    echo -e "${YELLOW}Installing nginx...${NC}"
    sudo apt update
    sudo apt install -y nginx
fi

# Create nginx config
ABS_PATH=$(pwd)
sudo tee /etc/nginx/sites-available/noc-configmaker > /dev/null <<EOF
server {
    listen 80;
    server_name 192.168.11.118;
    
    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        
        # WebSocket support (if needed)
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
EOF

# Enable site
sudo ln -sf /etc/nginx/sites-available/noc-configmaker /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default 2>/dev/null || true

# Test nginx config
sudo nginx -t
if [ $? -eq 0 ]; then
    sudo systemctl reload nginx
    sudo systemctl enable nginx
    echo -e "${GREEN}✓${NC} Nginx reverse proxy configured"
else
    echo -e "${RED}✗${NC} Nginx configuration error!"
fi

# Configure firewall
if command -v ufw &> /dev/null; then
    if sudo ufw status | grep -q "Status: active"; then
        echo -e "${YELLOW}Configuring firewall...${NC}"
        sudo ufw allow 80/tcp comment "NOC Config Maker" 2>/dev/null || true
        echo -e "${GREEN}✓${NC} Firewall configured (port 80 open)"
    fi
else
    echo -e "${GREEN}✓${NC} Firewall not active (ufw not installed)"
fi

echo ""
echo "=========================================="
echo -e "${GREEN}Setup Complete!${NC}"
echo "=========================================="
echo ""
echo "QUICK START:"
echo "  sudo systemctl start noc-configmaker"
echo "  sudo systemctl status noc-configmaker"
echo ""
echo "ACCESS:"
echo "  http://192.168.11.118"
echo ""
echo "MANAGE:"
echo "  Start:   sudo systemctl start noc-configmaker"
echo "  Stop:    sudo systemctl stop noc-configmaker"
echo "  Logs:    sudo journalctl -u noc-configmaker -f"
echo ""
echo "EMAIL (already configured in .env):"
echo "  Edit:    nano .env"
echo ""
echo "=========================================="
