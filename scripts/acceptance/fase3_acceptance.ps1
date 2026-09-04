#Requires -Version 5.1
<#
.SYNOPSIS
    Fase 3.0 foundation acceptance (HA/MQTT docs + compose profiles + pytest).
#>
param(
    [switch]$RequireHomeAssistant
)

$ErrorActionPreference = "Continue"
$Root = Resolve-Path (Join-Path $PSScriptRoot "..\..")
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

Write-Host "=== Fase 3.0 acceptance (casa inteligente - fundacao) ===" -ForegroundColor Cyan

Set-Check "docs_readme" (Test-Path (Join-Path $Root "docs\fase-3\README.md")) ""
Set-Check "docs_ha" (Test-Path (Join-Path $Root "docs\fase-3\home-assistant.md")) ""
Set-Check "docs_mqtt" (Test-Path (Join-Path $Root "docs\fase-3\mqtt.md")) ""
Set-Check "docs_frigate" (Test-Path (Join-Path $Root "docs\fase-3\frigate.md")) ""
Set-Check "docs_skills" (Test-Path (Join-Path $Root "docs\fase-3\skills-contract.md")) ""
Set-Check "mosquitto_conf" (Test-Path (Join-Path $Root "deploy\mosquitto\mosquitto.conf")) ""
Set-Check "frigate_stub" (Test-Path (Join-Path $Root "deploy\frigate\config.yml")) ""

$compose = Get-Content (Join-Path $Root "docker-compose.yml") -Raw
Set-Check "compose_mqtt" ($compose -match "mosquitto" -and $compose -match "profiles") ""
Set-Check "compose_ha" ($compose -match "homeassistant") ""
Set-Check "compose_frigate_profile" ($compose -match "frigate" -and $compose -match "profiles:\s*\[`"frigate`"\]") ""

& $py -m pytest tests/test_fase3_ha.py -q --tb=line
Set-Check "pytest_fase3" ($LASTEXITCODE -eq 0) "exit=$LASTEXITCODE"

$code = @'
from friday.config import Settings
from friday.skills.registry import default_registry
n = set(default_registry(Settings(ha_enabled=True)).names())
assert "ha_get_status" in n and "ha_list_entities" in n
print("ok")
'@
$code | & $py -
Set-Check "skills_ha_enabled" ($LASTEXITCODE -eq 0) ""

$ha = $false
try {
    $r = Invoke-WebRequest -Uri "http://127.0.0.1:8123/" -TimeoutSec 3 -UseBasicParsing
    $ha = ($r.StatusCode -ge 200 -and $r.StatusCode -lt 500)
} catch { $ha = $false }
Set-Check "live_homeassistant" $ha "localhost:8123"

if ($RequireHomeAssistant -and -not $ha) {
    $report.passed = $false
} elseif (-not $RequireHomeAssistant -and -not $ha) {
    $report.checks["live_homeassistant"].detail = "localhost:8123 (opcional offline)"
    $report.passed = $true
    foreach ($k in $report.checks.Keys) {
        if ($k -eq "live_homeassistant") { continue }
        if (-not $report.checks[$k].ok) { $report.passed = $false }
    }
}

$out = Join-Path $Root "docs\fase-3\acceptance-last.json"
($report | ConvertTo-Json -Depth 6) | Set-Content -Path $out -Encoding utf8
Write-Host ""
Write-Host ("Report: {0}" -f $out)
if ($report.passed) {
    Write-Host "Fase 3.0 automated gates PASSED." -ForegroundColor Green
    exit 0
} else {
    Write-Host "Fase 3.0 automated gates FAILED." -ForegroundColor Red
    exit 1
}
