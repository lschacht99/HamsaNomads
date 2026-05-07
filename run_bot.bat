@echo off
setlocal EnableExtensions
cd /d "%~dp0"

echo ========================================
echo Hamsa Caption Engine - Telegram Bot
echo ========================================
echo.

if exist ".venv\Scripts\activate.bat" (
  call ".venv\Scripts\activate.bat"
)

if exist ".env" (
  for /f "usebackq eol=# tokens=1,* delims==" %%A in (".env") do (
    if not "%%A"=="" set "%%A=%%B"
  )
) else (
  echo ERROR: .env was not found.
  echo Create .env with this line:
  echo   HAMSA_TELEGRAM_BOT_TOKEN=your_token_here
  echo.
  pause
  exit /b 1
)

if "%HAMSA_TELEGRAM_BOT_TOKEN%"=="" (
  echo ERROR: HAMSA_TELEGRAM_BOT_TOKEN is missing from .env.
  echo.
  pause
  exit /b 1
)

py -3.11 -m hamsa_caption_engine.telegram_bot
pause
