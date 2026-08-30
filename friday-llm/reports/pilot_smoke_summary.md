# Pilot smoke summary (Fase 0 → infra validada)

**Data:** 2026-08-29  
**Produção:** `LM_STUDIO_MODEL=microsoft/phi-4` **não alterado**.

## Resultados

| Etapa | Resultado |
|-------|-----------|
| Baseline Phi-4 | 15 itens; pass_rate **0.467**; mean latency ~11.4 s — ver `reports/baseline_phi4.json` |
| FineWeb2 stream | `por_Latn`, 80 docs → 75 após limpeza (5 PII); `source_note=fineweb_stream` |
| CPT smoke | `Qwen/Qwen2.5-0.5B` fp16 LoRA; train_loss≈2.85; eval_loss≈2.83; 20 steps |
| SFT smoke | Adapter em `checkpoints/sft-smoke/adapter/` (~35 MB) |
| Export | Manifesto com SHA-256; GGUF **não** convertido (falta llama.cpp) — documentado |
| Testes | `friday-llm/tests`: 5 passed |

## Limitações honestas

- Smoke usa **0.5B** para validar a infra no Windows sem bitsandbytes; o alvo de produção continua **Qwen2.5-7B** QLoRA.
- Subset FineWeb (80 docs) **não** equivale a conhecimento geral.
- Baseline <50% tool-calling no Phi-4 é o ponto de partida, não uma falha do piloto.
- GGUF / troca no LM Studio exige passo manual posterior.

## Próximos passos (Fases 3+)

1. Instalar bitsandbytes Windows ou usar QLoRA via outro backend.
2. CPT/SFT em `Qwen/Qwen2.5-7B` com orçamento de tokens aprovado.
3. Converter GGUF e avaliar sem substituir o default.
4. Ligar RAG store ao ToolRunner com skill `search_docs`.
