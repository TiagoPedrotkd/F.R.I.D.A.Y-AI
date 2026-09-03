# Checklist de Conclusão — Fase 1

Marca cada item quando validado.  
Script automático: `.\scripts\fase1_acceptance.ps1`  
Último relatório: [`acceptance-last.json`](acceptance-last.json)

## Critérios de planeamento (código)

- [x] **Voice pipeline** — wake / enter / text → STT → ToolRunner → Piper (`friday/pipeline`, `scripts/run-voice-loop.ps1`)
- [x] **Contrato conversacional** — intent router + tools + memória curta ([conversacao.md](conversacao.md))
- [x] **Skills Fase 1** — datetime, news/finance, web, monitors, memory, joke, system ([skills-contract.md](skills-contract.md))
- [x] **Agent API + Web UI** — FastAPI `:8090` + Vite `:5173` ([web-ui.md](web-ui.md))
- [x] **MCP server** — `friday-mcp` / `.cursor/mcp.json` ([mcp.md](mcp.md))
- [x] **Notícias / finanças / monitores** — skills + HTML snapshots
- [x] **Confirmação segura** — `ConfirmationGate` + modal (Enter não confirma)
- [x] **Modo demo** — UI com fixtures `[DEMO]` se LM down
- [x] **Testes automatizados** — API + skills + UI Vitest (ver `fase1_acceptance.ps1`)

## Estabilidade hardware / runtime

- [x] Piper voices presentes (`en_GB-cori-high`, `pt_PT-tugao-medium`)
- [x] Agent-api Whisper default **CPU** (CUDA só com `FRIDAY_WHISPER_CUDA=1`)
- [x] `VOICE_TRIGGER=text` suportado (sem mic) para desenvolvimento
- [x] Fallback LLM documentado (`LLM_FALLBACK_BASE_URL` — Ollama / llama.cpp)
- [ ] Mic WASAPI validado no teu PC (`.\scripts\mic-benchmark.ps1` / [mic-troubleshooting.md](mic-troubleshooting.md))
- [x] LM Studio Local Server ON na sessão de aceitação live (2026-09-03)
- [ ] (Opcional) Fallback Ollama configurado se quiseres headless

## Aceitação live (quando LM Studio + API + UI estiverem up)

Correr:

```powershell
# Terminal A
.\scripts\run-agent-api.ps1
# Terminal B
.\scripts\run-web-ui.ps1
# Validação
.\scripts\fase1_acceptance.ps1 -RequireLive
.\scripts\fase1_live_smoke.ps1
.\scripts\fase1_chat_latency.ps1 -N 5
```

Checklist UI: [web-ui-checklist.md](web-ui-checklist.md)  
Relatórios: [`acceptance-last.json`](acceptance-last.json), [`live-smoke-last.json`](live-smoke-last.json), [`chat-latency-last.json`](chat-latency-last.json)

Validado via API smoke + probes + Vitest (2026-09-03):

- [x] Arranque API + UI; status LLM ligado (`demo=false`, `phi-4`)
- [x] Chat texto (hora / piada)
- [x] STT→chat→TTS — `fase1_live_smoke` (Piper WAV → Whisper → TTS; mic físico WASAPI opcional)
- [x] Quick actions notícias / finanças (API path; sources podem variar)
- [x] Monitor HTML (`/monitors/world_snapshot.html`)
- [x] Confirmação demo + cancel (API)
- [x] Prefs roundtrip (API)
- [x] TTS WAV (`fase1_live_smoke`)
- [x] Demo com LM desligado — `test_status_demo_when_llm_down` + fixtures `[DEMO]` (Vitest)
- [x] Mobile / drawer “Data” — Vitest (`components.test.tsx`)

## Latência

| Caminho | Script | Alvo |
|---------|--------|------|
| Voz (text-equivalent) | `.\scripts\fase1_voice_latency.ps1` | p50 ~3–4s soft |
| Voz wake real | `benchmark-latency.ps1` + voice loop | p50 &lt; 3–4s (opcional mic/wake) |
| Chat API | `.\scripts\fase1_chat_latency.ps1` | soft p50 &lt; 8s (LLM local) |

- [x] Scripts de benchmark documentados e prontos
- [x] Medição voice-path API (chat+TTS) — ver [`voice-latency-last.json`](voice-latency-last.json)
- [x] Medição chat API com LM carregado — ver [`chat-latency-last.json`](chat-latency-last.json)
- [ ] (Opcional) wake word físico + mic WASAPI no teu hardware

## MCP Cursor

- [x] `.cursor/mcp.json` criado (local; gitignored — ver `mcp.json.example`)
- [x] Servidor MCP verificado: `list_tools` + `call_tool get_current_datetime` (`fase1_acceptance`)
- [ ] (Opcional) Toggle visual no Cursor Settings → MCP → `friday` (só UI do editor)

## Fora de âmbito Fase 1 (não bloqueia)

- Tauri / instalador → [desktop-tauri.md](desktop-tauri.md) (Fase 2)
- CalDAV / email / Home Assistant / Frigate → Fases 2–3
- CPT / SFT / GGUF / cutover modelo próprio → `friday-llm` (treino)

## Comandos de validação rápida

```powershell
.\scripts\fase1_acceptance.ps1
python -m pytest tests/test_agent_api.py tests/test_conversacao_skills.py -q
cd apps\web; npm test
# Com LM Studio ON:
.\scripts\fase1_acceptance.ps1 -RequireLive
.\scripts\fase1_live_smoke.ps1
.\scripts\fase1_chat_latency.ps1
.\scripts\fase1_voice_latency.ps1 -N 3
```

## Data de conclusão (engenharia)

| Campo | Valor |
|---|---|
| Engenharia fechada em | 2026-09-02 |
| Validado por (automatizado) | acceptance + live smoke + voice latency + Vitest (PASS 2026-09-03) |
| Aceitação live API | PASS — LM `:1234`, API `:8090` ready, UI `:5173` |
| Aceitação live | PASS automatizada; mic WASAPI / toggle MCP no Cursor são opcionais de hardware/UI |
| Notas | STT via WAV sintetizado; MCP `call_tool` real; drawer mobile em Vitest; demo LM-off em pytest+fixtures. |

Fase 1 engenharia + gates live automatizados: **concluída**.
