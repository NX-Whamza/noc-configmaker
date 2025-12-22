# GitHub Push Authentication Guide

## Issue
`git push` failed with 403 error - authentication required

## Solutions

### Option 1: GitHub Personal Access Token (Recommended)

**Step 1: Create a Personal Access Token**
1. Go to https://github.com/settings/tokens
2. Click "Generate new token" → "Generate new token (classic)"
3. Give it a name: "NOC Config Maker"
4. Select scopes:
   - ✅ `repo` (Full control of private repositories)
5. Click "Generate token"
6. **COPY THE TOKEN** (you won't see it again!)

**Step 2: Use Token for Push**
```powershell
# When prompted for password, paste your token instead
git push origin main

# Username: NX-Whamza
# Password: <paste your token here>
```

**Step 3: Save Credentials (Optional)**
```powershell
# Store credentials so you don't have to enter them every time
git config credential.helper store
git push origin main
# Enter credentials once, they'll be saved
```

---

### Option 2: GitHub CLI (Easiest)

**Step 1: Install GitHub CLI**
```powershell
# Download from: https://cli.github.com/
# Or use winget:
winget install GitHub.cli
```

**Step 2: Authenticate**
```powershell
gh auth login
# Follow prompts to authenticate via browser
```

**Step 3: Push**
```powershell
git push origin main
# Should work automatically now
```

---

### Option 3: SSH Keys (Most Secure)

**Step 1: Generate SSH Key**
```powershell
ssh-keygen -t ed25519 -C "your.name@team.nxlink.com"
# Press Enter to accept default location
# Enter passphrase (optional but recommended)
```

**Step 2: Add SSH Key to GitHub**
```powershell
# Copy public key to clipboard
Get-Content ~/.ssh/id_ed25519.pub | clip

# Go to: https://github.com/settings/keys
# Click "New SSH key"
# Paste key and save
```

**Step 3: Change Remote to SSH**
```powershell
git remote set-url origin git@github.com:NX-Whamza/noc-configmaker.git
git push origin main
```

---

## Quick Fix (Right Now)

**Use Personal Access Token:**
1. Create token at: https://github.com/settings/tokens
2. Run:
   ```powershell
   git push origin main
   ```
3. When prompted:
   - Username: `NX-Whamza`
   - Password: `<paste your token>`

---

## Verify After Push

```powershell
# Check if push succeeded
git log --oneline -1

# View on GitHub
# https://github.com/NX-Whamza/noc-configmaker
```

---

## Alternative: Push from Different Account

If you want to push from your `Wally0517` account instead:

```powershell
# Change remote back
git remote set-url origin https://github.com/Wally0517/noc-configmaker.git

# Push
git push origin main
```

Then you can transfer the repository to `NX-Whamza` organization later via GitHub settings.
