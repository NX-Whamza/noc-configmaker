@echo off
REM ========================================
REM NOC Config Maker - BACKEND STARTUP
REM This is the ONLY script you need!
REM ========================================
cd /d "%~dp0"

echo ========================================
echo NOC Config Maker - Backend Startup
echo ========================================
echo.
echo What happens here:
echo 1. Start Ollama (local AI service)
echo 2. Start api_server.py (backend)
echo 3. Ready for HTML tool to connect
echo ========================================
echo.

REM Check if Ollama is running
curl -s http://localhost:11434/api/tags >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [!] Starting Ollama service...
    start "" "%LOCALAPPDATA%\Programs\Ollama\ollama.exe" serve
    timeout /t 3 /nobreak >nul
    echo.
)

echo [*] Starting Flask backend with Ollama...
echo.
echo Model: phi3:mini (3x faster than qwen2.5-coder:7b)
echo API: http://localhost:5000
echo.
echo [TRAINING] Ollama has been configured with:
echo - Complete RouterOS v6 to v7 syntax mappings
echo - Nextlink naming conventions and standards  
echo - IP/firewall/VLAN preservation rules
echo - OSPF/BGP migration procedures
echo.
echo [Note] First translation: 15-30 seconds (model loading)
echo       Subsequent: 5-10 seconds
echo.
echo ========================================
echo.

set AI_PROVIDER=ollama
python api_server.py

pause

