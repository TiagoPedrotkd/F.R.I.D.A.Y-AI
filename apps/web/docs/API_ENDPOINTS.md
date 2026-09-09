# Criar um endpoint tipado

Guia para adicionar um helper JSON type-safe sobre o `HttpClient`. Streaming SSE usa [`stream-client.ts`](../src/api/stream-client.ts). Uploads e binary ficam em [`client.ts`](../src/api/client.ts) até haver adaptadores dedicados.

## Checklist

1. **Schema Zod** em [`schemas.ts`](../src/api/schemas.ts) — preferir `.passthrough()` / `.optional()` em campos instáveis.
2. Exportar `type X = z.infer<typeof XSchema>`.
3. **Ficheiro** em `src/api/endpoints/<name>.ts` com `defineEndpoint` ou `defineParamEndpoint`.
4. Reexportar no barrel [`endpoints/index.ts`](../src/api/endpoints/index.ts).
5. Em [`client.ts`](../src/api/client.ts), manter o nome público antigo (wrapper fino) para não partir imports.
6. Teste em `src/api/__tests__/` (happy path + ValidationError).
7. Preferir passar `signal` a partir de `useApi`.

## Exemplo estático (GET)

```ts
// endpoints/prefs.ts
import { PrefsResponseSchema } from '../schemas'
import { defineEndpoint } from './types'

export const fetchPrefs = defineEndpoint({
  method: 'GET',
  path: '/v1/prefs',
  schema: PrefsResponseSchema,
  timeoutMs: 10_000,
  retries: 3,
  cache: { ttlMs: 3_000 }, // opcional — só GET
})
```

## Exemplo com params (POST)

```ts
import { ChatResponseSchema, type ChatResponse } from '../schemas'
import { defineParamEndpoint } from './types'

export const chat = defineParamEndpoint<{ sessionId: string; text: string }, ChatResponse>({
  method: 'POST',
  path: () => '/v1/chat',
  body: ({ sessionId, text }) => ({ session_id: sessionId, text }),
  schema: ChatResponseSchema,
  timeoutMs: 120_000,
  retries: 2,
})
```

## Stream SSE (`chatStream`)

```ts
import { chatStream } from '@/api/stream-client'
// ou via client.ts (mesma assinatura pública)

const final = await chatStream(sessionId, text, (token) => append(token), {
  signal,
  regenerate: false,
})
```

- Partilha `api.resolveUrl` + interceptors `onRequest` / `onError` com o `HttpClient`.
- **Sem** retry mid-stream; payload `done` validado com `ChatResponseSchema`.
- Parser utilitário: `feedSseBuffer` / `parseSseBlock` (testado em `__tests__/stream-client.test.ts`).

## Wrapper em `client.ts` (compat)

```ts
import { fetchPrefs as fetchPrefsEndpoint, type EndpointCallOptions } from './endpoints'

export async function fetchPrefs(opts?: EndpointCallOptions) {
  return fetchPrefsEndpoint(opts)
}
```

## Integração com React (`useApi`)

```tsx
import { useApi } from '@/hooks/useApi'
import { fetchFinanceSummary } from '@/api/client'

function FinanceSummaryCard({ year, month }: { year: number; month: number }) {
  const { data, error, loading, refetch } = useApi(
    (signal) => fetchFinanceSummary(year, month, { signal }),
    { deps: [year, month], notifyOnError: true },
  )

  if (loading) return <p>A carregar…</p>
  if (error) return <p role="alert">{error.message}</p>
  if (!data) return null

  return (
    <div>
      <p>Restante: {data.remaining} {data.currency}</p>
      <button type="button" onClick={() => void refetch()}>
        Actualizar
      </button>
    </div>
  )
}
```

- **Store / chat / sessão:** continua a chamar helpers do `client` dentro das slices Zustand.
- **Painéis locais:** `useApi` + `signal` para cancelar ao desmontar.

## Interceptors (opcional)

```ts
import { api } from '@/api/http-client'

api.onRequest.push((ctx) => ({
  ...ctx,
  headers: { ...ctx.headers, 'X-Client': 'friday-web' },
}))
```

Erros em DEV passam por `loggingErrorInterceptor`. Com `notify: true` no request, a falha final chama `reportApiError`.

## Fora deste path (ainda legado)

| Tipo | Onde |
|------|------|
| `EventSource` (`subscribeEvents`) | `client.ts` (próximo: reutilizar parser SSE) |
| FormData (`stt`, uploads) | `client.ts` |
| Binary (`tts`) | `client.ts` |
| HA / Google / mail / finance CRUD | `client.ts` |
