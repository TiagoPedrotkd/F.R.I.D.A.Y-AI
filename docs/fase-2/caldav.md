# CalDAV — Fase 2

## Contentor

Serviço `radicale` no `docker-compose.yml` (porta host `5232`).

```powershell
docker compose up -d radicale
```

URL típica: `http://127.0.0.1:5232/`  
Calendário default do utilizador: `http://127.0.0.1:5232/friday/friday/`

## Variáveis (`.env`)

```env
CALDAV_URL=http://127.0.0.1:5232/friday/friday/
CALDAV_USER=friday
CALDAV_PASSWORD=friday
CALDAV_ENABLED=true
```

## Skills

| Skill | Confirmação |
|-------|-------------|
| `list_calendar_events` | Não |
| `create_calendar_event` | Sim (`ConfirmationGate`) |

## Dependências Python

```powershell
pip install -e ".[productivity]"
```

Pacotes: `caldav`, `icalendar`.
