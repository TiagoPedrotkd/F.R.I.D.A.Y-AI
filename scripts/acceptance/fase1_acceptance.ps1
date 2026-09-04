#Requires -Version 5.1
<#
.SYNOPSIS
    Fase 1 acceptance: automated gates + report for checklist-conclusao.
.DESCRIPTION
    Validates code/tests, MCP import, Piper assets, optional live LM/API/web.
    Writes friday-llm/reports is wrong place — writes docs/fase-1/acceptance-last.json
#>
param(
    [switch]$RequireLive
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

Write-Host "=== Fase 1 acceptance ===" -ForegroundColor Cyan

# Unit tests (core Fase 1)
& $py -m pytest tests/test_agent_api.py tests/test_conversacao_skills.py tests/test_intent_router.py tests/test_tool_runner.py tests/test_roadmap_features.py -q --tb=line
Set-Check "pytest_fase1" ($LASTEXITCODE -eq 0) "exit=$LASTEXITCODE"

# MCP import + tool call (Cursor UI toggle still local, but server is verified)
& $py -c "from friday.mcp_server import server; print('ok')"
Set-Check "mcp_import" ($LASTEXITCODE -eq 0) ""

$mcpToolOut = & $py -c @"
import asyncio
from friday.mcp_server.server import create_mcp_server
async def main():
    m = create_mcp_server()
    tools = await m.list_tools()
    names = sorted(t.name for t in tools)
    assert 'get_current_datetime' in names, names
    r = await m.call_tool('get_current_datetime', {'timezone': 'Europe/Lisbon'})
    assert not getattr(r, 'is_error', False), r
    print('ok', ','.join(names))
asyncio.run(main())
"@
Set-Check "mcp_tool_call" ($LASTEXITCODE -eq 0) ("$mcpToolOut".Trim())

# MCP cursor config
$mcp = Join-Path $Root ".cursor\mcp.json"
Set-Check "mcp_json" (Test-Path $mcp) $mcp

# Piper voice file
$piperRel = ""
Get-Content (Join-Path $Root ".env") -ErrorAction SilentlyContinue | ForEach-Object {
    if ($_ -match '^\s*PIPER_VOICE\s*=\s*(.+)\s*$') { $piperRel = $Matches[1].Trim() }
}
if (-not $piperRel) { $piperRel = "models/piper/en_GB-cori-high.onnx" }
$piperPath = Join-Path $Root ($piperRel -replace '/', '\')
Set-Check "piper_voice" (Test-Path $piperPath) $piperRel

# Web package
Set-Check "web_package" (Test-Path (Join-Path $Root "apps\web\package.json")) ""

# Live probes
function Test-Url([string]$Url) {
    try {
        $r = Invoke-WebRequest -Uri $Url -TimeoutSec 3 -UseBasicParsing
        return ($r.StatusCode -ge 200 -and $r.StatusCode -lt 500)
    } catch { return $false }
}

$lm = Test-Url "http://127.0.0.1:1234/v1/models"
$api = Test-Url "http://127.0.0.1:8090/health"
$web = Test-Url "http://127.0.0.1:5173/"
$ready = $false
if ($api) {
    try {
        $j = Invoke-RestMethod -Uri "http://127.0.0.1:8090/health/ready" -TimeoutSec 15
        $ready = [bool]$j.ready
    } catch { $ready = $false }
}

Set-Check "live_lm_studio" $lm "localhost:1234"
Set-Check "live_agent_api" $api "localhost:8090"
Set-Check "live_ready" $ready "/health/ready"
Set-Check "live_web_ui" $web "localhost:5173"

if ($RequireLive) {
    if (-not ($lm -and $api)) {
        $report.passed = $false
    }
} else {
    # Offline mode: live failures are warnings, not hard fail
    foreach ($k in @("live_lm_studio", "live_agent_api", "live_ready", "live_web_ui")) {
        if (-not $report.checks[$k].ok) {
            $report.checks[$k].detail = ($report.checks[$k].detail + " (opcional offline)")
        }
    }
    # Recompute passed ignoring live_*
    $report.passed = $true
    foreach ($k in $report.checks.Keys) {
        if ($k -like "live_*") { continue }
        if (-not $report.checks[$k].ok) { $report.passed = $false }
    }
}

$out = Join-Path $Root "docs\fase-1\acceptance-last.json"
($report | ConvertTo-Json -Depth 6) | Set-Content -Path $out -Encoding utf8
Write-Host ""
Write-Host ("Report: {0}" -f $out)
if ($report.passed) {
    Write-Host "Fase 1 automated gates PASSED." -ForegroundColor Green
    exit 0
} else {
    Write-Host "Fase 1 automated gates FAILED." -ForegroundColor Red
    exit 1
}
