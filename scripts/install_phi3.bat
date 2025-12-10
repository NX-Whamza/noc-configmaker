@echo off
echo Installing Phi-3 Mini (3x faster model)...
ollama pull phi3:mini
echo.
echo Model installed! Now restart your backend.
echo.
echo To use the fast model, run:
echo   set OLLAMA_MODEL=phi3:mini
echo   python api_server.py
echo.
pause