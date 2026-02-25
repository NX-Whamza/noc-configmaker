# NOC Config Maker - Documentation

## 📚 Documentation Index

This folder contains all documentation for the NOC Config Maker tool.

---

## 🚀 Quick Start Guides

| Document | Purpose | Audience |
|----------|---------|----------|
| [QUICK_START_EXE.md](QUICK_START_EXE.md) | How to run the executable | End users |
| [../QUICK_START_VM.md](../QUICK_START_VM.md) | How to deploy to VM | IT team |
| [../README.md](../README.md) | Project overview | Everyone |

---

## 📖 Complete Guides

| Document | Purpose |
|----------|---------|
| [COMPLETE_DOCUMENTATION.md](COMPLETE_DOCUMENTATION.md) | Full system documentation |
| [SECURITY_SETUP.md](SECURITY_SETUP.md) | Email, API keys, secrets configuration |
| [DISTRIBUTION_GUIDE.md](DISTRIBUTION_GUIDE.md) | How to distribute to users |
| [NOC_CONFIG_SUITE_SOP.md](NOC_CONFIG_SUITE_SOP.md) | Operational SOP for day-to-day tool usage |
| [UAT_VM_DEPLOYMENT_RUNBOOK.md](UAT_VM_DEPLOYMENT_RUNBOOK.md) | Deploy UAT/dev URL on same VM |

---

## 🔧 Configuration Policies

Located in `../config_policies/`:
- [POLICY_INDEX.md](../config_policies/POLICY_INDEX.md) - Index of all policies
- [router-interface-policy.md](../config_policies/nextlink/router-interface-policy.md) - Universal port assignments
- State-specific policies (Texas, Illinois, Kansas)

---

## 📝 Project Documentation

| Document | Purpose |
|----------|---------|
| [../CHANGELOG.md](../CHANGELOG.md) | Version history and updates |
| [../PRODUCTION_READY_SUMMARY.md](../PRODUCTION_READY_SUMMARY.md) | Production deployment guide |
| [../ENV_TEMPLATE.txt](../ENV_TEMPLATE.txt) | Environment configuration template |

---

## 📂 Document Organization

```
noc-configmaker/
├── README.md                          ← Start here
├── QUICK_START_VM.md                  ← For IT deployment
├── PRODUCTION_READY_SUMMARY.md        ← Production checklist
├── CHANGELOG.md                       ← What changed
├── ENV_TEMPLATE.txt                   ← Configuration template
│
├── docs/                              ← You are here
│   ├── README.md                      ← This file
│   ├── QUICK_START_EXE.md            ← Run the exe
│   ├── COMPLETE_DOCUMENTATION.md      ← Full docs
│   ├── SECURITY_SETUP.md              ← Secrets/API keys
│   └── DISTRIBUTION_GUIDE.md          ← Share with users
│
└── config_policies/                   ← RouterOS policies
    ├── POLICY_INDEX.md                ← Policy directory
    ├── README.md                      ← Policy overview
    ├── USAGE.md                       ← How to use policies
    └── nextlink/                      ← Nextlink-specific
        ├── router-interface-policy.md  ← Port assignments
        ├── texas-in-statepolicy.md     ← TX policy
        ├── illinois-out-of-state-mpls-config-policy.md
        └── kansas-out-of-state-mpls-config-policy.md
```

---

## 🎯 Which Document Do I Need?

### I want to run the tool locally
→ [QUICK_START_EXE.md](QUICK_START_EXE.md)

### I'm deploying to a VM
→ [../QUICK_START_VM.md](../QUICK_START_VM.md)

### I need complete documentation
→ [COMPLETE_DOCUMENTATION.md](COMPLETE_DOCUMENTATION.md)

### I'm setting up email/API keys
→ [SECURITY_SETUP.md](SECURITY_SETUP.md)

### I want to know what changed
→ [../CHANGELOG.md](../CHANGELOG.md)

### I'm checking if it's production ready
→ [../PRODUCTION_READY_SUMMARY.md](../PRODUCTION_READY_SUMMARY.md)

### I need router interface policies
→ [../config_policies/nextlink/router-interface-policy.md](../config_policies/nextlink/router-interface-policy.md)

---

## ✅ All Documents Are Up-To-Date

Last updated: November 27, 2024

All documentation reflects the current production-ready state of the tool.

