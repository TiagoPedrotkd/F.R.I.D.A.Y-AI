# CPT incremental - Dia 5
# Docs primeiro; duracao flexivel (pode ser menos de 1h).
$ErrorActionPreference = "Stop"
Set-Location (Resolve-Path (Join-Path $PSScriptRoot "..\.."))

$env:TRANSFORMERS_NO_TF = "1"
$env:USE_TF = "0"
$env:USE_TORCH = "1"
$env:PYTHONIOENCODING = "utf-8"

Write-Host "CPT incremental Dia 5 - config friday-llm/configs/incremental/cpt_day_5.yaml"
python -m friday_llm.training.continued_pretraining.smoke --config friday-llm/configs/incremental/cpt_day_5.yaml
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host "Dia 5 concluido. Ver friday-llm/reports/incremental/progress.md"
