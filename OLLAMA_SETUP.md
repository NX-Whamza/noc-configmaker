# Ollama Setup Guide - Free Local AI

## What is Ollama?
Ollama runs AI models locally on your PC - completely free, no API costs, and your configs never leave your network.

---

## Quick Setup (3 Steps)

### Step 1: Install Ollama (2 minutes)

**Windows:**
1. Download: https://ollama.com/download
2. Run `OllamaSetup.exe`
3. Installation is automatic

**Or use the provided script:**
```cmd
setup_ollama.bat
```

### Step 2: Download AI Model (5-15 minutes)

Open Command Prompt or PowerShell and run:

```cmd
ollama pull qwen2.5-coder:7b
```

**This will download ~4.7GB.** It's a one-time download.

**Why this model?**
- Best for code translation
- Fast inference (~5-10 seconds per config)
- Works on most PCs (8GB RAM minimum)

### Step 3: Start the Backend

```cmd
python api_server.py
```

You should see:
```
==================================================
NOC Config Maker - AI Backend Server
==================================================
AI Provider: OLLAMA
Ollama Model: qwen2.5-coder:7b
Ollama URL: http://localhost:11434
```

---

## Verify It's Working

1. Open your browser
2. Go to: http://localhost:11434/api/tags
3. You should see JSON with your installed models

OR use curl:
```cmd
curl http://localhost:11434/api/tags
```

---

## Usage

1. **Start Ollama** (runs automatically after install, or run `ollama serve`)
2. **Start Backend**: `python api_server.py`
3. **Open HTML**: Double-click `NOC-configMaker.html`
4. **Upload config** in "Upgrade Existing" mode
5. **Wait 30-60 seconds** for translation

---

## Alternative Models

If you have more RAM or want faster/better results:

| Model | Size | RAM Required | Speed | Quality |
|-------|------|--------------|-------|---------|
| `qwen2.5-coder:7b` | 4.7GB | 8GB | Fast | Good ✅ |
| `qwen2.5-coder:14b` | 9GB | 16GB | Medium | Better |
| `codestral:22b` | 13GB | 24GB | Slow | Best |

To change models:
```cmd
ollama pull codestral:22b
set OLLAMA_MODEL=codestral:22b
python api_server.py
```

---

## Troubleshooting

### "Cannot connect to Ollama"
- Make sure Ollama is running: `ollama serve`
- Check http://localhost:11434 is accessible

### "Model not found"
- Run: `ollama pull qwen2.5-coder:7b`
- Check installed models: `ollama list`

### "Response is slow"
- Normal: First request takes 10-15 seconds (model loading)
- Subsequent requests: 5-10 seconds
- Upgrade to faster model if needed

### "Out of memory"
- Close other applications
- Use smaller model: `ollama pull qwen2.5-coder:3b`
- Set: `set OLLAMA_MODEL=qwen2.5-coder:3b`

---

## Cost Comparison

| Provider | Cost per Config | Monthly (50 configs) |
|----------|----------------|----------------------|
| OpenAI GPT-4 | $0.03-0.05 | $1.50-2.50 |
| **Ollama (Local)** | **$0.00** | **$0.00** ✅ |

---

## Security Benefits

✅ Configs never leave your network  
✅ No API keys to manage  
✅ No internet required (after download)  
✅ Works offline  
✅ HIPAA/SOC2 compliant (air-gapped)

---

## Need Help?

Check Ollama docs: https://github.com/ollama/ollama/blob/main/docs/windows.md

