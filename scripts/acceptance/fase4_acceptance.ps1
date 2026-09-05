#Requires -Version 5.1
<#
.SYNOPSIS
    Fase 4 acceptance (Google OAuth / health / providers docs + pytest).
#>
param(
    [switch]$RequireGoogle
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

Write-Host "=== Fase 4 acceptance (Google + Saude) ===" -ForegroundColor Cyan

Set-Check "docs_readme" (Test-Path (Join-Path $Root "docs\fase-4\README.md")) ""
Set-Check "docs_oauth" (Test-Path (Join-Path $Root "docs\fase-4\google-oauth.md")) ""
Set-Check "docs_saude" (Test-Path (Join-Path $Root "docs\fase-4\saude.md")) ""
Set-Check "docs_cal_mail" (Test-Path (Join-Path $Root "docs\fase-4\calendar-gmail.md")) ""
Set-Check "docs_skills" (Test-Path (Join-Path $Root "docs\fase-4\skills-contract.md")) ""
Set-Check "oauth_module" (Test-Path (Join-Path $Root "friday\integrations\google_oauth.py")) ""
Set-Check "health_module" (Test-Path (Join-Path $Root "friday\integrations\google_health.py")) ""
Set-Check "calendar_provider" (Test-Path (Join-Path $Root "friday\productivity\calendar_provider.py")) ""
Set-Check "email_provider" (Test-Path (Join-Path $Root "friday\productivity\email_provider.py")) ""
Set-Check "saude_panel" (Test-Path (Join-Path $Root "apps\web\src\components\SaudePanel.tsx")) ""

& $py -m pytest tests/test_fase4_google.py -q --tb=line
Set-Check "pytest_fase4" ($LASTEXITCODE -eq 0) "exit=$LASTEXITCODE"

$code = @'
from friday.config import Settings
from friday.skills.registry import default_registry
n = set(default_registry(Settings()).names())
assert "get_health_summary" in n and "get_health_day" in n
print("ok")
'@
$code | & $py -
Set-Check "skills_health" ($LASTEXITCODE -eq 0) ""

if ($RequireGoogle) {
    try {
        $r = Invoke-WebRequest -Uri "http://127.0.0.1:8090/v1/google/status" -TimeoutSec 5 -UseBasicParsing
        Set-Check "live_google_status" ($r.StatusCode -eq 200) "status=$($r.StatusCode)"
    } catch {
        Set-Check "live_google_status" $false $_.Exception.Message
    }
}

$outDir = Join-Path $Root "docs\fase-4"
New-Item -ItemType Directory -Force -Path $outDir | Out-Null
$report | ConvertTo-Json -Depth 6 | Set-Content (Join-Path $outDir "acceptance-last.json") -Encoding utf8
if ($report.passed) {
    Write-Host "PASSED" -ForegroundColor Green
    exit 0
}
Write-Host "FAILED" -ForegroundColor Red
exit 1
