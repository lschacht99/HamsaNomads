@echo off
setlocal EnableExtensions
cd /d "%~dp0"

echo ========================================
echo Hamsa Caption Engine - One Click Runner
echo ========================================
echo.

if not exist "input\test.mp4" (
  echo ERROR: I could not find your video.
  echo.
  echo Please put your video here:
  echo   %CD%\input\test.mp4
  echo.
  echo Tip: rename your MP4 to test.mp4 and place it inside the input folder.
  echo.
  pause
  exit /b 1
)

if not exist "transcript.txt" (
  echo ERROR: I could not find your transcript.
  echo.
  echo Please create this file:
  echo   %CD%\transcript.txt
  echo.
  echo Put one caption per line in transcript.txt, then run this file again.
  echo.
  pause
  exit /b 1
)

where py >nul 2>nul
if errorlevel 1 (
  echo ERROR: The Windows Python launcher 'py' was not found.
  echo.
  echo Install Python 3.11 from python.org and check "Add python.exe to PATH".
  echo Then run install_windows.bat and try again.
  echo.
  pause
  exit /b 1
)

if not exist "output" mkdir "output"

echo Found video:      input\test.mp4
echo Found transcript: transcript.txt
echo.

echo Choose caption style:
echo   1 game
echo   2 paris-tip
echo   3 hamsa-clean
echo.
set /p STYLE_CHOICE="Type 1, 2, or 3, then press Enter: "

set "STYLE=hamsa-clean"
if "%STYLE_CHOICE%"=="1" set "STYLE=game"
if "%STYLE_CHOICE%"=="2" set "STYLE=paris-tip"
if "%STYLE_CHOICE%"=="3" set "STYLE=hamsa-clean"

echo.
echo Rendering with style: %STYLE%
echo This uses transcript mode, so Whisper is not required.
echo.

py -3.11 -m hamsa_caption_engine --input input\test.mp4 --output-dir output --style %STYLE% --transcript transcript.txt --thumbnail-at 00:00:01
if errorlevel 1 (
  echo.
  echo ERROR: The render failed.
  echo.
  echo Try running install_windows.bat first, and make sure FFmpeg is installed
  echo or ffmpeg.exe is in this project folder.
  echo.
  pause
  exit /b 1
)

echo.
echo Done! Opening the output folder ...
start "" "%CD%\output"
pause
