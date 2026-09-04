# Integrações

| Integração | Skill | Dados |
|------------|-------|--------|
| Weather | `get_weather` | Open-Meteo (sem API key) |
| Health | `get_health_summary` | `data/integrations/health/summary.json` |
| Notes / Notion export | `search_personal_notes` | `data/integrations/notion_export/**/*.md` |
| Strava (ficheiro) | (mesmo health ou export JSON) | `data/integrations/strava/` |
| Calendar / Email | skills CalDAV/IMAP | `.env` `CALDAV_*` / `EMAIL_*` |

Prefs: `integrations_enabled` via `/v1/prefs`.  
Criar pastas exemplo:

```powershell
New-Item -ItemType Directory -Force data\integrations\health, data\integrations\notion_export, data\integrations\strava
'{"sleep_hours":7.2,"steps":8000}' | Set-Content data\integrations\health\summary.json
```
