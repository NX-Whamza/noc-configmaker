@echo off
REM ========================================
REM AI SERVER DEPLOYMENT SCRIPT
REM Deploy NOC Config Maker AI Server
REM ========================================
cd /d "%~dp0"

echo ========================================
echo NOC AI SERVER DEPLOYMENT
echo ========================================
echo.
echo This will set up your PC as a dedicated AI server
echo accessible from anywhere on your network.
echo.
echo Features:
echo - Smart model selection (phi3:mini, qwen2.5-coder:7b)
echo - MikroTik documentation integration
echo - Nextlink standards training
echo - Network access from any device
echo - Auto-start on boot
echo ========================================
echo.

REM Check if running as administrator
net session >nul 2>&1
if %errorLevel% == 0 (
    echo [✓] Running as administrator
) else (
    echo [!] Please run as administrator for full setup
    echo     Right-click and "Run as administrator"
    pause
    exit /b 1
)

echo [1/8] Installing Python 3.11...
winget install Python.Python.3.11 --accept-package-agreements --accept-source-agreements
if %ERRORLEVEL% NEQ 0 (
    echo [!] Python installation failed. Please install manually from python.org
    pause
    exit /b 1
)

echo [2/8] Installing Ollama...
curl -fsSL https://ollama.com/install.sh | sh
if %ERRORLEVEL% NEQ 0 (
    echo [!] Ollama installation failed. Please install manually from ollama.com
    pause
    exit /b 1
)

echo [3/8] Starting Ollama service...
start "" "%LOCALAPPDATA%\Programs\Ollama\ollama.exe" serve
timeout /t 5 /nobreak >nul

echo [4/8] Downloading AI models...
ollama pull phi3:mini
ollama pull qwen2.5-coder:7b
ollama pull llama3.2:3b

echo [5/8] Installing Python dependencies...
py -3.11 -m pip install --upgrade pip
py -3.11 -m pip install -r requirements.txt

echo [6/8] Setting up network access...
netsh advfirewall firewall add rule name="NOC AI Server" dir=in action=allow protocol=TCP localport=5000
netsh advfirewall firewall add rule name="NOC AI Server WebUI" dir=in action=allow protocol=TCP localport=3000

echo [7/8] Creating auto-start service...
echo @echo off > "%USERPROFILE%\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Startup\start_ai_server.bat"
echo cd /d "%~dp0" >> "%USERPROFILE%\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Startup\start_ai_server.bat"
echo start "" "%LOCALAPPDATA%\Programs\Ollama\ollama.exe" serve >> "%USERPROFILE%\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Startup\start_ai_server.bat"
echo timeout /t 10 /nobreak ^>nul >> "%USERPROFILE%\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Startup\start_ai_server.bat"
echo set AI_PROVIDER=ollama >> "%USERPROFILE%\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Startup\start_ai_server.bat"
echo set OLLAMA_MODEL=phi3:mini >> "%USERPROFILE%\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Startup\start_ai_server.bat"
echo set ROS_TRAINING_DIR=%CD%\ros-migration-trainer-v3 >> "%USERPROFILE%\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Startup\start_ai_server.bat"
echo python api_server.py >> "%USERPROFILE%\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Startup\start_ai_server.bat"

echo [8/8] Starting AI server...
set AI_PROVIDER=ollama
set OLLAMA_MODEL=phi3:mini
set ROS_TRAINING_DIR=%CD%\ros-migration-trainer-v3

echo [CHAT] Initializing chat history database...
python -c "import sqlite3; conn = sqlite3.connect('chat_history.db'); conn.close(); print('Chat database ready')"

echo [MEMORY] Chat history and user preferences will be saved
echo [CONTEXT] AI will remember conversations across sessions
echo [EXPORT] Chat history can be exported via API

python api_server.py

echo ========================================
echo AI SERVER DEPLOYMENT COMPLETE!
echo ========================================
echo.
echo Your AI server is now running on:
echo   - AI API: http://YOUR_IP:5000/v1
echo   - Health: http://YOUR_IP:5000/api/health
echo.
echo To find your IP address, run: ipconfig
echo.
echo The server will auto-start on boot.
echo You can access it from any device on your network!
echo ========================================
pause
