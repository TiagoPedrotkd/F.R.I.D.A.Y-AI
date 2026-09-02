# Nightly / on-demand smoke eval against the live LM Studio model.
# Usage: .\scripts\eval_nightly.ps1

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root

$env:PYTHONIOENCODING = "utf-8"
$stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$out = "friday-llm\reports\nightly\eval_$stamp.json"
New-Item -ItemType Directory -Force -Path "friday-llm\reports\nightly" | Out-Null

Write-Host "Nightly eval -> $out"
python -m friday_llm.evaluation.run_baseline `
    --eval friday-llm/data/evaluation/friday_eval.jsonl `
    --out $out `
    --limit 20
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

if (Test-Path "friday-llm\reports\baseline_phi4.json") {
    python -m friday_llm.evaluation.compare_runs `
        --baseline friday-llm/reports/baseline_phi4.json `
        --candidate $out `
        --out "friday-llm\reports\nightly\gate_$stamp.json"
}

Write-Host "Done. Feedback dataset: data\feedback\feedback.jsonl"

Write-Host "Exporting feedback hard cases -> SFT/eval..."
python -m friday.quality.feedback_to_datasets `
    --feedback data/feedback/feedback.jsonl `
    --sft-out friday-llm/data/sft/feedback_hard_sft.jsonl `
    --eval-out friday-llm/data/evaluation/feedback_hard_eval.jsonl
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "Building metrics dashboard..."
python -m friday.quality.metrics_dashboard --out data/metrics/dashboard.html
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
