$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = "$Root\.venv\Scripts\python.exe"
if (-not (Test-Path $Python)) { throw 'Run .\setup.ps1 first.' }

Write-Host 'PoseLab is starting at http://127.0.0.1:8000'
Write-Host 'All four models will preload before the studio opens. Press Ctrl+C to stop.'
Push-Location "$Root\backend"
try { & $Python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 }
finally {
  Pop-Location
  Write-Host 'Cleaning generated video and preview artifacts...'
  & powershell -NoProfile -ExecutionPolicy Bypass -File "$Root\cleanup_runtime.ps1"
}
