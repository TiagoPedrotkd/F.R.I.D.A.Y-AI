# Skills contract — Fase 1

Formal interface for extending F.R.I.D.A.Y-AI with new capabilities without modifying the voice loop.

## Skill protocol

Every skill implements:

| Field | Type | Description |
|-------|------|-------------|
| `name` | `str` | Unique identifier (OpenAI function name) |
| `description` | `str` | Natural language description for the LLM |
| `parameters` | `dict` | JSON Schema (OpenAI function format) |
| `execute()` | async | Runs the skill and returns `SkillResult` |

### SkillResult

```python
@dataclass
class SkillResult:
    success: bool
    content: str              # Text for the LLM / user
    error: str | None = None
    metadata: dict | None = None
```

On failure, set `success=False` and populate `error` with an honest PT message.

## Registration

```python
from friday.skills.registry import default_registry

registry = default_registry()
tools = registry.to_openai_tools()
```

## Tool call flow

1. User input → optional intent router → skill **or** LLM + tools
2. LLM returns native `tool_calls` **or** JSON fallback
3. `ToolRunner` invokes `registry.execute(name, arguments)`
4. Result is sent back as a tool message; LLM may finalize
5. Max tool rounds: `LLM_MAX_TOOL_ROUNDS` (default 3)

## Skills (Fase 1)

| Skill | `name` | Example |
|-------|--------|---------|
| DateTime | `get_current_datetime` | "Que horas sao?" |
| Joke | `tell_joke` | "Conta uma piada" |
| System | `get_system_info` | "Que SO estou a usar?" |
| Words | `word_count` | "Conta as palavras..." |
| JSON | `format_json` | "Formata este JSON" |
| Search | `search_web` | "Pesquisa o Phi-4" |
| Fetch | `fetch_url` | "Le https://..." |
| News | `get_world_news` | "Poe-me a par" |
| Finance | `get_world_finance_news` | "Briefing financeiro" |
| Monitors | `open_world_monitor` / `open_finance_world_monitor` | "Abre o monitor..." |

Alias: `get_current_time` → `get_current_datetime`.

Roadmap (nao implementado): parâmetro `country` + briefing por país —
ver [noticias-financas-worldwide.md](noticias-financas-worldwide.md).

## Extension

New skill = new file + `registry.register()` + optional intent patterns —
zero changes to `pipeline/loop.py`.
