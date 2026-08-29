' LIBA Silent Background Launcher
' Runs the watchdog supervisor silently with pythonw.exe (no console window)

Set WshShell = CreateObject("WScript.Shell")
strCommand = """" & "C:\Users\Karthik\OneDrive\Desktop\LIBA\.venv\Scripts\pythonw.exe" & """ """ & "C:\Users\Karthik\OneDrive\Desktop\LIBA\orchestrator\watchdog.py" & """"
WshShell.Run strCommand, 0, False