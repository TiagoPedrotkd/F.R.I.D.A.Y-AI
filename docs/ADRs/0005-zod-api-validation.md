# ADR 0005 — Validação Zod na API client

## Context

Tipos TypeScript no client não protegem contra JSON inesperado da API (campos em falta, shapes errados).

## Decision

Introduzir **Zod** + `apiRequest` (`apps/web/src/api/http.ts`) com retry/backoff e erros tipados. Migrar endpoints críticos primeiro (`/v1/status`, `/v1/chat`, `/v1/finance/summary`).

## Consequences

- Falhas de schema → `ValidationError` (não retry); mensagens PT via `toUserMessage`.
- Schemas em `schemas.ts` são a fonte de tipos (`z.infer`).
- Bundle +~zod; aceitável vs robustez.
