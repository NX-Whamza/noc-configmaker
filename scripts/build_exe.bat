@echo off
REM ========================================
REM NOC Config Maker - Executable Builder
REM ========================================
setlocal enabledelayedexpansion
cd /d "%~dp0"

echo ========================================
echo NOC Config Maker - Executable Builder
echo ========================================
echo.

REM Check Python
python --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Python is not installed or not in PATH
    echo Please install Python 3.8+ and add it to your PATH
    pause
    exit /b 1
)

REM Check if requirements are installed
echo [1/3] Checking dependencies...
python -c "import flask" >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [1/3] Installing Python dependencies...
    python -m pip install -r requirements.txt
    if %ERRORLEVEL% NEQ 0 (
        echo [ERROR] Failed to install dependencies
        pause
        exit /b 1
    )
)

REM Check PyInstaller
echo [2/3] Checking PyInstaller...
python -c "import PyInstaller" >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [2/3] Installing PyInstaller...
    python -m pip install pyinstaller
    if %ERRORLEVEL% NEQ 0 (
        echo [ERROR] Failed to install PyInstaller
        pause
        exit /b 1
    )
)

REM Build executable
echo [3/3] Building executable...
echo This may take several minutes...
echo.

python build_exe.py

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ========================================
    echo Build Complete!
    echo ========================================
    echo.
    echo Executable location: dist\NOC-ConfigMaker.exe
    echo.
    echo You can now distribute this .exe file.
    echo Users can run it without installing Python.
    echo.
) else (
    echo.
    echo ========================================
    echo Build Failed!
    echo ========================================
    echo Check errors above.
    echo.
)

pause

