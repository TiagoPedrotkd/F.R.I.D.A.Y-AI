# Checklist de Conclusão — Fase 3.0 (fundação)

Script: `.\scripts\fase3_acceptance.ps1`  
Relatório: [`acceptance-last.json`](acceptance-last.json)

## Código / docs

- [x] `docs/fase-3/` completo
- [x] Compose profiles `mqtt`, `homeassistant`, `frigate`
- [x] Client `friday/integrations/home_assistant.py`
- [x] Skills HA read-only registadas quando `HA_ENABLED`
- [x] Intent + prompt listam tools HA
- [x] Frigate stub sem arranque automático
- [x] Prefs / Settings toggle `home_assistant`

## Aceitação automatizada

- [x] `fase3_acceptance.ps1` passa (docs + compose + pytest)
- [ ] Live HA opcional (`-RequireHomeAssistant`)

## Live (manual no teu PC)

- [ ] `docker compose --profile mqtt --profile homeassistant up -d`
- [ ] Token long-lived + `HA_ENABLED=true`
- [ ] Smoke: “qual o estado da casa?”
- [ ] Câmaras / Frigate — adiado (3.1)

## Fora de âmbito 3.0

- Acções HA com ConfirmationGate
- RTSP real / Coral
- Treino LLM
