#Requires -Version 5.1
<#
.SYNOPSIS
    Fase 2 product acceptance (CalDAV/IMAP skills + docs + desktop scaffold).
#>
param(
    [switch]$RequireRadicale
)

$ErrorActionPreference = "Continue"
$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $Root
$env:PYTHONIOENCODING = "utf-8"
$py = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $py)) { $py = "python" }

$report = [ordered]@{
    at = (Get-Date).ToUniversalTime().ToString("o")
    checks = [ordered]@{}
    passed = $true
}

function Set-Check([string]$Name, [bool]$Ok, [string]$Detail = "") {
    $script:report.checks[$Name] = @{ ok = $Ok; detail = $Detail }
    if (-not $Ok) { $script:report.passed = $false }
    $color = if ($Ok) { "Green" } else { "Red" }
    Write-Host ("[{0}] {1} {2}" -f ($(if ($Ok) { "OK" } else { "FAIL" }), $Name, $Detail)) -ForegroundColor $color
}

Write-Host "=== Fase 2 acceptance (produto) ===" -ForegroundColor Cyan

Set-Check "docs_readme" (Test-Path (Join-Path $Root "docs\fase-2\README.md")) ""
Set-Check "docs_caldav" (Test-Path (Join-Path $Root "docs\fase-2\caldav.md")) ""
Set-Check "docs_email" (Test-Path (Join-Path $Root "docs\fase-2\email-imap.md")) ""
Set-Check "docs_tauri" (Test-Path (Join-Path $Root "docs\fase-2\desktop-tauri.md")) ""
Set-Check "desktop_scaffold" (Test-Path (Join-Path $Root "apps\desktop\src-tauri\tauri.conf.json")) ""
Set-Check "compose_radicale" ((Get-Content (Join-Path $Root "docker-compose.yml") -Raw) -match "radicale") ""

& $py -m pytest tests/test_fase2_productivity.py tests/test_fase2_vision.py -q --tb=line
Set-Check "pytest_fase2" ($LASTEXITCODE -eq 0) "exit=$LASTEXITCODE"

& $py -c "from friday.skills.registry import default_registry; n=set(default_registry().names()); assert 'list_calendar_events' in n and 'send_email' in n; print('ok', len(n))"
Set-Check "skills_registered" ($LASTEXITCODE -eq 0) ""

$radicale = $false
try {
    $r = Invoke-WebRequest -Uri "http://127.0.0.1:5232/" -TimeoutSec 3 -UseBasicParsing
    $radicale = ($r.StatusCode -ge 200 -and $r.StatusCode -lt 500)
} catch { $radicale = $false }
Set-Check "live_radicale" $radicale "localhost:5232"

if ($RequireRadicale -and -not $radicale) {
    $report.passed = $false
} elseif (-not $RequireRadicale -and -not $radicale) {
    $report.checks["live_radicale"].detail = "localhost:5232 (opcional offline)"
    # recompute passed ignoring optional live_radicale
    $report.passed = $true
    foreach ($k in $report.checks.Keys) {
        if ($k -eq "live_radicale") { continue }
        if (-not $report.checks[$k].ok) { $report.passed = $false }
    }
}

$out = Join-Path $Root "docs\fase-2\acceptance-last.json"
($report | ConvertTo-Json -Depth 6) | Set-Content -Path $out -Encoding utf8
Write-Host ""
Write-Host ("Report: {0}" -f $out)
if ($report.passed) {
    Write-Host "Fase 2 automated gates PASSED." -ForegroundColor Green
    exit 0
} else {
    Write-Host "Fase 2 automated gates FAILED." -ForegroundColor Red
    exit 1
}
