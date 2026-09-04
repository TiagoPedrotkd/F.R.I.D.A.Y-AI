# Fase LLM — treino, prompts, especialistas

| Doc | Conteúdo |
|-----|----------|
| [prompts-evolution.md](prompts-evolution.md) | Phase 0–5 → código FRIDAY |
| [domain-packs.md](domain-packs.md) | Base + LoRA por domínio |
| [rag-moe.md](rag-moe.md) | RAG / GraphRAG leve / LoRA / Agentes |
| [integrations.md](integrations.md) | Weather / health / notes |
| [cutover.md](cutover.md) | Troca manual Phi-4 → modelo próprio |

## Comandos rápidos

```powershell
# Estado CPT incremental
python -m friday_llm.training.incremental.cli --status

# Dia N limpo (após reset)
python -m friday_llm.training.incremental.cli --day 1 --add 10 --prefer-domain --train

# Especialistas registados
# GET http://127.0.0.1:8090/v1/specialists
```

Produção continua em `LM_STUDIO_MODEL` (default Phi-4) até cutover manual.
