# Layout do repositório F.R.I.D.A.Y-AI

Mapa para editar e corrigir à mão sem adivinhar pastas.

## Árvore

| Caminho | Papel |
|---------|--------|
| `apps/web` | UI React (Vite) |
| `apps/desktop` | Shell Tauri |
| `services/agent-api` | API chat/SSE/STT/TTS/prefs |
| `services/` | healthcheck, MCP, etc. |
| `friday/` | Biblioteca runtime (skills, llm, memory, productivity, integrations) |
| `friday-llm/` | Treino CPT/SFT, export GGUF, checkpoints — **separado** da runtime |
| `docs/` | Documentação por fase + arquitectura + LLM |
| `scripts/run` | Arranque local (API, UI, voice) |
| `scripts/acceptance` | Gates fase 1/2 |
| `scripts/training` | CPT/SFT/export/cutover |
| `scripts/ops` | Mic, LM Studio, Task Scheduler, rede |
| `data/` | Runtime local (prefs, sessions, chroma, integrations) — **não** datasets de treino |
| `tests/` | Pytest do agente |

## Regras

1. Código do assistente em produção → `friday/` + `services/`.
2. Treino / adapters / GGUF → `friday-llm/`.
3. Memória pessoal (`data/chroma`) ≠ RAG docs (`data/rag_chroma`) ≠ datasets de treino (`friday-llm/data`).
4. Checkpoints activos: `friday-llm/checkpoints/`; arquivos: `friday-llm/checkpoints/archive/`.
5. Preferências e perfil: `data/prefs/default.json` (via Settings UI / `/v1/prefs`).
6. Integrações ficheiro: `data/integrations/{health,notion_export,strava}/`.

## Onde mudar X

| Queres mudar… | Ficheiro típico |
|---------------|-----------------|
| Tom / regras do LLM | `friday/llm/prompts.py` |
| Domínios / routing | `friday/llm/domains.yaml`, `domain_router.py` |
| Skills/tools | `friday/skills/` + `registry.py` |
| Perfil utilizador | Settings UI ou `data/prefs` |
| Especialistas LoRA | `friday-llm/checkpoints/specialists/<domain>/` |
| Arranque API | `scripts/run/run-agent-api.ps1` (wrapper em `scripts/run-agent-api.ps1`) |
