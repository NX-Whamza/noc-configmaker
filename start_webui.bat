@echo off
setlocal
cd /d "%~dp0"

rem ===== Ensure Python 3.11 pip exists =====
for /f "delims=" %%P in ('py -3.11 -m pip --version 2^>nul') do set HASPIP=1
if not defined HASPIP (
  echo [WEBUI] Python 3.11 and pip not detected. Install Python 3.11 first.
  pause
  exit /b 1
)

rem ===== Install/Upgrade Open WebUI (one-time; may take a few minutes) =====
echo [WEBUI] Installing/upgrading Open WebUI ...
py -3.11 -m pip install --upgrade open-webui --no-cache-dir --prefer-binary --timeout 600

rem ===== Launch WebUI =====
echo [WEBUI] Attempting to start Open WebUI on http://localhost:3000 ...
set "SCRIPTS_DIR=%LOCALAPPDATA%\Packages\PythonSoftwareFoundation.Python.3.11_qbz5n2kfra8p0\LocalCache\local-packages\Python311\Scripts"
set "OPENWEBUI_EXE=%SCRIPTS_DIR%\open-webui.exe"
if exist "%OPENWEBUI_EXE%" (
  start "Open WebUI" /min "%OPENWEBUI_EXE%" serve --host 0.0.0.0 --port 3000
) else (
  echo [WEBUI] open-webui.exe not found in %SCRIPTS_DIR% . Adding to PATH and trying shell fallback ...
  set "PATH=%SCRIPTS_DIR%;%PATH%"
  start "Open WebUI" /min cmd /c "open-webui serve --host 0.0.0.0 --port 3000"
)

rem ===== Fallback to default port 8080 (some builds ignore --port) =====
timeout /t 2 /nobreak >nul
echo [WEBUI] If http://localhost:3000 refuses, use http://localhost:8080
start "" "http://localhost:3000"
start "" "http://localhost:8080"
start "" "http://localhost:3000"
echo [WEBUI] Configure: Settings -> Connections
echo         Provider: OpenAI (custom)
echo         Base URL: http://localhost:5000/v1
echo         API Key : noc-local (any non-empty)
echo         Model   : noc-local
endlocal
exit /b 0


