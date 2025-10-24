@echo off
REM Run NOC Config Maker backend in the foreground with logs
cd /d "%~dp0"
echo [NOC] Starting backend (foreground)...
set AI_PROVIDER=ollama

REM Ensure Ollama is running
curl -s http://localhost:11434/api/tags >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
  echo [NOC] Launching Ollama...
  start "" "%LOCALAPPDATA%\Programs\Ollama\ollama.exe" serve
  timeout /t 3 /nobreak >nul
)

python api_server.py

