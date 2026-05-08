@echo off
setlocal EnableExtensions
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Missing .venv\Scripts\python.exe. Run install_windows.bat first.
  pause
  exit /b 1
)
if exist ".env" (
  for /f "usebackq tokens=1,* delims==" %%A in (".env") do (
    if not "%%A"=="" if not "%%A:~0,1"=="#" set "%%A=%%B"
  )
)
if "%HAMSA_TELEGRAM_BOT_TOKEN%"=="" (
  echo Missing HAMSA_TELEGRAM_BOT_TOKEN. Add it to .env.
  pause
  exit /b 1
)
.venv\Scripts\python.exe -m hamsa_caption_engine.telegram_bot
if errorlevel 1 (
  echo Bot stopped with an error.
  pause
  exit /b 1
)
