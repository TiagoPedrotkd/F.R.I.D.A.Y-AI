# Documentação F.R.I.D.A.Y-AI

| Área | Índice |
|------|--------|
| Layout do monorepo | [REPO_LAYOUT.md](REPO_LAYOUT.md) |
| Arquitectura / rede | [arquitectura/README.md](arquitectura/README.md) |
| Fase 0 — Docker + LM Studio | [fase-0/README.md](fase-0/README.md) |
| Fase 1 — Voz / UI / skills | [fase-1/README.md](fase-1/README.md) |
| Fase 2 — CalDAV / Email / desktop | [fase-2/README.md](fase-2/README.md) |
| Fase 3 — Casa inteligente (HA / MQTT / Frigate) | [fase-3/README.md](fase-3/README.md) |
| Fase 4 — Google (Saúde / Calendar / Gmail) | [fase-4/README.md](fase-4/README.md) |
| Fase 5 — Finanças pessoais (ledger local) | [fase-5/README.md](fase-5/README.md) |
| Fase LLM — prompts, treino, especialistas | [fase-llm/README.md](fase-llm/README.md) |

Runtime do assistente: `friday/` + `services/agent-api` + `apps/web`.  
Treino de modelo: `friday-llm/` (não misturar com `data/` de produção).
