# Skills contract — Fase 3.0 (HA read-only)

| Skill | Confirmação | Notas |
|-------|-------------|-------|
| `ha_get_status` | Não | API `/api/` reachable + versão |
| `ha_list_entities` | Não | Lista entidades (filtro `domain` opcional) |
| `ha_get_state` | Não | Estado de `entity_id` |

Aliases: `get_home_status` → `ha_get_status`.

Registo só se `HA_ENABLED=true` **e** prefs `integrations_enabled.home_assistant` ≠ false.

## Fase 3.1 (futuro)

| Skill | Confirmação |
|-------|-------------|
| `ha_call_service` | Sim |
| `frigate_get_snapshot` | Sim |
