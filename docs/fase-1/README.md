# Skills contract — Fase 1

See [skills-contract.md](skills-contract.md) for the formal interface.

## Quick reference

- `friday/skills/base.py` — `Skill` protocol + `SkillResult`
- `friday/skills/registry.py` — registration and OpenAI tool export
- Mock skills: `get_current_time`, `tell_joke`

## Adding a skill

1. Create a module under `friday/skills/` implementing `Skill`
2. Register in `default_registry()` or your app bootstrap
3. No changes required in the voice loop
