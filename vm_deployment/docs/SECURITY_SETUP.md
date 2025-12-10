# Security Configuration Guide

## 🔒 Proprietary Information Protection

This document outlines security measures to protect NextLink proprietary information.

## Required Environment Variables

### RADIUS Secret Configuration

**IMPORTANT**: The RADIUS secret is NO LONGER hardcoded. It should be set as an environment variable for production use.

**Note**: If the environment variable is not set, the system will use a placeholder (`CHANGE_ME_RADIUS_SECRET`) and display a warning. This allows the system to function, but you **MUST** replace the placeholder with the actual secret before deploying configurations.

#### Windows (PowerShell):
```powershell
$env:NEXTLINK_RADIUS_SECRET="your_radius_secret_here"
```

#### Windows (Command Prompt):
```cmd
set NEXTLINK_RADIUS_SECRET=your_radius_secret_here
```

#### Linux/macOS:
```bash
export NEXTLINK_RADIUS_SECRET="your_radius_secret_here"
```

#### Permanent Setup (Windows):
1. Open System Properties → Environment Variables
2. Add new User/System variable:
   - Name: `NEXTLINK_RADIUS_SECRET`
   - Value: `your_radius_secret_here`

#### Permanent Setup (Linux/macOS):
Add to `~/.bashrc` or `~/.zshrc`:
```bash
export NEXTLINK_RADIUS_SECRET="your_radius_secret_here"
```

## Database Security

- **Database Location**: All databases are stored in `secure_data/` directory
- **Access Control**: Databases are NOT accessible via HTTP
- **File Permissions**: Secure directory has restricted permissions (700 on Unix)
- **Backup**: Ensure `secure_data/` is backed up securely

## HTTP Server Security

The HTTP server (`serve_html.py`) is configured with:
- ✅ Directory listing: **BLOCKED**
- ✅ File browsing: **BLOCKED**
- ✅ Only `NOC-configMaker.html` is accessible
- ✅ Sensitive files/directories blocked:
  - `secure_data/` (databases)
  - `.git/` (source code)
  - All `.py`, `.js`, `.db`, `.md`, `.bat` files
  - Configuration files

## What's Protected

1. **RADIUS Secret**: Moved to environment variable
2. **Database Files**: Moved to `secure_data/` directory
3. **Source Code**: Not accessible via HTTP
4. **Configuration Files**: Blocked from HTTP access
5. **Proprietary IPs**: Still in code (infrastructure IPs - acceptable)

## Migration Instructions

If you have existing database files in the root directory:

1. **Stop the server** if running
2. **Create secure directory**:
   ```bash
   mkdir secure_data
   ```
3. **Move databases**:
   ```bash
   move chat_history.db secure_data\
   move completed_configs.db secure_data\
   ```
4. **Set environment variable** (see above)
5. **Restart server**

## Verification

After setup, verify:
- ✅ Environment variable is set: `echo $NEXTLINK_RADIUS_SECRET` (Linux) or `echo %NEXTLINK_RADIUS_SECRET%` (Windows)
- ✅ Database files are in `secure_data/` directory
- ✅ Accessing `http://your-ip:8000/` redirects to UI (no directory listing)
- ✅ Accessing `http://your-ip:8000/secure_data/` returns 404
- ✅ Accessing `http://your-ip:8000/api_server.py` returns 404

## Important Notes

- **NEVER** commit the `.env` file or `secure_data/` directory to Git
- **NEVER** hardcode secrets in source code
- **NEVER** expose database files via HTTP
- Always use environment variables for sensitive configuration

