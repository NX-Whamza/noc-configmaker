# NOC Config Maker - Quick Start (Ollama)

## Start the Backend

**Option 1: Use the batch script**
```cmd
start_ollama_server.bat
```

**Option 2: Manual start**
```cmd
set AI_PROVIDER=ollama
python api_server.py
```

## Use the Tool

1. Open `NOC-configMaker.html` in your browser
2. Click "Upgrade Existing" mode
3. Drag & drop your `.rsc` config file
4. Select target device (CCR2004, CCR2216, etc.)
5. Select target RouterOS version
6. Click "Start Upgrade" button
7. **Wait 15-30 seconds** (first translation loads model)
8. Subsequent translations: 5-10 seconds

## Troubleshooting

### "AI Backend offline"
- Run: `start_ollama_server.bat`
- Or check if Python server is running

### "Connection timeout"
- First translation always takes longer (loading 4.7GB model)
- Wait 30 seconds and click "Start Upgrade" again
- Model stays loaded for 5 minutes, then unloads

### "Cannot connect to Ollama"
- Ollama service stopped
- Run: `"%LOCALAPPDATA%\Programs\Ollama\ollama.exe" serve`

## Performance

- **First translation**: 15-30 seconds (model loading)
- **Subsequent translations**: 5-10 seconds
- **Model size**: 4.7GB RAM when active
- **Cost**: $0.00 (completely free)

## What Gets Translated

✅ v6 → v7 syntax conversion  
✅ Interface naming updates  
✅ OSPF/BGP template migration  
✅ Bridge VLAN filtering  
✅ IP addressing preserved  
✅ Firewall rules preserved  
✅ Nextlink standards applied  

## Notes

- Configs never leave your PC
- No internet required (after initial setup)
- Model unloads after 5 minutes of inactivity
- First request of the day = slow, rest = fast

