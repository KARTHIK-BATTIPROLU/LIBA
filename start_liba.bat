@echo off
REM LIBA Desktop Pet + Voice Agent Launcher

echo [LIBA] Starting LIBA Voice Agent service in background...
start "" /B "C:\Users\Karthik\OneDrive\Desktop\LIBA\.venv\Scripts\pythonw.exe" "C:\Users\Karthik\OneDrive\Desktop\LIBA\run_liba.py" --mode background

echo [LIBA] Waiting 3 seconds for event bridge to initialize...
timeout /t 3 /nobreak >nul

echo [LIBA] Starting Liebe Desktop Pet and Companion Chat UI...
start "" "C:\Users\Karthik\OneDrive\Desktop\LIBA\desktop_pet\node_modules\electron\dist\electron.exe" "C:\Users\Karthik\OneDrive\Desktop\LIBA\desktop_pet"

echo [LIBA] System is active! Liebe is running on your screen.