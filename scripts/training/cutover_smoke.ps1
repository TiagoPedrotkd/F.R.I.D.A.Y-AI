# Post-cutover smoke: ping LLM + short eval + readiness.
# Usage:
#   .\scripts\cutover_smoke.ps1
#   .\scripts\cutover_smoke.ps1 -MinPassRate 0.6 -Limit 8

param(
    [double]$MinPassRate = 0.5,
    [int]$Limit = 10,
    [string]$Eval = "friday-llm/data/evaluation/friday_eval.jsonl"
)

$ErrorActionPreference = "Stop"
$Root = Resolve-Path (Join-Path $PSScriptRoot "..\..")
Set-Location $Root
$env:PYTHONIOENCODING = "utf-8"
$stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$outDir = "friday-llm\reports\cutover"
New-Item -ItemType Directory -Force -Path $outDir | Out-Null
$out = Join-Path $outDir "smoke_$stamp.json"

Write-Host "Cutover smoke: LLM eval -> $out"
python -m friday_llm.evaluation.run_baseline --eval $Eval --out $out --limit $Limit
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

# Also try feedback hard eval if present
$hard = "friday-llm\data\evaluation\feedback_hard_eval_latest.jsonl"
if (Test-Path $hard) {
    $hardOut = Join-Path $outDir "smoke_hard_$stamp.json"
    Write-Host "Cutover smoke: feedback hard eval -> $hardOut"
    python -m friday_llm.evaluation.run_baseline --eval $hard --out $hardOut --limit ([Math]::Min(10, $Limit))
}

# Parse pass_rate
$report = Get-Content $out -Raw | ConvertFrom-Json
$rate = [double]$report.pass_rate
Write-Host ("pass_rate={0} model={1}" -f $rate, $report.model)

# Readiness (best-effort)
try {
    $ready = Invoke-RestMethod -Uri "http://127.0.0.1:8090/health/ready" -TimeoutSec 5
    Write-Host ("agent-api ready={0}" -f $ready.ready)
} catch {
    Write-Host "agent-api readiness skipped (not running)"
}

if ($rate -lt $MinPassRate) {
    Write-Host ("SMOKE FAILED: pass_rate {0} < min {1}" -f $rate, $MinPassRate) -ForegroundColor Red
    Write-Host "Consider: .\scripts\model_cutover.ps1 -Rollback"
    exit 2
}

Write-Host "Cutover smoke PASSED." -ForegroundColor Green
