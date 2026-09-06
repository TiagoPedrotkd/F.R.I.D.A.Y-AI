import type { ZodType } from 'zod'
import type { HttpClient, HttpRequestOptions } from '../http-client'
import { api } from '../http-client'

export type EndpointDefinition<T> = {
  method?: string
  path: string | ((params: never) => string)
  schema: ZodType<T>
  timeoutMs?: number
  retries?: number
  retryBaseMs?: number
  cache?: { ttlMs: number }
}

export type EndpointCallOptions = {
  signal?: AbortSignal
  notify?: boolean
  skipCache?: boolean
  headers?: Record<string, string>
  client?: HttpClient
}

type StaticDef<T> = {
  method?: string
  path: string
  schema: ZodType<T>
  timeoutMs?: number
  retries?: number
  retryBaseMs?: number
  cache?: { ttlMs: number }
}

type ParamDef<TParams, T> = {
  method?: string
  path: (params: TParams) => string
  schema: ZodType<T>
  timeoutMs?: number
  retries?: number
  retryBaseMs?: number
  cache?: { ttlMs: number }
  body?: (params: TParams) => unknown
}

/** No-arg typed endpoint (e.g. GET /v1/status). */
export function defineEndpoint<T>(def: StaticDef<T>) {
  return (opts?: EndpointCallOptions): Promise<T> => {
    const client = opts?.client ?? api
    const req: HttpRequestOptions<T> = {
      path: def.path,
      method: def.method ?? 'GET',
      schema: def.schema,
      timeoutMs: def.timeoutMs,
      retries: def.retries,
      retryBaseMs: def.retryBaseMs,
      cache: def.cache,
      signal: opts?.signal,
      notify: opts?.notify,
      skipCache: opts?.skipCache,
      headers: opts?.headers,
    }
    return client.request(req)
  }
}

/** Parametrised typed endpoint (path/body from params). */
export function defineParamEndpoint<TParams, T>(def: ParamDef<TParams, T>) {
  return (params: TParams, opts?: EndpointCallOptions): Promise<T> => {
    const client = opts?.client ?? api
    const req: HttpRequestOptions<T> = {
      path: def.path(params),
      method: def.method ?? (def.body ? 'POST' : 'GET'),
      schema: def.schema,
      body: def.body?.(params),
      timeoutMs: def.timeoutMs,
      retries: def.retries,
      retryBaseMs: def.retryBaseMs,
      cache: def.cache,
      signal: opts?.signal,
      notify: opts?.notify,
      skipCache: opts?.skipCache,
      headers: opts?.headers,
    }
    return client.request(req)
  }
}
