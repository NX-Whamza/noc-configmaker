@echo off
setlocal
cd /d "%~dp0"

rem ===== Start Ollama (if installed) =====
set "OLLAMA_EXE=%LOCALAPPDATA%\Programs\Ollama\ollama.exe"
if exist "%OLLAMA_EXE%" (
  echo [BACKEND] Starting Ollama serve (if not already running)...
  start "Ollama" /min "%OLLAMA_EXE%" serve
  timeout /t 2 /nobreak >nul
) else (
  echo [BACKEND] Ollama not found at %OLLAMA_EXE%. If not installed, visit https://ollama.com/download
)

rem ===== Env for NOC Config Maker backend =====
set "AI_PROVIDER=ollama"
set "OLLAMA_MODEL=phi3:mini"
set "ROS_TRAINING_DIR=%USERPROFILE%\Downloads\ros-migration-trainer-v3"

echo [BACKEND] Using training dir: %ROS_TRAINING_DIR%

rem ===== Start Flask backend =====
echo [BACKEND] Launching api_server.py ...
start "NOC Backend" /min cmd /c "cd /d %~dp0 && python api_server.py"
echo [BACKEND] Server starting on http://localhost:5000 (check /api/health)
endlocal
exit /b 0


