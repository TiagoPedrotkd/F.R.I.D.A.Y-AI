# Fase 2 — Produtividade (produto)

Calendário CalDAV, email IMAP/SMTP e app desktop Tauri.  
**Sem treino LLM** — o modelo continua o do LM Studio (ex. Phi-4).

## Documentos

| Documento | Conteúdo |
|-----------|----------|
| [checklist-conclusao.md](checklist-conclusao.md) | Critérios de fecho |
| [caldav.md](caldav.md) | Radicale + skills de calendário |
| [email-imap.md](email-imap.md) | IMAP/SMTP + skills de email |
| [desktop-tauri.md](desktop-tauri.md) | Empacotamento Windows |

## Ordem de implementação

1. CalDAV (Radicale) + `list_calendar_events` / `create_calendar_event`
2. IMAP leitura + `send_email` (sempre com ConfirmationGate)
3. Desktop Tauri (`apps/desktop`)
4. `.\scripts\fase2_acceptance.ps1`

## Pré-requisitos

- Fase 1 agent-api + web UI
- Docker para Radicale (`docker compose up -d radicale`)
- Credenciais só em `.env` (ver [gestao-secrets](../fase-0/gestao-secrets.md))

## Fora de âmbito

- `friday-llm` / CPT / SFT / cutover de modelo
- Home Assistant, Frigate, Open Banking (Fases 3+)
