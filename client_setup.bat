@echo off
REM ========================================
REM CLIENT SETUP - Connect to AI Server
REM ========================================
cd /d "%~dp0"

echo ========================================
echo NOC AI CLIENT SETUP
echo ========================================
echo.
echo This sets up your laptop to connect to the AI server
echo running on your dedicated PC.
echo ========================================
echo.

set /p SERVER_IP="Enter AI Server IP address (e.g., 192.168.1.100): "

echo [1/3] Testing connection to AI server...
curl -s http://%SERVER_IP%:5000/api/health
if %ERRORLEVEL% NEQ 0 (
    echo [!] Cannot connect to AI server at %SERVER_IP%:5000
    echo     Please check:
    echo     - Server is running
    echo     - IP address is correct
    echo     - Firewall allows connections
    pause
    exit /b 1
)

echo [✓] AI server is reachable!

echo [2/3] Updating Open WebUI configuration...
echo.
echo Open WebUI Settings:
echo   - Provider: OpenAI (Custom)
echo   - Base URL: http://%SERVER_IP%:5000/v1
echo   - API Key: noc-local
echo   - Model: noc-local
echo.

echo [3/3] Creating connection test...
echo @echo off > test_ai_connection.bat
echo echo Testing AI server connection... >> test_ai_connection.bat
echo curl -s http://%SERVER_IP%:5000/v1/models >> test_ai_connection.bat
echo if %%ERRORLEVEL%% EQU 0 ( >> test_ai_connection.bat
echo     echo [✓] AI server is working! >> test_ai_connection.bat
echo ^) else ( >> test_ai_connection.bat
echo     echo [!] AI server connection failed >> test_ai_connection.bat
echo ^) >> test_ai_connection.bat

echo ========================================
echo CLIENT SETUP COMPLETE!
echo ========================================
echo.
echo Your laptop is now configured to use the AI server.
echo.
echo Next steps:
echo 1. Open Open WebUI on your laptop
echo 2. Go to Settings → Connections
echo 3. Add new connection with the settings above
echo 4. Test the connection
echo.
echo AI Server URL: http://%SERVER_IP%:5000/v1
echo ========================================
pause
