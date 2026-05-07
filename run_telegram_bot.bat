@echo off
setlocal
cd /d "%~dp0"

echo ========================================
echo Hamsa Telegram Bot
echo ========================================
echo.

if exist ".venv\Scripts\activate.bat" (
  call ".venv\Scripts\activate.bat"
)

where python >nul 2>nul
if errorlevel 1 (
  echo ERROR: Python was not found.
  echo Run install_windows.bat first.
  pause
  exit /b 1
)

if exist "ffmpeg.exe" (
  set "PATH=%CD%;%PATH%"
) else (
  where ffmpeg >nul 2>nul
  if errorlevel 1 (
    echo ERROR: FFmpeg was not found.
    echo Put ffmpeg.exe in this folder or install FFmpeg system-wide.
    pause
    exit /b 1
  )
)

if "%HAMSA_TELEGRAM_BOT_TOKEN%"=="" (
  echo ERROR: HAMSA_TELEGRAM_BOT_TOKEN is not set.
  echo.
  echo 1. In Telegram, message @BotFather and create a bot.
  echo 2. Copy the token BotFather gives you.
  echo 3. In this same window, run:
  echo    set HAMSA_TELEGRAM_BOT_TOKEN=PASTE_YOUR_TOKEN_HERE
  echo 4. Then run run_telegram_bot.bat again from that window.
  echo.
  pause
  exit /b 1
)

python -m hamsa_caption_engine.telegram_bot
pause
