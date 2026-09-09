import type { ZodType } from 'zod'
import { HttpError, NetworkError, ValidationError } from './errors'
import { api, mergeSignals, type HttpClient } from './http-client'
import {
  type ErrorInterceptor,
  type RequestContext,
  loggingErrorInterceptor,
  notifyErrorInterceptor,
} from './interceptors'
import { ChatResponseSchema, type ChatResponse } from './schemas'

export type StreamRequestOptions = {
  path: string
  method?: string
  body?: unknown
  headers?: Record<string, string>
  /** Default 180_000 for chat streams. */
  timeoutMs?: number
  signal?: AbortSignal
  notify?: boolean
  client?: HttpClient
  /** Called for each parsed SSE event with JSON `data` (or raw string if not JSON). */
  onEvent: (event: string, data: unknown) => void
}

export type ParsedSseBlock = {
  event: string
  /** Raw data field (may span multiple `data:` lines). */
  data: string
}

/** Split an SSE text buffer into complete blocks; returns remainder. */
export function feedSseBuffer(buffer: string, chunk: string): { buffer: string; blocks: string[] } {
  const next = buffer + chunk
  const parts = next.split('\n\n')
  return { buffer: parts.pop() ?? '', blocks: parts }
}

/** Parse one SSE block (`event:` / `data:` lines). */
export function parseSseBlock(block: string): ParsedSseBlock | null {
  const lines = block.split('\n')
  let event = 'message'
  let data = ''
  for (const line of lines) {
    if (line.startsWith('event:')) event = line.slice(6).trim()
    if (line.startsWith('data:')) data += line.slice(5).trim()
  }
  if (!data) return null
  return { event, data }
}

/** Returns parsed JSON, or `null` if the payload is not valid JSON (skip block). */
function tryParseJson(raw: string): unknown | null {
  try {
    return JSON.parse(raw) as unknown
  } catch {
    return null
  }
}

/**
 * One-shot SSE POST/GET — shares URL resolve + interceptors with HttpClient.
 * No mid-stream retries (only connect / pre-body failures surface as typed errors).
 */
export async function streamRequest(opts: StreamRequestOptions): Promise<void> {
  const client = opts.client ?? api
  const method = (opts.method ?? (opts.body !== undefined ? 'POST' : 'GET')).toUpperCase()
  const timeoutMs = opts.timeoutMs ?? 180_000

  let reqCtx: RequestContext = {
    path: opts.path,
    method,
    headers: { ...opts.headers },
    body: opts.body,
    url: client.resolveUrl(opts.path),
  }

  for (const interceptor of client.onRequest) {
    reqCtx = await interceptor(reqCtx)
  }

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
      signal: mergeSignals(timeoutMs, opts.signal),
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
    let err: unknown = new NetworkError(msg, {
      cause,
      context: { path: reqCtx.path, method: reqCtx.method },
    })
    err = await runErrorInterceptors(client, err, reqCtx)
    if (opts.notify) notifyErrorInterceptor(err, reqCtx)
    throw err
  }

  if (!res.ok || !res.body) {
    const bodyText = await res.text().catch(() => '')
    let err: unknown = new HttpError(res.status || 0, bodyText || 'Stream sem corpo', {
      context: {
        path: reqCtx.path,
        method: reqCtx.method,
        status: res.status,
        body: bodyText.slice(0, 500),
      },
    })
    err = await runErrorInterceptors(client, err, reqCtx)
    if (opts.notify) notifyErrorInterceptor(err, reqCtx)
    throw err
  }

  const reader = res.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  try {
    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      const fed = feedSseBuffer(buffer, decoder.decode(value, { stream: true }))
      buffer = fed.buffer
      for (const block of fed.blocks) {
        dispatchSseBlock(block, opts.onEvent)
      }
    }
    if (buffer.trim()) {
      dispatchSseBlock(buffer, opts.onEvent)
    }
  } catch (cause) {
    if (cause instanceof DOMException && cause.name === 'AbortError') throw cause
    if (
      cause instanceof HttpError ||
      cause instanceof NetworkError ||
      cause instanceof ValidationError
    ) {
      let err: unknown = cause
      err = await runErrorInterceptors(client, err, reqCtx)
      if (opts.notify) notifyErrorInterceptor(err, reqCtx)
      throw err
    }
    // Propagate intentional stream errors (e.g. event: error) without wrapping
    if (cause instanceof Error) throw cause
    throw cause
  }
}

function dispatchSseBlock(block: string, onEvent: (event: string, data: unknown) => void): void {
  const parsed = parseSseBlock(block)
  if (!parsed) return
  const data = tryParseJson(parsed.data)
  if (data === null) return
  onEvent(parsed.event, data)
}

async function runErrorInterceptors(
  client: HttpClient,
  err: unknown,
  reqCtx: RequestContext,
): Promise<unknown> {
  const chain: ErrorInterceptor[] =
    client.onError.length > 0 ? client.onError : [loggingErrorInterceptor]
  let current = err
  for (const interceptor of chain) {
    current = await interceptor(current, reqCtx)
  }
  return current
}

function parseWithSchema<T>(schema: ZodType<T>, data: unknown, path: string): T {
  const parsed = schema.safeParse(data)
  if (!parsed.success) {
    throw new ValidationError('Resposta inválida do servidor', parsed.error.issues, {
      context: { path, method: 'POST' },
    })
  }
  return parsed.data
}

export type ChatStreamOpts = {
  regenerate?: boolean
  continue_reply?: boolean
  signal?: AbortSignal
  notify?: boolean
  client?: HttpClient
  timeoutMs?: number
}

/** SSE chat — same public behaviour as legacy client.chatStream. */
export async function chatStream(
  sessionId: string,
  text: string,
  onToken: (chunk: string) => void,
  opts?: ChatStreamOpts,
): Promise<ChatResponse> {
  let finalPayload: ChatResponse | null = null
  const path = '/v1/chat'

  await streamRequest({
    path,
    method: 'POST',
    body: {
      session_id: sessionId,
      text,
      stream: true,
      regenerate: opts?.regenerate ?? false,
      continue_reply: opts?.continue_reply ?? false,
    },
    timeoutMs: opts?.timeoutMs ?? 180_000,
    signal: opts?.signal,
    notify: opts?.notify,
    client: opts?.client,
    onEvent(event, data) {
      if (
        event === 'token' &&
        data &&
        typeof data === 'object' &&
        data !== null &&
        'text' in data
      ) {
        const t = (data as { text?: unknown }).text
        if (typeof t === 'string' || typeof t === 'number') onToken(String(t))
      }
      if (event === 'done') {
        finalPayload = parseWithSchema(ChatResponseSchema, data, path)
      }
      if (event === 'error') {
        const obj = data && typeof data === 'object' ? (data as Record<string, unknown>) : {}
        const msg =
          typeof obj.error === 'string'
            ? obj.error
            : typeof obj.reply === 'string'
              ? obj.reply
              : 'stream error'
        throw new Error(msg)
      }
    },
  })

  if (!finalPayload) {
    throw new Error('Stream terminou sem payload final')
  }
  return finalPayload
}
