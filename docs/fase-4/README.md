# Fase 4 — Google (Saúde + Calendar + Gmail)

**Estado:** OAuth Google partilhado; saúde com cache local + painel; Calendar/Gmail via providers (CalDAV/IMAP fallback).

## Objectivo

Conta Google como fonte primária de agenda, email e métricas de saúde (Fitbit/Pixel/Google Fit scopes em modo Testing).  
Dados sensíveis ficam em cache local; tokens em `data/secrets/`.

## Documentos

| Doc | Conteúdo |
|------|----------|
| [google-oauth.md](google-oauth.md) | Cloud Console + OAuth + rotas |
| [saude.md](saude.md) | Sync saúde + painel + schema |
| [calendar-gmail.md](calendar-gmail.md) | Providers Google vs CalDAV/IMAP |
| [skills-contract.md](skills-contract.md) | Skills + REST |
| [checklist-conclusao.md](checklist-conclusao.md) | Gates |

## Ordem

1. Criar OAuth client (Desktop) no Google Cloud Console; app em **Testing**; a tua conta como test user.
2. Preencher `.env`: `GOOGLE_ENABLED=true`, `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`.
3. Reiniciar agent-api → Definições → **Conectar Google**.
4. Abrir painéis **Saúde** / **Agenda** / **Mail**.

## Fora de âmbito

- Remover Radicale/IMAP; Frigate; Open Banking; verificação OAuth “Production”.
