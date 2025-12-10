# Quick Fix for Tar Extraction

## The Problem
You're using the wrong filename. The `ls` command shows:
```
noc-configmaker-vm-20251208-210556.tar.gz
```

But you tried to extract:
```
noc-configmaker-vm-20251208-210255.tar.gz  ❌ (wrong timestamp)
```

## Solution - Use the EXACT filename:

```bash
cd ~/vm_deployment
tar -xzf noc-configmaker-vm-20251208-210556.tar.gz
```

## Or use this safer method:

```bash
cd ~/vm_deployment

# Method 1: Copy the exact filename from ls output
ls -1 noc-configmaker-vm-*.tar.gz
# Then use that EXACT filename:
tar -xzf noc-configmaker-vm-20251208-210556.tar.gz

# Method 2: Use wildcard with proper syntax
tar -xzf noc-configmaker-vm-*.tar.gz

# Method 3: Extract to current directory explicitly
tar -xzf noc-configmaker-vm-*.tar.gz -C .
```

## Complete Step-by-Step:

```bash
# 1. Make sure you're in the right directory
cd ~/vm_deployment

# 2. List files to see exact name
ls -lh noc-configmaker-vm-*.tar.gz

# 3. Extract using the EXACT filename shown above
tar -xzf noc-configmaker-vm-20251208-210556.tar.gz

# 4. Verify extraction
ls -la

# 5. Make scripts executable
chmod +x setup_vm.sh configure_nginx_domain.sh

# 6. Run domain setup
bash configure_nginx_domain.sh
```

## If you still get errors:

Try extracting with verbose output to see what's happening:
```bash
tar -xzvf noc-configmaker-vm-20251208-210556.tar.gz
```

The `-v` flag shows what files are being extracted so you can see progress.
