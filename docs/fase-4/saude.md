# Saúde — Fase 4

## Schema local

`data/integrations/health/summary.json` (hoje) e `daily/YYYY-MM-DD.json`:

```json
{
  "date": "2026-09-05",
  "steps": 8000,
  "sleep_hours": 7.2,
  "resting_hr": 58,
  "hrv": 42,
  "active_minutes": 35,
  "source": "google_fitness",
  "synced_at": "2026-09-05T15:00:00+00:00"
}
```

## Sync

- `POST /v1/health/sync` — puxa Fitness API (scopes Google) e grava cache.
- Se Fitness falhar: mantém ficheiro manual; opcional Fitbit Web API (`FITBIT_*`).
- Skill `get_health_summary` lê o cache (não a cloud em cada pergunta).

## UI

Painel **Saúde**: métricas do dia, últimos dias, botão Sync, link estado Google.
