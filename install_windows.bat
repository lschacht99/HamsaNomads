@echo off
setlocal EnableExtensions
cd /d "%~dp0"
echo Hamsa Nomads Windows installer
where python >nul 2>nul
if errorlevel 1 (
  echo Python was not found. Install Python 3.10+ from python.org, then run this again.
  pause
  exit /b 1
)
if not exist ".venv\Scripts\python.exe" (
  echo Creating .venv...
  python -m venv .venv
  if errorlevel 1 goto fail
)
set "PY=.venv\Scripts\python.exe"
"%PY%" -m pip install --upgrade pip setuptools wheel
if errorlevel 1 goto fail
"%PY%" -m pip install -e .
if errorlevel 1 goto fail
set /p INSTALL_WHISPER="Install Whisper automatic transcription? Y/N: "
if /I "%INSTALL_WHISPER%"=="Y" (
  "%PY%" -m pip install -e ".[whisper]"
  if errorlevel 1 goto fail
)
set /p SETUP_FFMPEG="Set up FFmpeg locally? Y/N: "
if /I "%SETUP_FFMPEG%"=="Y" (
  call download_ffmpeg.bat
)
set /p INSTALL_REMOTION="Install Remotion premium renderer? Y/N: "
if /I "%INSTALL_REMOTION%"=="Y" (
  where npm >nul 2>nul
  if errorlevel 1 (
    echo npm was not found. Install Node.js LTS, then run npm install inside remotion\.
  ) else (
    pushd remotion
    npm install
    popd
  )
)
set /p SET_TOKEN="Do you want to create/update .env with your Telegram bot token? Y/N: "
if /I "%SET_TOKEN%"=="Y" (
  set /p BOT_TOKEN="Paste Telegram bot token: "
  > .env echo HAMSA_TELEGRAM_BOT_TOKEN=%BOT_TOKEN%
  echo Token saved to .env. It was not printed back.
)
echo Running setup diagnostics...
"%PY%" -m hamsa_caption_engine.diagnostics
echo.
echo Next step: Double-click run_bot.bat
pause
exit /b 0
:fail
echo Installer failed. Read the error above.
pause
exit /b 1
