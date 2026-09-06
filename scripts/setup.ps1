#Requires -Version 5.1
<#
.SYNOPSIS
  One-shot onboarding setup for F.R.I.D.A.Y-AI (Windows).
#>
$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

Write-Host "`n=== F.R.I.D.A.Y. setup ===" -ForegroundColor Cyan
Write-Host "Repo root: $Root`n"

function Assert-Cmd($Name) {
  if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
    Write-Host "Missing required command: $Name" -ForegroundColor Red
    Write-Host "See SETUP.md prerequisites." -ForegroundColor Yellow
    exit 1
  }
}

Assert-Cmd node
Assert-Cmd npm

$nodeVer = (node -v) -replace '^v', ''
$major = [int]($nodeVer.Split('.')[0])
if ($major -lt 20) {
  Write-Host "Node $nodeVer detected — need Node 20+." -ForegroundColor Red
  exit 1
}
Write-Host "Node $(node -v) OK"

$envExample = Join-Path $Root '.env.example'
$envFile = Join-Path $Root '.env'
if ((Test-Path $envExample) -and -not (Test-Path $envFile)) {
  Copy-Item $envExample $envFile
  Write-Host "Created .env from .env.example — edit LM_STUDIO_MODEL if needed." -ForegroundColor Yellow
} elseif (Test-Path $envFile) {
  Write-Host ".env already present"
} else {
  Write-Host "No .env.example found — skip env copy"
}

Write-Host "`nInstalling root dependencies (Husky / lint-staged)..."
npm install

Write-Host "`nInstalling apps/web dependencies..."
Push-Location (Join-Path $Root 'apps\web')
npm install
Pop-Location

Write-Host "`nEnsuring git hooks..."
npx husky

Write-Host "`n=== Setup complete ===" -ForegroundColor Green
Write-Host @"

Next (two terminals):

  1) Agent API (port 8090):
     .\scripts\run-agent-api.ps1

  2) Web UI (port 5173):
     .\scripts\run-web-ui.ps1

Optional: start LM Studio local server on :1234 first.

Docs: SETUP.md · docs/CONTRIBUTING.md · docs/TROUBLESHOOTING.md

"@
