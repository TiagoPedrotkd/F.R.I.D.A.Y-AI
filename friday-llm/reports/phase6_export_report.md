# Fase 6 — Export modelo final

**Run:** `friday-fase6-export`  
**Gerado:** 2026-08-29T22:39:50.572958+00:00

## Validação

- SFT: `D:\Repositories\F.R.I.D.A.Y-AI\friday-llm\checkpoints\sft-smoke\adapter`
- CPT: `D:\Repositories\F.R.I.D.A.Y-AI\friday-llm\checkpoints\cpt-smoke\adapter`
- Merge CPT: True

## Merge HF

- Base: `Qwen/Qwen2.5-0.5B`
- Output: `D:\Repositories\F.R.I.D.A.Y-AI\friday-llm\export\merged-friday-v1`
- CPT fundido: True

## GGUF

- Status: **skipped**

## Manifesto

- Ficheiro: `friday-llm/reports/export_manifest.json`
- GGUF status: `skipped`
- Rollback: repor `LM_STUDIO_MODEL` = `microsoft/phi-4`

## Avaliação vs baseline

| Métrica | Phi-4 | Modelo exportado | Delta |
|---------|-------|------------------|-------|
| pass_rate | 0.467 | — | — |
| mean_latency_s | 11.372 | — | — |

- Gate eval: **FAIL / não corrido**

## LM Studio

1. Importar `friday-llm/export/gguf/*-Q4_K_M.gguf`
2. Testar com `$env:LM_STUDIO_MODEL = "<model-id>"`
3. Rollback: ver [`export/rollback.md`](../export/rollback.md)
