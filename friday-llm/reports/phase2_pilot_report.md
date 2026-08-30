# Fase 2 — Relatório Piloto (FRIDAY LLM)

**Run:** `friday-fase2-pilot`  
**Gerado:** 2026-08-29T22:34:23.594681+00:00

## Treino


## Avaliação vs baseline

| Métrica | Phi-4 baseline | Piloto pós-SFT | Delta |
|---------|----------------|----------------|-------|
| pass_rate | 0.467 | — | — |
| mean_latency_s | 11.372 | — | — |
| tool_call_rate | 0.0 | — | — |

## Export LM Studio

- Adapter: `friday-llm/checkpoints/sft-fase2-pilot/adapter`
- Manifest: `friday-llm/reports/export_manifest.json`
- Guia: [`export/lm_studio_guide.md`](../export/lm_studio_guide.md)

## Avisos

- Subset piloto **não** equivale a conhecimento geral.
- `LM_STUDIO_MODEL` em produção permanece `microsoft/phi-4`.
- Eval piloto requer modelo carregado manualmente no LM Studio.
