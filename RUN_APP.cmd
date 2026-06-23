@echo off
setlocal
cd /d "%~dp0"

echo.
echo ===============================================
echo   PoseLab Studio - one click local launcher
echo ===============================================
echo.

if not exist ".venv\Scripts\python.exe" (
  echo First run detected: preparing Python and React dependencies...
  powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0setup.ps1"
  if errorlevel 1 (
    echo.
    echo Setup failed. Keep this window open and read the error above.
    pause
    exit /b 1
  )
)

if not exist "frontend\dist\index.html" (
  echo Building the presentation UI...
  pushd frontend
  call npm run build
  if errorlevel 1 (
    popd
    echo.
    echo Frontend build failed. Keep this window open and read the error above.
    pause
    exit /b 1
  )
  popd
)

echo Starting local app at http://127.0.0.1:8000
start "" "http://127.0.0.1:8000"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0start.ps1"

echo.
echo PoseLab stopped.
pause
