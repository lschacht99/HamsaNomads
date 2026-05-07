@echo off
setlocal EnableExtensions
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Missing .venv\Scripts\python.exe. Run install_windows.bat first.
  pause
  exit /b 1
)
if not exist "input\test.mp4" (
  echo Put your MP4 at input\test.mp4 first.
  pause
  exit /b 1
)
set /p PROMPT="Prompt (or leave blank for clean style): "
if "%PROMPT%"=="" (
  .venv\Scripts\python.exe -m hamsa_caption_engine --input input\test.mp4 --output-dir output --style hamsa-clean --renderer ffmpeg --auto-cut
) else (
  .venv\Scripts\python.exe -m hamsa_caption_engine --input input\test.mp4 --output-dir output --prompt "%PROMPT%" --renderer ffmpeg --auto-cut
)
if errorlevel 1 pause
