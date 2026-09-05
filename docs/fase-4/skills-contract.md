# Skills / REST — Fase 4

## Skills (inalterados + saúde)

| Skill | Notas |
|-------|-------|
| `get_health_summary` | Lê cache local |
| `get_health_day` | Dia `YYYY-MM-DD` |
| `list_calendar_events` / create / cancel / modify | Via `calendar_provider` |
| `list_emails` / `read_email` / `send_email` | Via `email_provider` |

## REST

| Rota | Função |
|------|--------|
| `/v1/google/*` | OAuth |
| `/v1/health/status\|summary\|days\|sync` | Saúde |
| `/v1/agenda/events` | Lista eventos |
| `/v1/mail/messages` | Lista emails |
| `/v1/mail/messages/{id}` | Ler email |
