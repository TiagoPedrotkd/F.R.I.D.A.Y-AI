# Checklist de Conclusão — Fase 2 (produto)

Script: `.\scripts\fase2_acceptance.ps1`  
Último relatório: [`acceptance-last.json`](acceptance-last.json)  
Live smoke: [`live-smoke-last.json`](live-smoke-last.json) · `.\scripts\acceptance\fases2-5_live_gates.ps1`

## Código / docs

- [x] `docs/fase-2/` completo
- [x] Radicale no compose + vars `.env.example`
- [x] Skills CalDAV registadas
- [x] Skills IMAP/SMTP registadas
- [x] Create event / send email passam por ConfirmationGate (execução real após “sim”)
- [x] `apps/desktop` Tauri scaffold
- [x] Platform adapters detectam Tauri quando disponível

## Aceitação

- [x] Testes `tests/test_fase2_productivity.py` + `tests/test_fase2_vision.py`
- [x] CONTEXT JSON por turno + prompt v6
- [x] cancel/modify/find_free_slots + overlap no create
- [x] Preview no ConfirmationGate / UI
- [x] draft_email_reply (LLM local + fallback) + resolve_contact + workflows (3 passos + lembrete)
- [x] Proactive alerts (`GET /v1/alerts` + SSE periódico + banner UI com CTA)
- [x] Pattern prefs (`productivity_patterns`) + UI Settings + contact book
- [x] `prepare_meeting` + intent cancel/create com titulo/hora
- [x] Live setup script (`scripts/fase2_live_setup.ps1`) + Radicale no compose
- [x] CalDAV live: collection `/friday/friday/` + fallback com `GOOGLE_ENABLED=false`
- [ ] Credenciais IMAP reais + smoke live (`EMAIL_ENABLED` / `IMAP_*` no `.env`)
- [ ] `tauri build` no teu PC (requer Rust + WebView2)

## Fora de âmbito

- Treino LLM
- HA / Frigate
