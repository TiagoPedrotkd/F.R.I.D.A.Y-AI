#Requires -Version 5.1
<#
.SYNOPSIS
    Fase 2 live setup: productivity deps + Radicale + .env CalDAV defaults.
#>
param(
    [switch]$SkipDocker,
    [switch]$SkipPip
)

$ErrorActionPreference = "Continue"
$Root = Resolve-Path (Join-Path $PSScriptRoot "..\..")
Set-Location $Root
$py = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $py)) { $py = "python" }

Write-Host "=== Fase 2 live setup ===" -ForegroundColor Cyan

if (-not $SkipPip) {
    Write-Host "Installing productivity extras..."
    & $py -m pip install -e ".[productivity]" -q
    if ($LASTEXITCODE -ne 0) {
        Write-Host "pip install failed" -ForegroundColor Red
        exit 1
    }
    Write-Host "[OK] pip productivity"
}

# Ensure CalDAV defaults in .env without overwriting secrets
$envPath = Join-Path $Root ".env"
$defaults = @{
    "CALDAV_ENABLED" = "true"
    "CALDAV_URL" = "http://127.0.0.1:5232/friday/friday/"
    "CALDAV_USER" = "friday"
    "CALDAV_PASSWORD" = "friday"
    "CALDAV_PORT" = "5232"
}
if (Test-Path $envPath) {
    $raw = Get-Content $envPath -Raw -ErrorAction SilentlyContinue
    foreach ($k in $defaults.Keys) {
        if ($raw -notmatch "(?m)^\s*$k\s*=") {
            Add-Content $envPath "`n$k=$($defaults[$k])"
            Write-Host "[OK] appended $k to .env"
        }
    }
} else {
    Copy-Item (Join-Path $Root ".env.example") $envPath -ErrorAction SilentlyContinue
    Write-Host "[OK] created .env from example (edit IMAP secrets manually)"
}

if (-not $SkipDocker) {
    Write-Host "Starting Radicale..."
    docker compose up -d radicale
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[WARN] docker compose radicale failed — start Docker Desktop and retry" -ForegroundColor Yellow
    } else {
        Start-Sleep -Seconds 2
        try {
            $r = Invoke-WebRequest "http://127.0.0.1:5232/" -TimeoutSec 5 -UseBasicParsing
            Write-Host "[OK] radicale $($r.StatusCode)"
        } catch {
            Write-Host "[WARN] radicale not reachable yet: $($_.Exception.Message)" -ForegroundColor Yellow
        }
    }
}

Write-Host ""
Write-Host "Next: set EMAIL_* in .env if you want IMAP; then .\scripts\run-agent-api.ps1"
Write-Host "Smoke: .\scripts\fase2_acceptance.ps1 -RequireRadicale"
exit 0
