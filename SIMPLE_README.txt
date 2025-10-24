========================================
NOC CONFIG MAKER - SIMPLE INSTRUCTIONS
========================================

WHAT YOU HAVE:
--------------
1. Ollama (local AI service - installed separately)
2. api_server.py (backend that talks to Ollama)
3. NOC-configMaker.html (the actual tool)

HOW TO USE:
-----------
Step 1: ONE-TIME SETUP
   - Double-click: setup_ollama.bat
   - This installs Ollama and downloads the AI model (~4.7GB)
   - Only do this once!

Step 2: EVERY TIME YOU WANT TO USE THE TOOL
   - Double-click: start_ollama_server.bat
   - This starts the backend (keep window open)
   - Then open: NOC-configMaker.html in your browser

Step 3: USE THE TOOL
   - In browser: Select "Upgrade Existing" mode
   - Drag & drop your .rsc config file
   - Select target device and RouterOS version
   - Click "Start Upgrade"
   - Wait 15-60 seconds
   - Get translated config!

TROUBLESHOOTING:
----------------
If you see "Backend offline":
   → Make sure start_ollama_server.bat is running
   → Keep that PowerShell window open
   → Check that you ran setup_ollama.bat first

If upgrade takes forever:
   → First run after startup takes 15-30 seconds (loading model)
   → After that, should be 5-10 seconds

THAT'S IT! No cloud API, no payments, all local.

========================================
Questions? Check QUICK_START.md
========================================

