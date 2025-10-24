@echo off
echo ========================================
echo Installing Fast Ollama Model
echo ========================================
echo.
echo Installing Phi-3 Mini (3.8B) - FASTEST for RouterOS
echo This will be 3-5x faster than qwen2.5-coder:7b
echo.

echo [1/3] Pulling Phi-3 Mini model...
ollama pull phi3:mini

echo.
echo [2/3] Setting environment variable...
set OLLAMA_MODEL=phi3:mini

echo.
echo [3/3] Starting backend with fast model...
set AI_PROVIDER=ollama
python api_server.py

echo.
echo ========================================
echo Fast model installed and ready!
echo ========================================
pause
