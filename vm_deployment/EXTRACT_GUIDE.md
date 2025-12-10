# How to Extract the Transferred Files

## Step 1: Find the Archive File

The file was transferred to your home directory (`~`), not `~/vm_deployment`. Check:

```bash
# List files in home directory
ls -lh ~/noc-configmaker-vm-*.tar.gz

# Or check all .tar.gz files
ls -lh ~/*.tar.gz
```

## Step 2: Extract to vm_deployment

**Option A: Extract to existing vm_deployment directory**
```bash
cd ~/vm_deployment
tar -xzf ~/noc-configmaker-vm-*.tar.gz
```

**Option B: Extract to a new location**
```bash
mkdir -p ~/vm_deployment
cd ~/vm_deployment
tar -xzf ~/noc-configmaker-vm-*.tar.gz
```

**Option C: Extract to current directory (if file is already in vm_deployment)**
```bash
cd ~/vm_deployment
# First, find the exact filename
ls -la *.tar.gz
# Then extract (replace with actual filename)
tar -xzf noc-configmaker-vm-20251208-*.tar.gz
```

## Common Mistakes Fixed

❌ **Wrong:** `tar -xzf noc-configmaker-vm-*.tar.gz -c`
- `-c` is for creating archives, not extracting
- The file might not be in current directory

✅ **Correct:** `tar -xzf ~/noc-configmaker-vm-*.tar.gz`
- Extracts to current directory
- Uses `~` to reference home directory

✅ **Also Correct:** `tar -xzf ~/noc-configmaker-vm-*.tar.gz -C ~/vm_deployment`
- `-C` (capital C) changes to directory before extracting
- Extracts directly to vm_deployment

## Quick Fix Command

If the file is in your home directory:
```bash
cd ~/vm_deployment
tar -xzf ~/noc-configmaker-vm-*.tar.gz
```

If you're not sure where the file is:
```bash
# Find it
find ~ -name "noc-configmaker-vm-*.tar.gz" -type f 2>/dev/null

# Then extract (replace with the path found above)
cd ~/vm_deployment
tar -xzf /path/to/noc-configmaker-vm-*.tar.gz
```
