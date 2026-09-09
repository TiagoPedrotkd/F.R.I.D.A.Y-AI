# Checklist — Fase 4

Script: `.\scripts\fase4_acceptance.ps1`  
Live smoke: [`live-smoke-last.json`](live-smoke-last.json) · `.\scripts\acceptance\fases2-5_live_gates.ps1`

## Código / docs

- [x] `docs/fase-4/`
- [x] Google OAuth + rotas
- [x] Health sync + painel Saúde
- [x] calendar_provider / email_provider
- [x] Painéis Agenda + Mail
- [x] Testes + acceptance

## Live (manual)

- [x] Cloud Console Testing + test user (OAuth ligado com scopes calendar/gmail/fitness)
- [x] `.env` GOOGLE_* + reiniciar agent-api
- [x] Conectar Google nas Definições (`/v1/google/status` → `connected=true`)
- [x] Sync saúde (`POST /v1/health/sync`) + listar mail (`/v1/mail/messages`) + agenda (`/v1/agenda/events`)
- [x] Fallback CalDAV: `GOOGLE_ENABLED=false` → Radicale (`/friday/friday/`)
- [ ] Fallback IMAP puro (requer `EMAIL_*` — ver Fase 2)
