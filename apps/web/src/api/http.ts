import type { ZodType } from 'zod'
import { api, type HttpRequestOptions } from './http-client'

export type ApiRequestOptions<T> = HttpRequestOptions<T>

/**
 * Fetch + Zod validate with exponential backoff.
 * Thin wrapper around the shared {@link api} HttpClient for backward compatibility.
 */
export async function apiRequest<T>(opts: {
  path: string
  schema: ZodType<T>
  method?: string
  body?: unknown
  headers?: Record<string, string>
  timeoutMs?: number
  retries?: number
  retryBaseMs?: number
  notify?: boolean
  signal?: AbortSignal
  cache?: { ttlMs: number }
  skipCache?: boolean
}): Promise<T> {
  return api.request(opts)
}

export { api, HttpClient } from './http-client'
export type { HttpClientConfig, HttpRequestOptions, CacheOption } from './http-client'
