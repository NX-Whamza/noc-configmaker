# Scripts Folder - Quick Reference

## CURRENT STATUS: Most scripts are OBSOLETE

**Reason**: The NOC ConfigMaker now has a **unified backend** (`api_server.py` + `launcher.py`) that handles everything automatically. The EXE auto-starts all services.

---

## ✅ USE THESE (Updated, Current)

### `QUICK_START.bat` (in root folder, NOT scripts/)
**Purpose**: Development launcher - Starts both backend + frontend  
**When to use**: When developing/testing locally  
**Location**: Root folder (not in scripts/)

### `build_exe.py` (in root folder)
**Purpose**: Build the distributable EXE  
**When to use**: After making code changes, rebuild EXE  
**Location**: Root folder

---

## ⚠️ LEGACY (Old, Kept for Reference Only)

### `start_backend_services.bat`
**Status**: OBSOLETE - Replaced by `QUICK_START.bat` in root  
**Old Purpose**: Started backend + Ollama + frontend separately  
**Why obsolete**: New launcher handles this automatically

### `deploy_ai_server.bat`
**Status**: OBSOLETE - AI is now integrated into api_server.py  
**Old Purpose**: Set up dedicated AI server PC  
**Why obsolete**: Backend is unified, AI is built-in

### `build_exe.bat`
**Status**: OBSOLETE - Use `python build_exe.py` instead  
**Old Purpose**: Build EXE with batch wrapper  
**Why obsolete**: Direct Python script is cleaner

### `setup_ollama.bat`
**Status**: REFERENCE ONLY - Manual Ollama installation  
**Old Purpose**: Install and configure Ollama  
**Why kept**: Useful for first-time Ollama setup

### `install_fast_model.bat` / `install_phi3.bat`
**Status**: REFERENCE ONLY  
**Purpose**: Quick install specific Ollama models  
**Why kept**: Useful shortcuts for model installation

### GitHub Scripts
- `setup_github.bat`
- `push_to_github.bat`
**Status**: REFERENCE ONLY - Use git commands directly

### Network Scripts
- `setup_network_access.bat`
**Status**: REFERENCE ONLY - Windows Firewall rules  
**Why kept**: Useful for LAN deployment

---

## 🎯 FOR END USERS

**Just run**: `NOC-ConfigMaker.exe`  
Everything auto-starts:
- Backend API (port 5000)
- Frontend UI (port 8000)
- Browser opens automatically

**No scripts needed!**

---

## 🛠️ FOR DEVELOPERS

### Daily Development:
```bash
# Option 1: Quick start
QUICK_START.bat

# Option 2: Manual Python
python launcher.py
```

### After Code Changes:
```bash
# Rebuild EXE
python build_exe.py
```

### Install Ollama (one-time):
```bash
# Download from: https://ollama.com/download
# Or use: scripts/setup_ollama.bat
```

### Install AI Model (one-time):
```bash
ollama pull phi3:mini
# Or: ollama pull qwen2.5-coder:7b
```

---

## Summary

| Script | Status | Use |
|--------|--------|-----|
| `QUICK_START.bat` (root) | ✅ CURRENT | Dev launcher |
| `build_exe.py` (root) | ✅ CURRENT | Build EXE |
| `start_backend_services.bat` | ❌ OBSOLETE | Don't use |
| `deploy_ai_server.bat` | ❌ OBSOLETE | Don't use |
| `build_exe.bat` | ❌ OBSOLETE | Don't use |
| `setup_ollama.bat` | 📖 REFERENCE | First-time Ollama setup |
| `install_*.bat` | 📖 REFERENCE | Model installers |
| Network/GitHub scripts | 📖 REFERENCE | Useful for specific tasks |

**Bottom Line**: Most scripts are obsolete. Use `QUICK_START.bat` for dev, `python build_exe.py` for builds, or just run the EXE for production.


