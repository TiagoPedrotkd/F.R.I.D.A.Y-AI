#Requires -Version 5.1
<#
.SYNOPSIS
    Fase 5b acceptance (personal finance ledger docs + pytest).
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

Write-Host "=== Fase 5b acceptance (Financas ledger) ===" -ForegroundColor Cyan

Set-Check "docs_readme" (Test-Path (Join-Path $Root "docs\fase-5\README.md")) ""
Set-Check "docs_schema" (Test-Path (Join-Path $Root "docs\fase-5\schema.md")) ""
Set-Check "docs_skills" (Test-Path (Join-Path $Root "docs\fase-5\skills-contract.md")) ""
Set-Check "no_enablebanking_doc" (-not (Test-Path (Join-Path $Root "docs\fase-5\enablebanking.md"))) ""
Set-Check "module_ledger" (Test-Path (Join-Path $Root "friday\integrations\finance_ledger.py")) ""
Set-Check "no_enable_module" (-not (Test-Path (Join-Path $Root "friday\integrations\enable_banking.py"))) ""
$financasPanel = @(
    (Join-Path $Root "apps\web\src\features\financas\FinancasPanel.tsx"),
    (Join-Path $Root "apps\web\src\components\FinancasPanel.tsx")
) | Where-Object { Test-Path $_ } | Select-Object -First 1
Set-Check "financas_panel" ([bool]$financasPanel) $(if ($financasPanel) { Split-Path $financasPanel -Leaf } else { "missing" })

& $py -m pytest tests/test_fase5_finance.py -q --tb=line
Set-Check "pytest_fase5" ($LASTEXITCODE -eq 0) "exit=$LASTEXITCODE"

$code = @'
from friday.config import Settings
from friday.skills.registry import default_registry
n = set(default_registry(Settings()).names())
assert "get_finance_summary" in n and "set_salary" in n and "get_investment_summary" in n
print("ok")
'@
$code | & $py -
Set-Check "skills_finance" ($LASTEXITCODE -eq 0) ""

if ($RequireLive) {
    try {
        $r = Invoke-WebRequest -Uri "http://127.0.0.1:8090/v1/finance/status" -TimeoutSec 5 -UseBasicParsing
        Set-Check "live_finance_status" ($r.StatusCode -eq 200) "status=$($r.StatusCode)"
    } catch {
        Set-Check "live_finance_status" $false $_.Exception.Message
    }
}

$outDir = Join-Path $Root "docs\fase-5"
New-Item -ItemType Directory -Force -Path $outDir | Out-Null
$report | ConvertTo-Json -Depth 6 | Set-Content (Join-Path $outDir "acceptance-last.json") -Encoding utf8
if ($report.passed) {
    Write-Host "PASSED" -ForegroundColor Green
    exit 0
}
Write-Host "FAILED" -ForegroundColor Red
exit 1
