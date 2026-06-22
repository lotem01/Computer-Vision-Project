$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path

Write-Host 'Creating Python environment...'
$PythonCommand = if (Get-Command py -ErrorAction SilentlyContinue) { @('py', '-3.9') } else { @('python') }
if (-not (Test-Path "$Root\.venv")) {
  if ($PythonCommand.Count -gt 1) { & $PythonCommand[0] $PythonCommand[1] -m venv "$Root\.venv" }
  else { & $PythonCommand[0] -m venv "$Root\.venv" }
  if ($LASTEXITCODE -ne 0) { throw 'Could not create the Python virtual environment.' }
}
& "$Root\.venv\Scripts\python.exe" -m pip install --upgrade pip
if ($LASTEXITCODE -ne 0) { throw 'Could not install pip.' }
& "$Root\.venv\Scripts\python.exe" -m pip install --no-cache-dir -r "$Root\backend\requirements.txt"
if ($LASTEXITCODE -ne 0) { throw 'Could not install Python dependencies.' }

Write-Host 'Installing frontend packages...'
Push-Location "$Root\frontend"
try {
  npm install --offline=false
  if ($LASTEXITCODE -ne 0) { throw 'Could not install frontend dependencies.' }
  npm run build
  if ($LASTEXITCODE -ne 0) { throw 'Could not build the frontend.' }
} finally { Pop-Location }

Write-Host 'PoseLab is ready. Run .\start.ps1'
