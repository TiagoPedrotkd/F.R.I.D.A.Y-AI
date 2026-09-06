import type { ZodType } from 'zod'
import { apiUrl } from '@/platform/config'
import { HttpError, NetworkError, ValidationError, isRetryable } from './errors'
import {
  type ErrorInterceptor,
  type RequestContext,
  type RequestInterceptor,
  type ResponseInterceptor,
  loggingErrorInterceptor,
  notifyErrorInterceptor,
} from './interceptors'

export type HttpClientConfig = {
  /** Default request timeout. Default 30_000. */
  timeoutMs?: number
  /** Total attempts including the first. Default 3. */
  retries?: number
  /** Base delay before first retry (ms). Default 300. */
  retryBaseMs?: number
  /** Minimum gap between outbound requests (ms). Default 0. */
  minIntervalMs?: number
  resolveUrl?: (path: string) => string
}

export type CacheOption = {
  ttlMs: number
}

export type HttpRequestOptions<T> = {
  path: string
  schema: ZodType<T>
  method?: string
  body?: unknown
  headers?: Record<string, string>
  timeoutMs?: number
  retries?: number
  retryBaseMs?: number
  /** If true, run notifyErrorInterceptor on final failure. Default false. */
  notify?: boolean
  signal?: AbortSignal
  /** In-memory GET cache. Ignored for non-GET. */
  cache?: CacheOption
  skipCache?: boolean
}

type CacheEntry = { expires: number; data: unknown }

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

function backoffMs(attempt: number, baseMs: number): number {
  const exp = baseMs * 2 ** attempt
  const jitter = Math.floor(Math.random() * baseMs)
  return exp + jitter
}

function mergeSignals(timeoutMs: number, external?: AbortSignal): AbortSignal {
  const timeout = AbortSignal.timeout(timeoutMs)
  if (!external) return timeout
  if (typeof AbortSignal.any === 'function') {
    return AbortSignal.any([timeout, external])
  }
  return timeout
}

function parseRetryAfterMs(res: Response): number | null {
  const raw = res.headers.get('Retry-After')
  if (!raw) return null
  const asNum = Number(raw)
  if (!Number.isNaN(asNum) && asNum >= 0) return Math.floor(asNum * 1000)
  const date = Date.parse(raw)
  if (!Number.isNaN(date)) return Math.max(0, date - Date.now())
  return null
}

function cacheKey(method: string, path: string, body: unknown): string {
  const bodyPart = body === undefined ? '' : JSON.stringify(body)
  return `${method}:${path}:${bodyPart}`
}

export class HttpClient {
  readonly timeoutMs: number
  readonly retries: number
  readonly retryBaseMs: number
  readonly minIntervalMs: number
  readonly resolveUrl: (path: string) => string

  onRequest: RequestInterceptor[] = []
  onResponse: ResponseInterceptor[] = []
  onError: ErrorInterceptor[] = [loggingErrorInterceptor]

  private cache = new Map<string, CacheEntry>()
  private lastRequestAt = 0
  private queue: Promise<void> = Promise.resolve()

  constructor(config: HttpClientConfig = {}) {
    this.timeoutMs = config.timeoutMs ?? 30_000
    this.retries = config.retries ?? 3
    this.retryBaseMs = config.retryBaseMs ?? 300
    this.minIntervalMs = config.minIntervalMs ?? 0
    this.resolveUrl = config.resolveUrl ?? apiUrl
  }

  clearCache(pathPrefix?: string): void {
    if (!pathPrefix) {
      this.cache.clear()
      return
    }
    for (const key of this.cache.keys()) {
      if (key.includes(`:${pathPrefix}`) || key.includes(`:${pathPrefix}?`)) {
        this.cache.delete(key)
      }
    }
  }

  async request<T>(opts: HttpRequestOptions<T>): Promise<T> {
    const method = (opts.method ?? (opts.body !== undefined ? 'POST' : 'GET')).toUpperCase()
    const maxAttempts = Math.max(1, opts.retries ?? this.retries)
    const baseMs = opts.retryBaseMs ?? this.retryBaseMs
    const timeoutMs = opts.timeoutMs ?? this.timeoutMs

    let reqCtx: RequestContext = {
      path: opts.path,
      method,
      headers: { ...opts.headers },
      body: opts.body,
      url: this.resolveUrl(opts.path),
    }

    for (const interceptor of this.onRequest) {
      reqCtx = await interceptor(reqCtx)
    }

    const useCache = method === 'GET' && opts.cache && !opts.skipCache && opts.cache.ttlMs > 0
    const key = cacheKey(reqCtx.method, reqCtx.path, reqCtx.body)

    if (useCache) {
      const hit = this.cache.get(key)
      if (hit && hit.expires > Date.now()) {
        return hit.data as T
      }
    }

    let lastError: unknown

    for (let attempt = 0; attempt < maxAttempts; attempt++) {
      try {
        const data = await this.once(reqCtx, opts.schema, timeoutMs, opts.signal)
        if (useCache && opts.cache) {
          this.cache.set(key, { expires: Date.now() + opts.cache.ttlMs, data })
        }
        return data
      } catch (err) {
        lastError = err
        for (const interceptor of this.onError) {
          lastError = await interceptor(lastError, reqCtx)
        }

        const canRetry = isRetryable(lastError) && attempt < maxAttempts - 1
        if (!canRetry) break

        let wait = backoffMs(attempt, baseMs)
        if (lastError instanceof HttpError && lastError.status === 429) {
          const ra = lastError.context?.retryAfterMs
          if (typeof ra === 'number' && ra > wait) wait = ra
        }
        await sleep(wait)
      }
    }

    if (opts.notify) {
      notifyErrorInterceptor(lastError, reqCtx)
    }
    throw lastError
  }

  private async throttle(): Promise<void> {
    if (this.minIntervalMs <= 0) return
    const run = async () => {
      const gap = this.minIntervalMs - (Date.now() - this.lastRequestAt)
      if (gap > 0) await sleep(gap)
      this.lastRequestAt = Date.now()
    }
    this.queue = this.queue.then(run, run)
    await this.queue
  }

  private async once<T>(
    reqCtx: RequestContext,
    schema: ZodType<T>,
    timeoutMs: number,
    external?: AbortSignal,
  ): Promise<T> {
    await this.throttle()

    const headers: Record<string, string> = { ...reqCtx.headers }
    if (reqCtx.body !== undefined && !headers['Content-Type']) {
      headers['Content-Type'] = 'application/json'
    }

    let res: Response
    try {
      res = await fetch(reqCtx.url, {
        method: reqCtx.method,
        headers,
        body: reqCtx.body !== undefined ? JSON.stringify(reqCtx.body) : undefined,
        signal: mergeSignals(timeoutMs, external),
      })
    } catch (cause) {
      if (cause instanceof DOMException && cause.name === 'AbortError') {
        throw cause
      }
      const msg =
        cause instanceof Error && (cause.name === 'TimeoutError' || /timeout/i.test(cause.message))
          ? 'API sem resposta (timeout).'
          : cause instanceof Error
            ? cause.message
            : 'Falha de rede'
      throw new NetworkError(msg, {
        cause,
        context: { path: reqCtx.path, method: reqCtx.method },
      })
    }

    if (!res.ok) {
      const bodyText = await res.text().catch(() => '')
      const retryAfterMs = parseRetryAfterMs(res)
      throw new HttpError(res.status, bodyText, {
        context: {
          path: reqCtx.path,
          method: reqCtx.method,
          status: res.status,
          body: bodyText.slice(0, 500),
          ...(retryAfterMs != null ? { retryAfterMs } : {}),
        },
      })
    }

    const raw = await this.parseJson(res, reqCtx)
    let respCtx = {
      request: reqCtx,
      status: res.status,
      headers: res.headers,
      data: raw,
    }
    for (const interceptor of this.onResponse) {
      respCtx = await interceptor(respCtx)
    }

    const parsed = schema.safeParse(respCtx.data)
    if (!parsed.success) {
      throw new ValidationError('Resposta inválida do servidor', parsed.error.issues, {
        context: { path: reqCtx.path, method: reqCtx.method, status: res.status },
      })
    }
    return parsed.data
  }

  private async parseJson(res: Response, reqCtx: RequestContext): Promise<unknown> {
    const text = await res.text().catch(() => '')
    if (!text) return null
    try {
      return JSON.parse(text) as unknown
    } catch (cause) {
      throw new ValidationError('Resposta não é JSON válido', cause, {
        context: { path: reqCtx.path, method: reqCtx.method, status: res.status },
      })
    }
  }
}

/** Shared app client (agent-api via apiUrl). */
export const api = new HttpClient()
