# Evolução de system prompts (Phase 0–5 → FRIDAY)

| Phase | Ideia | Implementação actual |
|-------|--------|----------------------|
| 0 | Assistente genérico | Substituído por prompt v8 + tools |
| 1 | Memória / perfil | `user_profile` em prefs + bloco PERSONAL CONTEXT em `tool_runner` + Settings |
| 2 | Routing MoE (6 pilares + folhas) | `friday/llm/domain_router.py` + `domains.yaml` (pillars + domains) + bloco ROUTING com Pillar |
| 3 | RAG / dados vivos | CONTEXT + `search_docs` / `search_knowledge_graph` / `research_web` + GraphRAG leve |
| 4 | Qualidade + CoT/reflect | `quality.py` + hedges + passe REFLECT no `tool_runner` |
| 5 | Multimodal + integrações | Voz/visão; weather/health/notes; confirmações gated |

Prompt vivo: `friday/llm/prompts.py` (`PROMPT_VERSION = v8`).
