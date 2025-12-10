#!/usr/bin/env pwsh
# Quick Update Script - Deploy only changed files to VM
# Usage: .\quick_update.ps1

$VM_IP = "192.168.11.118"
$VM_USER = "whamza"
$VM_PATH = "/home/whamza/noc-configmaker"  # Adjust this path if needed

Write-Host "================================" -ForegroundColor Cyan
Write-Host "NOC Config Maker - Quick Update" -ForegroundColor Cyan
Write-Host "================================" -ForegroundColor Cyan
Write-Host ""

# Step 1: Copy files to vm_deployment folder
Write-Host "[1/3] Copying files to vm_deployment..." -ForegroundColor Yellow
Copy-Item -Path "api_server.py" -Destination "vm_deployment\api_server.py" -Force
Copy-Item -Path "NOC-configMaker.html" -Destination "vm_deployment\NOC-configMaker.html" -Force
Write-Host "✓ Files copied to vm_deployment" -ForegroundColor Green

# Step 2: SCP files to VM
Write-Host ""
Write-Host "[2/3] Uploading to VM ($VM_IP)..." -ForegroundColor Yellow
Write-Host "Uploading api_server.py..." -ForegroundColor Gray
scp vm_deployment/api_server.py ${VM_USER}@${VM_IP}:${VM_PATH}/

Write-Host "Uploading NOC-configMaker.html..." -ForegroundColor Gray
scp vm_deployment/NOC-configMaker.html ${VM_USER}@${VM_IP}:${VM_PATH}/

if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ Files uploaded successfully" -ForegroundColor Green
} else {
    Write-Host "✗ Upload failed - Check VM path and credentials" -ForegroundColor Red
    Write-Host ""
    Write-Host "Troubleshooting:" -ForegroundColor Yellow
    Write-Host "1. Verify VM path exists: ssh ${VM_USER}@${VM_IP} 'ls -la ${VM_PATH}'" -ForegroundColor Gray
    Write-Host "2. If path doesn't exist, update VM_PATH variable in this script" -ForegroundColor Gray
    exit 1
}

# Step 3: Restart service on VM
Write-Host ""
Write-Host "[3/3] Restarting service on VM..." -ForegroundColor Yellow
ssh ${VM_USER}@${VM_IP} "cd ${VM_PATH} && sudo systemctl restart noc-configmaker || (pkill -f api_server.py; nohup python3 api_server.py > nohup.out 2>&1 &)"

if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ Service restarted" -ForegroundColor Green
} else {
    Write-Host "⚠ Could not restart service automatically" -ForegroundColor Yellow
    Write-Host "Manual restart command:" -ForegroundColor Gray
    Write-Host "  ssh ${VM_USER}@${VM_IP}" -ForegroundColor Gray
    Write-Host "  cd ${VM_PATH}" -ForegroundColor Gray
    Write-Host "  sudo systemctl restart noc-configmaker" -ForegroundColor Gray
}

Write-Host ""
Write-Host "================================" -ForegroundColor Cyan
Write-Host "✅ Update Complete!" -ForegroundColor Green
Write-Host "================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Test the changes:" -ForegroundColor Yellow
Write-Host "  http://${VM_IP}:5000/app" -ForegroundColor Cyan
Write-Host ""
