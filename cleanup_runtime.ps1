param(
  [switch]$DryRun
)

$ErrorActionPreference = 'Stop'

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$JobsDir = Join-Path $Root 'backend\runtime\jobs'

if (-not (Test-Path $JobsDir)) {
  New-Item -ItemType Directory -Path $JobsDir | Out-Null
}

$ResolvedRoot = (Resolve-Path $Root).Path
$ResolvedJobs = (Resolve-Path $JobsDir).Path

if (-not $ResolvedJobs.StartsWith($ResolvedRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
  throw "Safety check failed: jobs directory is outside the project root."
}

$Items = Get-ChildItem -LiteralPath $ResolvedJobs -Force | Where-Object { $_.Name -ne '.gitkeep' }

if ($Items.Count -eq 0) {
  Write-Host 'Runtime cleanup: no generated video/image artifacts found.'
} elseif ($DryRun) {
  Write-Host "Runtime cleanup dry run: would remove $($Items.Count) generated artifact(s)."
  $Items | ForEach-Object { Write-Host "  $($_.FullName)" }
} else {
  $Items | Remove-Item -Force -Recurse
  Write-Host "Runtime cleanup: removed $($Items.Count) generated artifact(s)."
}

$Gitkeep = Join-Path $ResolvedJobs '.gitkeep'
if (-not (Test-Path $Gitkeep)) {
  Set-Content -Path $Gitkeep -Value '' -NoNewline
}
