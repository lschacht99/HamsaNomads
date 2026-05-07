@echo off
setlocal
cd /d "%~dp0"

echo ========================================
echo Hamsa Caption Engine - Windows Installer
echo ========================================
echo.

where python >nul 2>nul
if errorlevel 1 (
  echo ERROR: Python was not found.
  echo.
  echo Install Python 3.10 or newer from:
  echo https://www.python.org/downloads/windows/
  echo.
  echo During install, check: Add python.exe to PATH
  echo Then double click install_windows.bat again.
  pause
  exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
  echo Creating local Python environment in .venv ...
  python -m venv .venv
  if errorlevel 1 (
    echo ERROR: Could not create .venv.
    pause
    exit /b 1
  )
) else (
  echo Found existing .venv.
)

echo Updating pip ...
".venv\Scripts\python.exe" -m pip install --upgrade pip
if errorlevel 1 (
  echo ERROR: pip update failed.
  pause
  exit /b 1
)

echo Installing Hamsa Caption Engine ...
".venv\Scripts\python.exe" -m pip install -e .
if errorlevel 1 (
  echo ERROR: package install failed.
  pause
  exit /b 1
)

echo.
if exist "ffmpeg.exe" (
  echo Found ffmpeg.exe in this project folder.
) else (
  echo FFmpeg check: ffmpeg.exe is NOT in this project folder.
  where ffmpeg >nul 2>nul
  if errorlevel 1 (
    echo.
    echo IMPORTANT: FFmpeg is still needed before rendering videos.
    echo.
    echo Easy option:
    echo   1. Download a Windows FFmpeg build.
    echo   2. Copy ffmpeg.exe into this same folder as install_windows.bat.
    echo.
    echo Alternative option:
    echo   Install FFmpeg system-wide, then reopen this folder and run run_hamsa.bat.
    echo   With winget, this command often works:
    echo     winget install --id Gyan.FFmpeg -e
    echo.
  ) else (
    echo ffmpeg was found on your Windows PATH, so the app can use it.
    echo Optional: you may also copy ffmpeg.exe into this folder.
  )
)

echo.
echo Install step finished.
echo Next: put one MP4 in the input folder, then double click run_hamsa.bat.
echo.
pause
