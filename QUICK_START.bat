@echo off
REM Quick Start - Opens both backend and frontend in separate windows

title NOC ConfigMaker - Launcher
color 0E

echo ========================================
echo  NOC ConfigMaker - Quick Start
echo ========================================
echo.
echo Starting backend and frontend servers...
echo.

REM Start backend in new window
start "NOC Backend" /MIN cmd /c "python api_server.py"

REM Wait for backend to start
timeout /t 3 /nobreak >nul

REM Start frontend in new window
start "NOC Frontend" cmd /c "python -m http.server 8000"

REM Wait for frontend to start
timeout /t 3 /nobreak >nul

REM Open browser
echo Opening browser...
start http://localhost:8000/NOC-configMaker.html

echo.
echo ========================================
echo  Services Started!
echo ========================================
echo.
echo Backend:  http://localhost:5000
echo Frontend: http://localhost:8000
echo.
echo KEEP THE SERVER WINDOWS OPEN!
echo Close this window anytime.
echo.

pause


