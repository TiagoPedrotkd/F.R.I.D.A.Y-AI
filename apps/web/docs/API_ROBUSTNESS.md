# Robustez API — apps/web

Camada `HttpClient` (fetch nativo), endpoints tipados, Zod, retry com backoff+jitter, interceptors, ErrorBoundary e `useApi`.

## Fluxo

```
UI / store / useApi
        ↓
endpoints/*  (ou client.ts reexport)
        ↓
HttpClient.request  →  onRequest interceptors
        ↓
fetch (+ timeout 30s default, minInterval, GET cache)
        ↓
onResponse → Zod schema → DTO tipado
        ↓ falha retryable
backoff / Retry-After → retry
        ↓ falha final
onError → (notify?) reportApiError → store.error → ErrorNotice
```

## Ficheiros

| Ficheiro | Função |
|----------|--------|
| `src/api/http-client.ts` | Classe `HttpClient` + singleton `api` |
| `src/api/interceptors.ts` | Tipos + logging / notify |
| `src/api/http.ts` | `apiRequest` → `api.request` (compat) |
| `src/api/endpoints/` | Endpoints tipados (`defineEndpoint`) |
| `src/api/schemas.ts` | Schemas Zod + `z.infer` |
| `src/api/errors.ts` | `ApiError`, `HttpError`, `NetworkError`, `ValidationError` |
| `src/api/report.ts` | Log + `store.error` |
| `src/hooks/useApi.ts` | Hook para painéis |
| `src/components/ErrorBoundary.tsx` | Captura erros de render |
| `docs/API_ENDPOINTS.md` | Guia para criar endpoints |

## Defaults do HttpClient

| Opção | Default |
|-------|---------|
| `timeoutMs` | **30_000** |
| `retries` | 3 (tentativas totais) |
| `retryBaseMs` | 300 → `base * 2^attempt + jitter` |
| `minIntervalMs` | 0 (activar no client se UI fizer spam) |
| Cache GET | só com `cache: { ttlMs }` no request |

Em **429**, se existir header `Retry-After`, a espera de retry usa esse valor quando for maior que o backoff.

## Endpoints migrados

Definidos em `src/api/endpoints/` e reexportados por `client.ts` com a mesma assinatura pública (+ `opts?: EndpointCallOptions` opcional com `signal`).

| Helper | Path | Notas |
|--------|------|-------|
| `fetchStatus` | `GET /v1/status` | timeout 15s |
| `chat` | `POST /v1/chat` | timeout 120s, retries 2 |
| `fetchFinanceSummary` | `GET /v1/finance/summary` | timeout 10s, cache 5s |

`chatStream`, SSE, FormData e `tts` continuam no legado de `client.ts` (fora do JSON `HttpClient`).

Ver checklist completo em [API_ENDPOINTS.md](./API_ENDPOINTS.md).

## Retry

- Retry só se `isRetryable(err)` (network, timeout, 408, 429, 5xx)
- Sem retry em 4xx “normais” nem em `ValidationError`
- Erros trazem `context: { path, method, status, body }` para debug

## ErrorBoundary

Montado em `main.tsx` à volta de `AppShell`. Fallback HUD com “Tentar de novo”.
