# F.R.I.D.A.Y. web UI (Vite)
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location (Join-Path $root "apps\web")

if (-not (Test-Path "node_modules")) {
  Write-Host "Installing npm dependencies…"
  npm install
}

if (-not $env:VITE_AGENT_API_BASE) {
  # Empty = use Vite proxy to :8090
  $env:VITE_AGENT_API_BASE = ""
}

Write-Host "Web UI → http://127.0.0.1:5173 (API proxy → 8090)"
# Avoid `npm run -- --host` on Windows (flags get stripped → vite treats host as root dir)
npx --yes vite --host 127.0.0.1 --port 5173
