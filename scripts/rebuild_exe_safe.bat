@echo off
REM Safe rebuild - checks if exe is running and prompts to close it
setlocal enabledelayedexpansion
cd /d "%~dp0"

echo ========================================
echo NOC Config Maker - Safe Rebuild
echo ========================================
echo.

REM Check if executable is running
tasklist /FI "IMAGENAME eq NOC-ConfigMaker.exe" 2>NUL | find /I /N "NOC-ConfigMaker.exe">NUL
if "%ERRORLEVEL%"=="0" (
    echo [WARNING] NOC-ConfigMaker.exe is currently running!
    echo.
    echo Please close the application window first, then press any key to continue...
    pause >nul
    echo.
)

REM Check again after pause
tasklist /FI "IMAGENAME eq NOC-ConfigMaker.exe" 2>NUL | find /I /N "NOC-ConfigMaker.exe">NUL
if "%ERRORLEVEL%"=="0" (
    echo [ERROR] Executable is still running. Please close it manually.
    echo.
    pause
    exit /b 1
)

echo [1/3] Cleaning previous build...
if exist dist (
    rmdir /s /q dist 2>nul
    if exist dist (
        echo [WARNING] Could not delete dist folder - may still be in use
    ) else (
        echo [1/3] ✓ Cleaned dist folder
    )
) else (
    echo [1/3] ✓ No dist folder to clean
)

if exist build (
    rmdir /s /q build 2>nul
    if exist build (
        echo [WARNING] Could not delete build folder
    ) else (
        echo [1/3] ✓ Cleaned build folder
    )
) else (
    echo [1/3] ✓ No build folder to clean
)
echo.

echo [2/3] Rebuilding executable...
echo This may take several minutes...
echo.

python -m PyInstaller --clean --noconfirm NOC-ConfigMaker.spec

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ========================================
    echo ✓ Build Complete!
    echo ========================================
    echo.
    echo Executable location: dist\NOC-ConfigMaker.exe
    echo.
    echo You can now test the new executable.
    echo.
) else (
    echo.
    echo ========================================
    echo ✗ Build Failed!
    echo ========================================
    echo Check errors above.
    echo.
)

pause

