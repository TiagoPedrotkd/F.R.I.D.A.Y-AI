# Após CPT incremental suficiente: select best → SFT Fase 4.
# Uso (quando TU decidires que há docs/steps suficientes):
#   .\scripts\incremental_after_cpt.ps1
#
# Não troca Phi-4 automaticamente. Export/eval ficam manuais após SFT.

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root

$env:TRANSFORMERS_NO_TF = "1"
$env:USE_TF = "0"
$env:USE_TORCH = "1"
$env:PYTHONIOENCODING = "utf-8"

$runDir = "friday-llm\checkpoints\cpt-incremental"
if (-not (Test-Path $runDir)) {
    Write-Error "Sem checkpoints em $runDir — corre dias de CPT incremental primeiro."
}

Write-Host "Select best adapter (cpt-incremental)..."
python -m friday_llm.training.continued_pretraining.select_checkpoint `
    --run-dir friday-llm/checkpoints/cpt-incremental `
    --dest friday-llm/checkpoints/cpt-incremental-best/adapter `
    --metrics friday-llm/reports/incremental/checkpoint_metrics.jsonl
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "SFT Fase 4 a partir do adapter incremental..."
python -m friday_llm.training.sft.cli --config friday-llm/configs/fase4_sft_incremental.yaml 2>&1 |
    Tee-Object -FilePath "friday-llm\reports\incremental\sft_after_cpt.log"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host @"

SFT concluido.
Proximos passos:
  .\scripts\incremental_export_eval.ps1 -SkipSft [-RunEval]
  (ou manual: export + eval gate + so entao LM_STUDIO_MODEL)

Ver friday-llm/docs/AFTER_INCREMENTAL_SFT.md
"@
