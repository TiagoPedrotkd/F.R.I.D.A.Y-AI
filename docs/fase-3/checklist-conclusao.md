# Checklist de Conclusão — Fase 3 (fundação + Casa UI)

Script: `.\scripts\fase3_acceptance.ps1`  
Relatório: [`acceptance-last.json`](acceptance-last.json)

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
- [ ] Live HA opcional (`-RequireHomeAssistant`)

## Live (manual no teu PC)

- [ ] `docker compose --profile mqtt --profile homeassistant up -d`
- [ ] Token long-lived + `HA_ENABLED=true`
- [ ] Smoke: “qual o estado da casa?” + painel **Casa**
- [ ] Câmaras / Frigate — adiado

## Fora de âmbito

- RTSP real / Coral
- Treino LLM
