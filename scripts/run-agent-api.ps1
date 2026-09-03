# F.R.I.D.A.Y. agent API
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$env:AGENT_API_HOST = if ($env:AGENT_API_HOST) { $env:AGENT_API_HOST } else { "127.0.0.1" }
$env:AGENT_API_PORT = if ($env:AGENT_API_PORT) { $env:AGENT_API_PORT } else { "8090" }
$env:HEALTHCHECK_URL = if ($env:HEALTHCHECK_URL) { $env:HEALTHCHECK_URL } else { "http://127.0.0.1:8080" }

# Prefer project venv so voice extras (piper, whisper) resolve correctly
$venvPython = Join-Path $root ".venv\Scripts\python.exe"
if (Test-Path $venvPython) {
  $python = $venvPython
} else {
  $python = "python"
  Write-Warning "Sem .venv - a usar python do PATH. Instala com: pip install -e '.[voice,api]'"
}

Write-Host "Starting agent-api on http://$($env:AGENT_API_HOST):$($env:AGENT_API_PORT)"
Write-Host "Python: $python"
# Keep repo root as CWD so relative .env paths (RAG_INDEX_DIR, sessions, etc.) resolve
Set-Location $root
& $python -m uvicorn main:app --app-dir (Join-Path $root "services\agent-api") --host $env:AGENT_API_HOST --port $env:AGENT_API_PORT
