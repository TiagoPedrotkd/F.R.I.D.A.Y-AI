# Checklist de Conclusão — Fase 3 (fundação + Casa UI)

Script: `.\scripts\fase3_acceptance.ps1`  
Relatório: [`acceptance-last.json`](acceptance-last.json)  
Live smoke: [`live-smoke-last.json`](live-smoke-last.json)

## Código / docs

- [x] `docs/fase-3/` completo
- [x] Compose profiles `mqtt`, `homeassistant`, `frigate`
- [x] Client `friday/integrations/home_assistant.py` (read + `call_service` + energy)
- [x] Skills HA registadas quando `HA_ENABLED` (incl. `ha_call_service` gated)
- [x] REST `/v1/ha/*` + `ha` em `/v1/status`
- [x] Painel Casa na web UI
- [x] Intent + prompt listam tools HA
- [x] Frigate stub sem arranque automático
- [x] Prefs / Settings toggle `home_assistant`

## Aceitação automatizada

- [x] `fase3_acceptance.ps1` passa (docs + compose + pytest)
- [x] Live HA (`-RequireHomeAssistant`) — `localhost:8123` + `/v1/ha/status` + entities

## Live (manual no teu PC)

- [x] `docker compose --profile mqtt --profile homeassistant up -d`
- [x] Token long-lived + `HA_ENABLED=true`
- [x] Smoke: `/v1/ha/status` + entities (painel **Casa** / chat “estado da casa” com LLM up)
- [ ] Câmaras / Frigate — adiado

## Fora de âmbito

- RTSP real / Coral
- Treino LLM
