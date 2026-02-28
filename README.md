# NOC Config Maker

> **Intelligent Network Configuration Generator for Nextlink Internet**  
> Automate MikroTik RouterOS configurations with AI-powered validation and compliance checking

[![Testing consistency](https://img.shields.io/badge/status-Testing%20consistency-brightgreen)]()
[![Version](https://img.shields.io/badge/version-2.0-blue)]()
[![License](https://img.shields.io/badge/license-proprietary-red)]()

---

## 📖 Table of Contents

- [The Problem](#-the-problem)
- [Our Solution](#-our-solution)
- [Key Features](#-key-features)
- [Quick Start](#-quick-start)
- [Best Practices](#-best-practices)
- [Step-by-Step Usage Guide](#-step-by-step-usage-guide)
- [Architecture](#-architecture)
- [Deployment](#-deployment)
- [Documentation](#-documentation)
- [Support](#-support)

---

## 🔴 The Problem

### Manual Configuration Challenges

Network operations teams face significant challenges when configuring MikroTik routers:

#### 1. **Time-Consuming Manual Work**
- Each router configuration takes 30-60 minutes to create manually
- Copy-paste errors lead to misconfigurations
- Inconsistent naming conventions across sites
- Repetitive work for similar deployments

#### 2. **Human Error & Inconsistency**
- Typos in IP addresses, VLAN IDs, or interface names
- Forgotten firewall rules or security policies
- Inconsistent OSPF/BGP configurations
- Missing compliance requirements

#### 3. **Version Compatibility Issues**
- RouterOS v6 vs v7 syntax differences
- Speed syntax changes (`10G-baseSR` vs `10G-baseSR-LR`)
- Interface naming variations across device models
- Migration complexity when upgrading firmware

#### 4. **Knowledge Silos**
- Configuration expertise locked in individual engineers' heads
- No standardized templates or policies
- Difficult onboarding for new team members
- Lack of configuration history and audit trail

#### 5. **Compliance & Validation**
- No automated compliance checking
- Manual verification of security policies
- Difficult to enforce organizational standards
- No validation before deployment

### Real-World Impact

- **Deployment Time**: 30-60 minutes per router → **2-3 minutes**
- **Error Rate**: ~15% manual errors → **<1% with validation**
- **Consistency**: Variable → **100% standardized**
- **Knowledge Transfer**: Weeks → **Minutes** (built-in templates)

---

## ✅ Our Solution

### NOC Config Maker: Intelligent Automation Platform

A unified web application that generates production-ready MikroTik RouterOS configurations with:

#### 1. **Template-Driven Generation**
- Pre-built templates for 7 common deployment scenarios
- Automatic syntax conversion for RouterOS v6/v7
- Device-specific interface mappings (CCR1036, CCR2004, CCR2116, CCR2216)
- State-specific OSPF area configurations

#### 2. **AI-Powered Validation**
- Real-time configuration analysis
- Compliance checking against organizational policies
- Security best practice verification
- Syntax error detection before deployment

#### 3. **Standardization & Consistency**
- Universal port assignment policies
- Consistent naming conventions
- Standardized VLAN configurations
- Enforced security policies

#### 4. **Knowledge Management**
- All configurations saved to database
- Searchable history by site, device, date
- Built-in documentation and tooltips
- Live activity feed showing team actions

#### 5. **Migration Automation**
- One-click RouterOS v6 → v7 migration
- Automatic syntax conversion
- Nokia migration support (in development)
- Bulk configuration updates

### How It Works

```
User Input → Template Selection → AI Validation → Generated Config → Deploy
    ↓              ↓                    ↓                ↓             ↓
Site Info    Tower/Enterprise    Compliance Check   Download .rsc   SSH/Winbox
Device Type  MPLS/Non-MPLS      Security Policies   Save to DB     Apply Config
RouterOS Ver Interface Mapping   Syntax Validation   Audit Trail    Verify
```

---

## 🚀 Key Features

### Configuration Generators (7 Types)

| Generator | Use Case | Production Ready |
|-----------|----------|------------------|
| **🗼 Tower Config** | Full BGP/OSPF/MPLS tower routers with multi-sector support | ✅ Yes |
| **🏢 Non-MPLS Enterprise** | Simplified enterprise customers without MPLS | ✅ Yes |
| **🏢 MPLS Enterprise** | Enterprise sites with MPLS/OSPF/BGP support | ✅ Yes |
| **📡 Tarana Sectors** | ALPHA/BETA/GAMMA/DELTA sector configuration | ✅ Yes |
| **🌐 Enterprise Feeding** | Commercial/enterprise uplink provisioning | ✅ Yes |
| **📡 6GHz Switch Port** | 6GHz switch configuration with VLAN 3000/4000 | ✅ Yes |
| **🔄 Migration/Upgrade** | RouterOS v6 → v7 automation | ✅ Yes |

### Modern Dashboard

- **Live Metrics**: Total configs, migrations, success rate, today's activity
- **Activity Feed**: Real-time view of team's configuration work
- **Quick Actions**: One-click access to common tasks
- **Dark Mode**: Easy on the eyes during late-night deployments

### Intelligent Features

- ✅ **Auto-Syntax Conversion**: RouterOS v6 ↔ v7
- ✅ **Device Detection**: Automatic interface mapping for CCR models
- ✅ **Compliance Checking**: Enforces organizational policies
- ✅ **Persistent Storage**: All configs saved to database
- ✅ **Feedback System**: Built-in bug reporting and feature requests
- ✅ **Multi-User Support**: Track who generated what and when

---

## 🏁 Quick Start

### Option 1: For End Users (Recommended)

**Using the Executable (No Python Required)**

1. **Download the latest release**:
   ```bash
   # Get NOC-ConfigMaker.exe from releases
   ```

2. **Run the application**:
   ```bash
   # Double-click NOC-ConfigMaker.exe
   # Or from command line:
   NOC-ConfigMaker.exe
   ```

3. **Access the web interface**:
   - Browser opens automatically to `http://localhost:8000`
   - Login with your email (default password is set via `DEFAULT_PASSWORD` in `.env`)
   - Change password on first login

### Option 2: For Developers

**Running from Source**

1. **Clone the repository**:
   ```bash
   git clone https://github.com/NX-Whamza/noc-configmaker.git
   cd noc-configmaker
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Start the server**:
   ```bash
   uvicorn --app-dir vm_deployment fastapi_server:app --host 0.0.0.0 --port 5000
   ```

4. **Access the application**:
   - Navigate to `http://localhost:5000`
   - Login and start generating configs

### Option 3: Production VM Deployment

See [Deployment Guide](#-deployment) below for complete VM setup instructions.

### Option 4: Docker (Recommended for VM Consistency)

1. **Start containers** (frontend on `:8000`, backend behind `/api`):
   ```bash
   docker compose up -d --build
   ```

2. **Open UI**:
   - `http://localhost:8000`

---

## 📋 Best Practices

### 1. Configuration Generation

#### ✅ DO:
- **Always review generated configs** before deploying to production
- **Use the AI validation** feature to catch potential issues
- **Save configs to database** for audit trail and future reference
- **Test configs in lab environment** first when possible
- **Document any manual changes** made after generation

#### ❌ DON'T:
- Deploy configs without reviewing them
- Skip the validation step
- Forget to update site information (coordinates, contact info)
- Use outdated RouterOS versions without testing
- Ignore warning messages from the validator

### 2. Site Information

#### Required Information Checklist:
- [ ] **Site Name**: Use consistent naming (e.g., `CHICAGO-TOWER-01`)
- [ ] **Device Model**: CCR1036, CCR2004, CCR2116, or CCR2216
- [ ] **RouterOS Version**: Target version (6.x or 7.x)
- [ ] **Router ID**: Unique loopback IP (e.g., `10.2.0.123`)
- [ ] **Coordinates**: Latitude/Longitude for tower sites
- [ ] **OSPF Area**: Correct area for your region
- [ ] **BGP Peers**: If applicable

### 3. Security

#### Essential Security Practices:
- **Change default password** on first login
- **Use strong passwords** (minimum 12 characters)
- **Review feedback** in the **ADMIN** panel (admin users only)
- **Review firewall rules** in generated configs
- **Verify SNMP community strings** are updated
- **Check shared keys** for VPLS/MPLS tunnels

### 4. Deployment Workflow

#### Recommended Process:

```
1. Gather Site Information
   ↓
2. Generate Configuration
   ↓
3. AI Validation Check
   ↓
4. Manual Review
   ↓
5. Lab Testing (if possible)
   ↓
6. Deploy to Production
   ↓
7. Verify Connectivity
   ↓
8. Save to Database
```

### 5. Version Control

- **Save all configs** to the database via the tool
- **Export configs** as `.rsc` files for backup
- **Document changes** in the feedback system
- **Track who generated what** using the activity feed

### 6. Team Collaboration

- **Use the activity feed** to see what teammates are working on
- **Submit feedback** for bugs or feature requests
- **Share best practices** via the feedback system
- **Review configs** generated by team members for learning

---

## 📚 Step-by-Step Usage Guide

### Scenario 1: Generating a Tower Configuration

#### Step 1: Login
1. Navigate to `http://localhost:8000` (or your VM URL)
2. Enter your email and password
3. Click **LOGIN**

#### Step 2: Navigate to Tower Config
1. Click **MIKROTIK CONFIG** dropdown in navigation
2. Select **🗼 Tower Config**

#### Step 3: Fill Out Site Information

**Basic Information:**
```
Site Name: CHICAGO-TOWER-01
System Identity: RTR-CCR2004-1.CHICAGO-TOWER-01
Device Model: CCR2004-1G-12S+2XS
RouterOS Version: 7.16.2
```

**Network Configuration:**
```
Router ID: 10.2.0.150
LAN Bridge IP: 10.25.150.1/24
NAT Public IP: 203.0.113.50
```

**Location:**
```
Latitude: 41.8781
Longitude: -87.6298
```

**Routing:**
```
OSPF Area: backbone-v2
BGP AS: 26077
BGP Peers: [{"name":"CR7","remote":"10.2.0.107/32"}]
```

#### Step 4: Configure Features

**Enable Optional Features:**
- ☑ Enable Tarana Ports (if applicable)
- ☑ Enable SWT (VLAN 4000)
- ☑ Enable VPLS Tunnels
- ☑ Enable MPLS/LDP
- ☐ Enable DHCP Server (only for backbone-v2)

**Configure Tarana Sectors** (if enabled):
```
ALPHA: sfp-sfpplus6, 10G-baseSR-LR, MTU 1500
BETA: sfp-sfpplus7, 10G-baseSR-LR, MTU 1500
GAMMA: sfp-sfpplus8, 10G-baseSR-LR, MTU 1500
DELTA: sfp-sfpplus9, 10G-baseSR-LR, MTU 1500
```

#### Step 5: Generate Configuration
1. Click **🔧 GENERATE CONFIG** button
2. Wait for generation (2-5 seconds)
3. Review the generated configuration in the output box

#### Step 6: AI Validation (Recommended)
1. Click **🤖 VALIDATE WITH AI** button
2. Review validation results
3. Address any warnings or errors

#### Step 7: Download and Deploy
1. Click **💾 DOWNLOAD CONFIG** button
2. Save as `CHICAGO-TOWER-01.rsc`
3. Upload to router via Winbox or SSH:
   ```bash
   scp CHICAGO-TOWER-01.rsc admin@router-ip:/
   ssh admin@router-ip
   /import file-name=CHICAGO-TOWER-01.rsc
   ```

#### Step 8: Verify
1. Check OSPF neighbors: `/routing ospf neighbor print`
2. Check BGP status: `/routing bgp peer print`
3. Verify interfaces: `/interface print`
4. Test connectivity

---

### Scenario 2: Migrating RouterOS v6 → v7

#### Step 1: Export Current Config
```bash
# On RouterOS v6 router
/export file=old-config-v6
```

#### Step 2: Navigate to Migration Tool
1. Click **NOKIA CONFIG** dropdown
2. Select **🔄 NOKIA MIGRATION** for Migrating to Nokia
3. Or use the **Migration/Upgrade** tab when you upgrading a Mikrotik router to a new routerboard/ Firmware

#### Step 3: Upload Config
1. Click **Choose File** button
2. Select your `old-config-v6.rsc` file
3. Click **Upload**

#### Step 4: Configure Migration
```
Source Version: 6.49.2
Target Version: 7.16.2
Device Model: CCR2004-1G-12S+2XS
```

#### Step 5: Generate Migrated Config
1. Click **🔄 MIGRATE CONFIG** button
2. Review syntax changes highlighted in output
3. Pay special attention to:
   - Speed syntax changes
   - Interface naming updates
   - Deprecated commands

#### Step 6: Validate
1. Click **🤖 VALIDATE WITH AI**
2. Review compatibility warnings
3. Test in lab environment first

#### Step 7: Deploy
1. Backup current config: `/export file=backup-before-upgrade`
2. Upgrade RouterOS: `/system package update download`
3. Reboot router
4. Import migrated config: `/import file=migrated-config-v7.rsc`

---

### Scenario 3: Enterprise Customer Setup

#### Step 1: Choose Config Type
- **Non-MPLS Enterprise**: For simple enterprise customers
- **MPLS Enterprise**: For customers requiring MPLS connectivity

#### Step 2: Fill Out Customer Information
```
Site Name: ACME-CORP-MAIN
Customer Name: ACME Corporation
Device Model: CCR2004-1G-12S+2XS
RouterOS Version: 7.16.2
```

#### Step 3: Network Configuration
```
Router ID: 10.2.0.200
WAN Interface: ether1
WAN IP: 203.0.113.100/30
LAN Network: 192.168.100.0/24
```

#### Step 4: Configure Services
- ☑ NAT (if required)
- ☑ Firewall rules
- ☑ DHCP server (if managing LAN)
- ☐ MPLS (only for MPLS Enterprise)

#### Step 5: Generate and Deploy
Follow steps 5-8 from Scenario 1

---

## 🏗️ Architecture

### System Components

```
┌─────────────────────────────────────────────────────────────┐
│                     NOC Config Maker                        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────┐      ┌──────────────┐      ┌──────────┐ │
│  │   Frontend   │◄────►│   Backend    │◄────►│ Database │ │
│  │              │      │              │      │          │ │
│  │ HTML/JS/CSS  │      │ Flask API    │      │ SQLite   │ │
│  │ Dashboard    │      │ Python       │      │ Configs  │ │
│  │ Forms        │      │ AI Engine    │      │ Activity │ │
│  └──────────────┘      └──────────────┘      └──────────┘ │
│         │                     │                     │      │
│         │                     │                     │      │
│         ▼                     ▼                     ▼      │
│  ┌──────────────────────────────────────────────────────┐ │
│  │           Configuration Policies & Standards         │ │
│  │  • nextlink_standards.py                            │ │
│  │  • nextlink_enterprise_reference.py                 │ │
│  │  • nextlink_compliance_reference.py                 │ │
│  │  • config_policies/*.md                             │ │
│  └──────────────────────────────────────────────────────┘ │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Technology Stack

- **Frontend**: HTML5, JavaScript (ES6+), CSS3
- **Backend**: Python 3.10+, Flask
- **Database**: SQLite (portable, no setup required)
- **Authentication**: JWT tokens, bcrypt password hashing
- **Packaging**: PyInstaller (standalone executable)

### File Structure

```
noc-configmaker/
├── api_server.py                 # Backend API server
├── NOC-configMaker.html          # Main application UI
├── login.html                    # Authentication page
├── change-password.html          # Password management
├── launcher.py                   # Application entry point
├── build_exe.py                  # Executable builder
│
├── nextlink_standards.py         # RouterOS policies
├── nextlink_enterprise_reference.py  # Enterprise templates
├── nextlink_compliance_reference.py  # Compliance rules
│
├── config_policies/              # Policy documentation
│   ├── POLICY_INDEX.md
│   └── nextlink/
│       ├── router-interface-policy.md
│       └── ...
│
├── secure_data/                  # Runtime data (not in repo)
│   ├── users.db                  # User accounts
│   ├── completed_configs.db      # Config history
│   ├── activity_log.db           # Activity tracking
│   └── feedback.db               # User feedback
│
├── vm_deployment/                # VM deployment files
│   ├── NOC-configMaker.html
│   ├── login.html
│   ├── api_server.py
│   └── ...
│
└── docs/                         # Documentation
    ├── COMPLETE_DOCUMENTATION.md
    ├── QUICK_START_EXE.md
    └── SECURITY_SETUP.md
```

---

## 🌐 Deployment

### Local Development

```bash
# 1. Clone repository
git clone https://github.com/NX-Whamza/noc-configmaker.git
cd noc-configmaker

# 2. Install dependencies
pip install -r requirements.txt

# 3. Start server
python api_server.py

# 4. Access application
# http://localhost:5000
```

### Production VM Deployment

#### Prerequisites
- **VM**: Windows Server 2019+ or Ubuntu 22.04 LTS
- **CPU**: 4 vCPUs
- **RAM**: 4-8 GB
- **Disk**: 20 GB SSD
- **Network**: Ports 5000 (API) and 8000 (Web) open
- **DNS**: Domain name (e.g., `config.nxlink.com`)

#### Deployment Steps

**1. Package Application**
```powershell
# On development machine
.\transfer_all.ps1
```

**2. Transfer to VM**
```bash
# Files are automatically transferred via SCP
# Or manually:
scp noc-configmaker-vm-*.tar.gz user@vm:/opt/noc/
```

**3. Extract on VM**
```bash
cd /opt/noc
tar -xzf noc-configmaker-vm-*.tar.gz
```

**4. Configure Environment**
```bash
# Create .env file (optional)
cat > .env << EOF
ADMIN_EMAILS=netops@team.nxlink.com,whamza@team.nxlink.com
AI_PROVIDER=openai
# NEXTLINK_SSH_USERNAME=
# NEXTLINK_SSH_PASSWORD=
# BASE_CONFIG_PATH=/opt/base_configs
EOF
```

**5. Start Service**
```bash
# Option A: Run directly
uvicorn --app-dir vm_deployment fastapi_server:app --host 0.0.0.0 --port 5000

# Option B: As systemd service (Linux)
sudo systemctl start noc-configmaker
sudo systemctl enable noc-configmaker

# Option C: As Windows service
nssm install NOCConfigMaker "C:\NOC\NOC-ConfigMaker.exe"
nssm start NOCConfigMaker
```

**6. Configure Reverse Proxy**

**Nginx Example:**
```nginx
server {
    listen 80;
    server_name config.nxlink.com;

    location / {
        proxy_pass http://localhost:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

**IIS Example:**
```xml
<rewrite>
    <rules>
        <rule name="ReverseProxyInboundRule1" stopProcessing="true">
            <match url="(.*)" />
            <action type="Rewrite" url="http://localhost:5000/{R:1}" />
        </rule>
    </rules>
</rewrite>
```

**7. Verify Deployment**
```bash
# Check service status
curl http://localhost:5000/api/health

# Access via domain
https://config.nxlink.com
```

### Updating Production

```bash
# 1. Package new version
.\transfer_all.ps1

# 2. Deploy to VM
ssh user@vm
cd /opt/noc
tar -xzf noc-configmaker-vm-*.tar.gz

# 3. Restart service
sudo systemctl restart noc-configmaker

# 4. Verify
curl http://localhost:5000/api/health
```

---

## 📚 Documentation

| Document | Purpose |
|----------|---------|
| [Complete Documentation](docs/COMPLETE_DOCUMENTATION.md) | Full system documentation |
| [Quick Start (EXE)](docs/QUICK_START_EXE.md) | End-user guide for executable |
| [Security Setup](docs/SECURITY_SETUP.md) | API keys, email, secrets configuration |
| [Policy Index](config_policies/POLICY_INDEX.md) | Configuration policies by state |
| [Router Interface Policy](config_policies/nextlink/router-interface-policy.md) | Universal port assignments |
| [CHANGELOG](CHANGELOG.md) | All updates and fixes |

---

## 🐛 Support

### Built-In Feedback System

1. Click **FEEDBACK** button in navigation
2. Choose type:
   - 💡 **Feedback**: General comments or suggestions
   - 🐛 **Bug Report**: Something isn't working
   - ✨ **Feature Request**: New functionality ideas
3. Fill out form with details
4. Submit (stored in local database; admins can review in the **ADMIN** panel)

### Contact

- **NOC Team**: [netops@team.nxlink.com](mailto:netops@team.nxlink.com)

### Common Issues

**Issue**: Can't login  
**Solution**: Default password is set via `DEFAULT_PASSWORD` in your `.env` file

**Issue**: Can’t access Admin panel  
**Solution**: Ensure your email is in `ADMIN_EMAILS` and you are logged in

**Issue**: AI validation not working  

**Issue**: Configs not saving  
**Solution**: Check `secure_data/` folder permissions

---

## 📝 License

**Proprietary** - Nextlink Internet Internal Use Only

---

## 🎉 Status

**Version**: 2.0 (Unified Backend Architecture)  
**Last Updated**: December 9, 2024  
**Status**: ✅ **PRODUCTION READY**

### What's Working
- ✅ All 7 configuration generators operational
- ✅ AI-powered validation functional
- ✅ Live tracking and metrics
- ✅ Feedback system with email notifications
- ✅ Multi-user authentication
- ✅ Database persistence
- ✅ VM deployment tested and documented
- ✅ Interface policies for all router models

### In Development
- 🚧 Nokia 7250 configuration generator
- 🚧 Nokia migration (MikroTik → Nokia syntax)
- 🚧 Bulk configuration updates
- 🚧 Advanced reporting and analytics

---

**Made with ❤️ by the Nextlink NOC Team**
