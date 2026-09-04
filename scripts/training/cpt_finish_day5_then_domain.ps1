"""Resume Day 5 CPT from latest checkpoint, then prepare domain Day 6 (no Day 6 train).

Usage (GPU free, LM Studio closed):
  .\scripts\cpt_finish_day5_then_domain.ps1
"""

$ErrorActionPreference = "Stop"
Set-Location (Resolve-Path (Join-Path $PSScriptRoot "..\.."))

$env:TRANSFORMERS_NO_TF = "1"
$env:USE_TF = "0"
$env:USE_TORCH = "1"
$env:PYTHONIOENCODING = "utf-8"

Write-Host "=== CPT Day 5 resume (checkpoint latest → 320) ==="
python -u -m friday_llm.training.continued_pretraining.smoke --config friday-llm/configs/incremental/cpt_day_5.yaml 2>&1 |
    Tee-Object -FilePath "friday-llm\reports\incremental\cpt_day_5_final.log"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== Prepare Day 6 with domain docs (no train) ==="
& "$PSScriptRoot\cpt_prepare_domain_day.ps1" -Day 6 -Add 20
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host @"

Day 5 CPT done. Day 6 config ready.
Next:
  1. .\scripts\cpt_day_6.ps1
  2. .\scripts\incremental_export_eval.ps1
"@
