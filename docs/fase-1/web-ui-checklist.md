# Checklist manual — web UI Fase 1

Automatizado (código): `.\scripts\fase1_acceptance.ps1`  
Fecho: [checklist-conclusao.md](checklist-conclusao.md)

## Antes de começar

1. LM Studio → modelo carregado → Local Server **ON** (`localhost:1234`)
2. `.\scripts\run-agent-api.ps1`
3. `.\scripts\run-web-ui.ps1` → http://127.0.0.1:5173

## Checklist

Automatizado: `fase1_live_smoke.ps1`, `fase1_acceptance.ps1`, Vitest (`npm test`).

- [x] Arranque: API/LM ligados — *API*
- [x] Chat texto: hora / piada — *API*
- [x] STT path: WAV→Whisper→texto — *API* (mic browser/WASAPI = opcional hardware)
- [x] Quick actions: notícias / finanças — *API*
- [x] Monitor HTML — *API*
- [x] Confirmação demo + cancel — *API*; a11y modal — *Vitest*
- [x] Prefs roundtrip — *API*
- [x] TTS WAV — *API*
- [x] Demo LM off: `status.demo=true` + fixtures `[DEMO]` — *pytest + Vitest*
- [x] Mobile drawer “Data” — *Vitest*
- [ ] (Opcional) Permissão mic no browser + Stop interruptível na tua máquina

## Atalhos de verificação

```powershell
.\scripts\fase1_acceptance.ps1 -RequireLive
.\scripts\fase1_live_smoke.ps1
.\scripts\fase1_chat_latency.ps1 -N 5
.\scripts\fase1_voice_latency.ps1 -N 3
cd apps\web; npm test
```
