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
- [ ] LM Studio Local Server ON na sessão de aceitação live
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
.\scripts\fase1_chat_latency.ps1 -N 5
```

Checklist UI: [web-ui-checklist.md](web-ui-checklist.md)

- [ ] Arranque API + UI; header mostra API/LM
- [ ] Chat texto (hora / piada)
- [ ] Mic → STT → chat → TTS interruptível
- [ ] Quick actions notícias / finanças + sources
- [ ] Abrir monitor
- [ ] Confirmação demo (Escape cancela)
- [ ] Definições persistem; a11y básica
- [ ] Demo com LM desligado
- [ ] Mobile / drawer Painel

## Latência

| Caminho | Script | Alvo |
|---------|--------|------|
| Voz wake→TTS | `.\scripts\benchmark-latency.ps1 -LogFile logs\voice.log` | p50 &lt; 3–4s, p95 &lt; 5s |
| Chat API | `.\scripts\fase1_chat_latency.ps1` | soft p50 &lt; 8s (LLM local) |

- [x] Scripts de benchmark documentados e prontos
- [ ] Medição wake→TTS no teu hardware (requer voice loop + log)
- [ ] Medição chat API com LM carregado

## MCP Cursor

- [x] `.cursor/mcp.json` criado (local; gitignored — ver `mcp.json.example`)
- [ ] No Cursor: Settings → MCP → `friday` ligado; testar tool `get_current_datetime` ou prompt `summarize`

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
.\scripts\fase1_chat_latency.ps1
```

## Data de conclusão (engenharia)

| Campo | Valor |
|---|---|
| Engenharia fechada em | 2026-09-02 |
| Validado por (automatizado) | `fase1_acceptance.ps1` (gates offline PASS) |
| Aceitação live UI | Pendente — requer LM Studio + run-agent-api + run-web-ui |
| Notas | Piper EN/PT OK; MCP json local; testes API 45+ e Vitest 8 OK. Live ports 1234/8090/5173 down na corrida de fecho. |

Quando a secção **Aceitação live** estiver marcada no teu PC, a Fase 1 está **100% concluída**.
