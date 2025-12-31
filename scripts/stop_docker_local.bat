@echo off
title NOC Config Maker - Docker Stop
color 0C

cd /d "%~dp0.."

where docker >nul 2>nul
if %errorlevel% neq 0 (
  echo Docker is not installed or not on PATH.
  pause
  exit /b 1
)

echo Stopping NOC Config Maker containers...
docker compose down
pause

