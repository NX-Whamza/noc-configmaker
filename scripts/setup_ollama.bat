@echo off
REM Ollama Setup Script for NOC Config Maker
REM This script helps you install Ollama and download the AI model

echo ========================================
echo Ollama Setup for NOC Config Maker
echo ========================================
echo.

REM Check if Ollama is installed
where ollama >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    echo [OK] Ollama is already installed!
    echo.
    goto :download_model
)

echo [!] Ollama is not installed.
echo.
echo Step 1: Download Ollama
echo ----------------------------------------
echo Opening download page in your browser...
echo.
echo Please download and install OllamaSetup.exe
echo Then run this script again.
echo.
start https://ollama.com/download
echo.
pause
exit /b

:download_model
echo Step 2: Download AI Model
echo ----------------------------------------
echo Downloading qwen2.5-coder:7b (Best for code, ~4.7GB)...
echo This may take 5-15 minutes depending on your internet speed.
echo.

ollama pull qwen2.5-coder:7b

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ========================================
    echo [SUCCESS] Ollama is ready!
    echo ========================================
    echo.
    echo Model: qwen2.5-coder:7b
    echo Status: Downloaded and ready
    echo.
    echo Next steps:
    echo 1. Run: python api_server.py
    echo 2. Open NOC-configMaker.html in browser
    echo 3. Upload your config file
    echo.
) else (
    echo.
    echo [ERROR] Model download failed.
    echo Please check your internet connection and try again.
    echo.
)

pause

