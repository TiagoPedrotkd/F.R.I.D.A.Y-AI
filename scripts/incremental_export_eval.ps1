# Após CPT incremental: select best → SFT → export (GGUF se llama.cpp) → eval gate.
# Uso:
#   .\scripts\incremental_export_eval.ps1
#   .\scripts\incremental_export_eval.ps1 -SkipSft   # se SFT ja correu
#   .\scripts\incremental_export_eval.ps1 -RunEval   # precisa LM Studio com o candidato

param(
    [switch]$SkipSft,
    [switch]$RunEval
)

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

if (-not $SkipSft) {
    Write-Host "SFT Fase 4 a partir do adapter incremental..."
    python -m friday_llm.training.sft.cli --config friday-llm/configs/fase4_sft_incremental.yaml 2>&1 |
        Tee-Object -FilePath "friday-llm\reports\incremental\sft_after_cpt.log"
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

Write-Host "Export merge (+ GGUF se LLAMA_CPP_PATH)..."
python -m friday_llm.export.cli --config friday-llm/configs/fase6_export_incremental.yaml 2>&1 |
    Tee-Object -FilePath "friday-llm\reports\incremental\export_after_sft.log"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

if ($RunEval) {
    Write-Host "Eval candidato vs baseline Phi-4..."
    python -m friday_llm.evaluation.run_baseline `
        --eval friday-llm/data/evaluation/friday_eval.jsonl `
        --out friday-llm/reports/incremental/phase6_eval_candidate.json
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    python -m friday_llm.evaluation.compare_runs `
        --baseline friday-llm/reports/baseline_phi4.json `
        --candidate friday-llm/reports/incremental/phase6_eval_candidate.json `
        --out friday-llm/reports/incremental/eval_gate.json
}

Write-Host @"

Pipeline CPT→SFT→export concluido.
Cutover opcional (manual):
  1. Carrega o GGUF/HF merge no LM Studio
  2. So se o eval gate passar: define LM_STUDIO_MODEL no .env
  3. Rollback: friday-llm/export/rollback.md

Ver friday-llm/docs/AFTER_INCREMENTAL_SFT.md
"@
