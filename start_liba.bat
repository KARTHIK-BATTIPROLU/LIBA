@echo off
REM LIBA Desktop Pet + Voice Agent Launcher

echo [LIBA] Starting Liebe Desktop Pet...
start "" /D "C:\Users\Karthik\OneDrive\Desktop\LIBA\desktop_pet" "node_modules\electron\dist\electron.exe" .

echo [LIBA] Waiting 3 seconds...
ping 127.0.0.1 -n 4 >nul

echo [LIBA] Starting Python Orchestrator...
start "" /B "C:\Users\Karthik\OneDrive\Desktop\LIBA\.venv\Scripts\pythonw.exe" "C:\Users\Karthik\OneDrive\Desktop\LIBA\run_liba.py" --mode background

echo [LIBA] System is active! Liebe is running on your desktop.