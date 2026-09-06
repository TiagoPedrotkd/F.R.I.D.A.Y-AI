# ADR 0001 — LLM local via LM Studio

## Context

Queremos um assistente pessoal sem depender de APIs cloud para inferência no dia-a-dia, com privacidade e custo controláveis na LAN.

## Decision

Usar **LM Studio** (OpenAI-compatible server em `:1234`) como backend LLM de desenvolvimento/produção local. O modelo activo (ex. Phi-4) é configurado via `.env` (`LM_STUDIO_MODEL`).

## Consequences

- Requer LM Studio a correr para chat “real”; sem ele a UI pode entrar em modo demo.
- Troca de modelo = config + reload, não redeploy cloud.
- SPOF: máquina local / GPU; documentado em arquitectura.
