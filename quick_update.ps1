#!/usr/bin/env pwsh
# Quick Update Script - Deploy key files to VM
# Usage: .\quick_update.ps1

$VM_IP = "192.168.11.118"
$VM_USER = "whamza"
$VM_PATH = "/home/whamza/noc-configmaker"  # Adjust this path if needed

Write-Host "================================" -ForegroundColor Cyan
Write-Host "NOC Config Maker - Quick Update" -ForegroundColor Cyan
Write-Host "================================" -ForegroundColor Cyan
Write-Host ""

# IMPORTANT:
# - Source of truth for the VM is `vm_deployment/`
# - Repo root `api_server.py` is a compatibility shim for local dev; don't deploy it to the VM

Write-Host "[1/2] Uploading files to VM ($VM_IP)..." -ForegroundColor Yellow

$uploads = @(
    @{ Local = "vm_deployment/api_server.py"; Remote = "$VM_PATH/api_server.py" },
    @{ Local = "vm_deployment/NOC-configMaker.html"; Remote = "$VM_PATH/NOC-configMaker.html" },
    @{ Local = "vm_deployment/login.html"; Remote = "$VM_PATH/login.html" },
    @{ Local = "vm_deployment/change-password.html"; Remote = "$VM_PATH/change-password.html" },
    @{ Local = "vm_deployment/nextlink_standards.py"; Remote = "$VM_PATH/nextlink_standards.py" },
    @{ Local = "vm_deployment/nextlink_enterprise_reference.py"; Remote = "$VM_PATH/nextlink_enterprise_reference.py" },
    @{ Local = "vm_deployment/nextlink_compliance_reference.py"; Remote = "$VM_PATH/nextlink_compliance_reference.py" },
    @{ Local = "requirements.txt"; Remote = "$VM_PATH/requirements.txt" }
)

foreach ($u in $uploads) {
    if (-not (Test-Path $u.Local)) {
        Write-Host "[WARN] Missing local file: $($u.Local)" -ForegroundColor Yellow
        continue
    }
    Write-Host "Uploading $($u.Local) -> $($u.Remote)" -ForegroundColor Gray
    scp $u.Local "$VM_USER@$VM_IP:$($u.Remote)"
    if ($LASTEXITCODE -ne 0) { break }
}

if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] Upload failed - Check VM path and credentials" -ForegroundColor Red
    Write-Host "Verify path: ssh $VM_USER@$VM_IP 'ls -la $VM_PATH'" -ForegroundColor Gray
    exit 1
}

Write-Host "[OK] Upload complete" -ForegroundColor Green

Write-Host ""
Write-Host "[2/2] Restarting service on VM..." -ForegroundColor Yellow
ssh "$VM_USER@$VM_IP" "cd $VM_PATH && sudo systemctl restart noc-configmaker || (pkill -f api_server.py; nohup python3 api_server.py > nohup.out 2>&1 &)"

if ($LASTEXITCODE -eq 0) {
    Write-Host "[OK] Service restarted" -ForegroundColor Green
} else {
    Write-Host "[WARN] Could not restart service automatically" -ForegroundColor Yellow
    Write-Host "Manual restart:" -ForegroundColor Gray
    Write-Host "  ssh $VM_USER@$VM_IP" -ForegroundColor Gray
    Write-Host "  cd $VM_PATH" -ForegroundColor Gray
    Write-Host "  sudo systemctl restart noc-configmaker" -ForegroundColor Gray
}

Write-Host ""
Write-Host "================================" -ForegroundColor Cyan
Write-Host "Update Complete" -ForegroundColor Green
Write-Host "================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Test:" -ForegroundColor Yellow
Write-Host "  http://$VM_IP:5000/api/health" -ForegroundColor Cyan
Write-Host "  http://$VM_IP:8000/NOC-configMaker.html" -ForegroundColor Cyan
Write-Host ""
