@echo off
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0"

echo ========================================
echo Hamsa Caption Engine
echo ========================================
echo.

if exist ".venv\Scripts\activate.bat" (
  call ".venv\Scripts\activate.bat"
)

where python >nul 2>nul
if errorlevel 1 (
  echo ERROR: Python was not found.
  echo Run install_windows.bat first. If that fails, install Python from python.org
  echo and check "Add python.exe to PATH" during install.
  pause
  exit /b 1
)

if exist "ffmpeg.exe" (
  set "PATH=%CD%;%PATH%"
) else (
  where ffmpeg >nul 2>nul
  if errorlevel 1 (
    echo ERROR: FFmpeg was not found.
    echo.
    echo Put ffmpeg.exe in this project folder, or install FFmpeg system-wide.
    echo If you have winget, you can run:
    echo   winget install --id Gyan.FFmpeg -e
    echo.
    pause
    exit /b 1
  )
)

set "INPUT_VIDEO="
for %%F in (input\*.mp4) do (
  if not defined INPUT_VIDEO if exist "%%~fF" set "INPUT_VIDEO=%%~fF"
)

if not defined INPUT_VIDEO (
  echo ERROR: No MP4 file was found in the input folder.
  echo Put one .mp4 video inside:
  echo   %CD%\input
  echo.
  pause
  exit /b 1
)

echo Found video:
echo   %INPUT_VIDEO%
echo.

echo Choose caption style:
echo   1. game
echo   2. paris-tip
echo   3. hamsa-clean
echo   4. wrong-vs-right
echo   5. video-game-dialogue
echo.
set /p STYLE_CHOICE="Type 1, 2, 3, 4, or 5, then press Enter: "
if "%STYLE_CHOICE%"=="1" set "STYLE=game"
if "%STYLE_CHOICE%"=="2" set "STYLE=paris-tip"
if "%STYLE_CHOICE%"=="3" set "STYLE=hamsa-clean"
if "%STYLE_CHOICE%"=="4" set "STYLE=wrong-vs-right"
if "%STYLE_CHOICE%"=="5" set "STYLE=video-game-dialogue"
if not defined STYLE (
  echo Invalid choice. Using hamsa-clean.
  set "STYLE=hamsa-clean"
)

echo.
echo Caption text mode:
echo   1. Whisper mode - automatic local captions, slower, no paid APIs
echo   2. Transcript mode - use input\transcript.txt, faster for weak PCs
echo.
set /p MODE_CHOICE="Type 1 or 2, then press Enter: "

echo.
echo Running Hamsa Caption Engine with style: %STYLE%
echo Please wait. Weak PCs can take a while, especially in Whisper mode.
echo.

if "%MODE_CHOICE%"=="2" (
  if not exist "input\transcript.txt" (
    echo.
    echo ERROR: Transcript mode needs this file:
    echo   %CD%\input\transcript.txt
    echo.
    echo Put one caption per line in transcript.txt, then run again.
    pause
    exit /b 1
  )
  python -m hamsa_caption_engine --input "%INPUT_VIDEO%" --style %STYLE% --transcript "input\transcript.txt"
) else (
  python -m hamsa_caption_engine --input "%INPUT_VIDEO%" --style %STYLE% --model tiny.en
)

if errorlevel 1 (
  echo.
  echo ERROR: The render failed. Read the message above for details.
  pause
  exit /b 1
)

echo.
echo Done! Opening the output folder ...
start "" "%CD%\output"
pause
