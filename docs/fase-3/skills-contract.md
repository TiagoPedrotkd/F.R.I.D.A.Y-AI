# Skills contract — Fase 3 (HA + acções gated)

| Skill | Confirmação | Notas |
|-------|-------------|-------|
| `ha_get_status` | Não | API `/api/` reachable + versão |
| `ha_list_entities` | Não | Lista entidades (filtro `domain` opcional) |
| `ha_get_state` | Não | Estado de `entity_id` |
| `ha_call_service` | Sim | `turn_on` / `turn_off` / `toggle` (light, switch, …) |

Aliases: `get_home_status` → `ha_get_status`.

Registo só se `HA_ENABLED=true` **e** prefs `integrations_enabled.home_assistant` ≠ false.

## UI Casa (agent-api)

| Método | Rota | Confirmação |
|--------|------|-------------|
| GET | `/v1/ha/status` | — |
| GET | `/v1/ha/entities` | — |
| GET | `/v1/ha/energy` | — |
| POST | `/v1/ha/action` | Cria pending → `/v1/confirm` |

## Ainda futuro (Frigate)

| Skill | Confirmação |
|-------|-------------|
| `frigate_get_snapshot` | Sim |
