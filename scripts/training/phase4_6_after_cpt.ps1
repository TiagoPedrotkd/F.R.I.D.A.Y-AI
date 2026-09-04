# Encadeia Fase 4 SFT + Fase 6 export após conclusão do CPT Fase 3.
# Uso: .\scripts\phase4_6_after_cpt.ps1

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root

$env:TRANSFORMERS_NO_TF = "1"
$env:USE_TF = "0"
$env:USE_TORCH = "1"
$env:PYTHONIOENCODING = "utf-8"

$log = Join-Path $Root "friday-llm\reports\cpt_fase3_train.log"
$selection = Join-Path $Root "friday-llm\checkpoints\cpt-fase3-best\selection.json"

Write-Host "A aguardar conclusão CPT (selection.json)..."
while (-not (Test-Path $selection)) {
    if (Test-Path $log) {
        $tail = Get-Content $log -Tail 1 -ErrorAction SilentlyContinue
        if ($tail) { Write-Host $tail }
    }
    Start-Sleep -Seconds 120
}

Write-Host "CPT concluído. A iniciar Fase 4 SFT..."
python -m friday_llm.training.sft.cli --config friday-llm/configs/fase4_sft.yaml 2>&1 |
    Tee-Object -FilePath "friday-llm\reports\sft_fase4_train.log"

Write-Host "A actualizar fase6_export.yaml para adapters 7B..."
$exportCfg = Join-Path $Root "friday-llm\configs\fase6_export.yaml"
$content = Get-Content $exportCfg -Raw
$content = $content -replace "cpt_adapter:.*", "cpt_adapter: friday-llm/checkpoints/cpt-fase3-best/adapter"
$content = $content -replace "sft_adapter:.*", "sft_adapter: friday-llm/checkpoints/sft-fase4-best/adapter"
$content = $content -replace "use_smoke_model: true", "use_smoke_model: false"
$content = $content -replace 'gguf_basename:.*', "gguf_basename: friday-qwen25-7b-v1"
Set-Content -Path $exportCfg -Value $content -NoNewline

Write-Host "A executar Fase 6 export (7B)..."
python -m friday_llm.export.cli --config friday-llm/configs/fase6_export.yaml 2>&1 |
    Tee-Object -FilePath "friday-llm\reports\phase6_export_7b.log"

Write-Host "Pipeline Fase 4+6 concluído."
