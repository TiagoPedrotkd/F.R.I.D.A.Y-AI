# Skills contract — Fase 1

See [skills-contract.md](skills-contract.md) for the formal interface.
See [conversacao.md](conversacao.md) for the full conversational contract.
See [mcp.md](mcp.md) for the MCP server (summarize / explain_code).
See [noticias-financas-worldwide.md](noticias-financas-worldwide.md) for
country-scoped news & finance (design — not implemented yet).

## Quick reference

- `friday/skills/base.py` — `Skill` protocol + `SkillResult`
- `friday/skills/registry.py` — registration and OpenAI tool export
- Skills: datetime, joke, system_info, word_count, format_json, search_web,
  fetch_url, world/finance news, open monitors, summarize, explain_code,
  remember/recall (Chroma)

## Adding a skill

1. Create a module under `friday/skills/` implementing `Skill`
2. Register in `default_registry()` or your app bootstrap
3. No changes required in the voice loop
4. Add intent patterns in `friday/llm/intent_router.py` when useful

## Voice / microfone

- Loop: `.\scripts\run-voice-loop.ps1` (`VOICE_TRIGGER=text` sem mic)
- Diagnóstico: [mic-troubleshooting.md](mic-troubleshooting.md)
- Benchmark: `.\scripts\mic-benchmark.ps1`
