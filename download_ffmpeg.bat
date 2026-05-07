@echo off
setlocal EnableExtensions
cd /d "%~dp0"
set "FFDIR=tools\ffmpeg"
set "BINDIR=%FFDIR%\bin"
set "ZIP=%FFDIR%\ffmpeg-release-essentials.zip"
set "URL=https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"
mkdir "%FFDIR%" 2>nul
mkdir "%BINDIR%" 2>nul
echo Downloading FFmpeg essentials from %URL%
powershell -NoProfile -ExecutionPolicy Bypass -Command "try { Invoke-WebRequest -Uri '%URL%' -OutFile '%ZIP%' -UseBasicParsing; exit 0 } catch { Write-Host $_; exit 1 }"
if errorlevel 1 goto manual
rmdir /s /q "%FFDIR%\_extract" 2>nul
mkdir "%FFDIR%\_extract"
powershell -NoProfile -ExecutionPolicy Bypass -Command "try { Expand-Archive -Path '%ZIP%' -DestinationPath '%FFDIR%\_extract' -Force; exit 0 } catch { Write-Host $_; exit 1 }"
if errorlevel 1 goto manual
for /r "%FFDIR%\_extract" %%F in (ffmpeg.exe) do copy /Y "%%F" "%BINDIR%\ffmpeg.exe" >nul
for /r "%FFDIR%\_extract" %%F in (ffprobe.exe) do copy /Y "%%F" "%BINDIR%\ffprobe.exe" >nul
if exist "%BINDIR%\ffmpeg.exe" if exist "%BINDIR%\ffprobe.exe" (
  echo FFmpeg installed to %BINDIR%.
  exit /b 0
)
:manual
echo Automatic FFmpeg setup failed.
echo Manual instructions:
echo 1. Download ffmpeg-release-essentials.zip from https://www.gyan.dev/ffmpeg/builds/
echo 2. Extract it.
echo 3. Put ffmpeg.exe and ffprobe.exe inside tools\ffmpeg\bin\
exit /b 1
