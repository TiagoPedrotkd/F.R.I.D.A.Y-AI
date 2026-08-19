# Skills contract — Fase 1

Formal interface for extending F.R.I.D.A.Y-AI with new capabilities without modifying the voice loop.

## Skill protocol

Every skill implements:

| Field | Type | Description |
|-------|------|-------------|
| `name` | `str` | Unique identifier (OpenAI function name), e.g. `get_current_time` |
| `description` | `str` | Natural language description for the LLM |
| `parameters` | `dict` | JSON Schema (OpenAI function format) |
| `execute()` | async | Runs the skill and returns `SkillResult` |

### SkillResult

```python
@dataclass
class SkillResult:
    success: bool
    content: str              # Text for the LLM to present to the user
    error: str | None = None
    metadata: dict | None = None
```

On failure, set `success=False` and populate `error`. The tool runner converts this to a tool message without crashing the pipeline.

## Registration

```python
from friday.skills.registry import SkillRegistry
from friday.skills.mock.time_skill import TimeSkill

registry = SkillRegistry()
registry.register(TimeSkill())
tools = registry.to_openai_tools()
```

## Tool call flow

1. User speaks → STT → LLM receives message + tools list
2. LLM returns native `tool_calls` **or** JSON fallback (Bionic)
3. `ToolRunner` invokes `registry.execute(name, arguments)`
4. Result is sent back as `{"role": "tool", "tool_call_id": "...", "content": "..."}`
5. LLM produces final spoken reply (max 3 tool rounds)

### ToolCall (internal)

```python
@dataclass
class ToolCall:
    id: str
    name: str
    arguments: dict
```

## Mock skills (Fase 1)

| Skill | `name` | Example trigger |
|-------|--------|-----------------|
| TimeSkill | `get_current_time` | "Que horas sao?" |
| JokeSkill | `tell_joke` | "Conta uma piada" |

## Extension (Fase 2+)

New skill = new file + `registry.register()` — zero changes to `pipeline/loop.py`.
