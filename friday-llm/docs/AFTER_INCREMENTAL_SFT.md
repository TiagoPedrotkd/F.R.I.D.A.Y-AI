# Após CPT incremental — SFT / export / eval

Corre **só** quando o CPT incremental tiver docs/steps suficientes (vários dias ou corpus grande o suficiente para o teu critério). Phi-4 em produção **não** muda sozinho.

## Passos

1. **Select best** do run incremental:

```powershell
python -m friday_llm.training.continued_pretraining.select_checkpoint `
  --run-dir friday-llm/checkpoints/cpt-incremental `
  --dest friday-llm/checkpoints/cpt-incremental-best/adapter `
  --metrics friday-llm/reports/incremental/checkpoint_metrics.jsonl
```

2. **SFT Fase 4** com adapter CPT incremental (config dedicada):

```powershell
$env:TRANSFORMERS_NO_TF = "1"; $env:USE_TF = "0"; $env:USE_TORCH = "1"
python -m friday_llm.training.sft.cli --config friday-llm/configs/fase4_sft_incremental.yaml
```

3. **Export + eval** (gate vs Phi-4):

```powershell
# Ajusta fase6_export.yaml para os adapters incremental-best / sft-incremental-best se necessário
python -m friday_llm.export.cli --config friday-llm/configs/fase6_export.yaml
```

4. **Troca manual** de `LM_STUDIO_MODEL` / produção só se o gate passar.

## Script encadeado

`scripts/incremental_after_cpt.ps1` — select best → SFT → lembrete de export/eval.
Não espera automaticamente “CPT acabou para sempre”; corre-o quando **tu** decidires que o incremental está pronto.
