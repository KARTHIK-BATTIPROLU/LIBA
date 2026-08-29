@echo off
setlocal enabledelayedexpansion
title LIBA Desktop Pet ^& Voice Assistant

echo ===================================================
echo     LIBA Desktop Pet + Voice Assistant Launcher
echo ===================================================
echo.

cd /d "%~dp0desktop_pet"
echo [1/3] Launching Liebe Desktop Pet...
start "" "%~dp0desktop_pet\node_modules\electron\dist\electron.exe" .

echo [2/3] Initializing components (3s)...
ping 127.0.0.1 -n 4 >nul

cd /d "%~dp0"
echo [3/3] Starting LIBA Voice Agent in background...
start "" /B "%~dp0.venv\Scripts\pythonw.exe" "%~dp0run_liba.py" --mode background

echo.
echo ===================================================
echo [SUCCESS] Liebe is now running on your desktop!
echo Say "LIBA" to wake her up or drag her around.
echo ===================================================
echo.
ping 127.0.0.1 -n 4 >nul