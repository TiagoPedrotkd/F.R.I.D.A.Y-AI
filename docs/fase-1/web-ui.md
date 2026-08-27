# Interface web F.R.I.D.A.Y. — Fase 1

## Arquitectura

```
Browser (apps/web)  --REST/SSE-->  services/agent-api (FastAPI :8090)
                                         |
                                         +-- ToolRunner / skills / ShortTermMemory
                                         +-- Whisper STT / Piper TTS (bytes)
                                         +-- friday/monitors/*.html
                                         +-- healthcheck / LM Studio (status)
```

O browser **nunca** liga ao MCP. O CLI `friday-voice` continua a existir em paralelo.

## Contrato API

| Método | Rota | Função |
|--------|------|--------|
| GET | `/v1/status` | Backend + LM; `demo=true` se LM down |
| POST | `/v1/sessions` | Cria sessão |
| GET/DELETE | `/v1/sessions/{id}` | Estado / limpar |
| POST | `/v1/chat` | `{session_id, text}` → reply + activity + ui |
| POST | `/v1/confirm` | `{session_id, decision: confirm\|cancel}` |
| POST | `/v1/stt` | Upload WAV → texto |
| POST | `/v1/tts` | Texto → `audio/wav` |
| GET | `/v1/sessions/{id}/events` | SSE (`state`, `activity`, …) |
| GET | `/monitors/{name}` | Snapshots HTML (sem path traversal) |

## Como correr

1. (Opcional) Healthcheck: `services/healthcheck` na porta 8080.
2. LM Studio Local Server + modelo carregado (`localhost:1234`).
3. API:

```powershell
.\scripts\run-agent-api.ps1
```

4. UI:

```powershell
.\scripts\run-web-ui.ps1
```

Abre http://127.0.0.1:5173. Em dev, o Vite faz proxy de `/v1` e `/monitors` para `:8090`.

Variável opcional: `VITE_AGENT_API_BASE=http://127.0.0.1:8090` (obrigatória se não usares o proxy).

Dependências Python (API): `pip install -e ".[api,voice]"` (ou pelo menos `.[api]` + voice para STT/TTS).

## Modo demo

Se o LM / API estiver indisponível, `/v1/status` devolve `demo: true` e a UI usa fixtures etiquetadas **[DEMO]** — nunca apresentadas como dados reais. Também podes forçar em Definições → “Forçar modo demo”.

## Preferências (localStorage)

Idioma, TTS, volume, autoplay, interrupt, auto-open monitors, alto contraste, reduzir movimento, demo.

Abstrações Tauri-ready: `apps/web/src/platform/{audio,storage,links,config}.ts`.

## Limitações Fase 1

- Sem empacotamento Tauri / instalador.
- STT espera WAV PCM (o mic da UI grava WAV 16 kHz).
- Monitores: botão “Abrir monitor”; `AUTO_OPEN_MONITORS` / preferência UI controlam abertura automática.
- Confirmação: `ConfirmationGate` via `/v1/confirm` e acção rápida “Confirmação demo”; Enter **não** confirma acções perigosas.

## Checklist manual

Ver `docs/fase-1/web-ui-checklist.md`.

## Testes

```powershell
# API
python -m pytest tests/test_agent_api.py -q

# UI
cd apps/web
npm test
```
