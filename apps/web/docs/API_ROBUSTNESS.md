# Robustez API — apps/web

Camada `HttpClient` (fetch nativo), endpoints tipados, Zod, retry com backoff+jitter, interceptors, ErrorBoundary e `useApi`. Stream SSE partilha URL/interceptors via `stream-client` (sem retry mid-stream).

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

Stream (chat):

```
sessionSlice.sendText
        ↓
chatStream (stream-client)
        ↓
streamRequest → onRequest → fetch SSE → parse event/data → onToken / done Zod
```

## Ficheiros

| Ficheiro | Função |
|----------|--------|
| `src/api/http-client.ts` | Classe `HttpClient` + singleton `api` + `mergeSignals` |
| `src/api/stream-client.ts` | `streamRequest`, parser SSE, `chatStream` |
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
| `chat` | `POST /v1/chat` | timeout 120s, retries 2 (não-stream) |
| `chatStream` | `POST /v1/chat` SSE | `stream-client`; timeout 180s; **sem** retry mid-stream |
| `fetchFinanceSummary` | `GET /v1/finance/summary` | timeout 10s, cache 5s |
| `createSession` | `POST /v1/sessions` | timeout 8s |
| `listSessions` | `GET /v1/sessions` | timeout 8s |
| `getSession` | `GET /v1/sessions/{id}` | timeout 8s |
| `fetchPrefs` / `savePrefs` | `/v1/prefs` | timeout 8s |
| `confirm` | `POST /v1/confirm` | timeout 15s |
| `sendFeedback` | `POST /v1/feedback` | timeout 10s |
| `fetchAlerts` | `GET /v1/alerts` | timeout 20s |

Ainda legado em `client.ts`: `EventSource` (`subscribeEvents`), FormData (`stt`, uploads), binary (`tts`), HA/Google/mail/finance CRUD.

Ver checklist completo em [API_ENDPOINTS.md](./API_ENDPOINTS.md).

## Retry

- Retry só se `isRetryable(err)` (network, timeout, 408, 429, 5xx)
- Sem retry em 4xx “normais” nem em `ValidationError`
- Stream SSE: **sem** retry após o body começar; erros tipados no connect / HTTP pré-stream
- Erros trazem `context: { path, method, status, body }` para debug

## ErrorBoundary

Montado em `main.tsx` à volta de `AppShell`. Fallback HUD com “Tentar de novo”.
