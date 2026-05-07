@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Missing .venv\Scripts\python.exe. Run install_windows.bat first.
  pause
  exit /b 1
)
.venv\Scripts\python.exe -m hamsa_caption_engine.diagnostics
pause
