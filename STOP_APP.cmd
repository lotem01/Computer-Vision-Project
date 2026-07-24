@echo off
setlocal
cd /d "%~dp0"

echo.
echo ===============================================
echo   PoseLab Studio - shutdown
echo ===============================================
echo.

set FOUND=0
for /f "tokens=5" %%P in ('netstat -ano ^| findstr /R /C:":8000 .*LISTENING"') do (
  set FOUND=1
  echo Stopping local PoseLab server on port 8000, PID %%P...
  taskkill /PID %%P /F
)

if "%FOUND%"=="0" (
  echo No local PoseLab server was found on port 8000.
) else (
  echo PoseLab server stopped.
)

echo.
echo Cleaning generated video and preview artifacts...
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0cleanup_runtime.ps1"
if errorlevel 1 (
  echo Runtime cleanup failed. Keep this window open and read the error above.
)

echo.
pause
