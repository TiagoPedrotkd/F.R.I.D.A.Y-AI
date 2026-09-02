import { apiUrl } from '../platform/config'

export type ActivityStep = {
  label: string
  status: string
  tool?: string
  monitor?: string
}

export type SourceItem = {
  title: string
  url: string
  snippet?: string
  source?: string
  date?: string | null
  kind?: 'document' | 'memory' | 'web' | 'news' | string | null
}

export type PendingConfirmation = {
  action: string
  target: string
  summary: string
  consequences?: string
}

export type ChatResponse = {
  reply: string
  metadata: Record<string, unknown>
  activity: ActivityStep[]
  ui: {
    sources?: SourceItem[]
    headlines_only?: boolean
    not_realtime_prices?: boolean
    country?: string
    kind?: string
    opened?: boolean
    monitor_kind?: string | null
    offer_monitor?: boolean
    monitor_path?: string | null
    grounding_score?: number | null
    grounded?: boolean
    confidence_score?: number | null
    confidence_level?: string | null
    hallucination_risk?: string | null
  }
  session?: {
    last_country?: string | null
    last_news_context?: string | null
    last_language?: string
  }
  pending_confirmation?: PendingConfirmation | null
  grounding?: { score?: number; grounded?: boolean }
  confidence?: { score?: number; level?: string; hallucination_risk?: string }
  error?: string
}

export type StatusResponse = {
  status: string
  backend: boolean
  demo: boolean
  llm: { ok: boolean; model?: string; error?: string | null }
  auto_open_monitors?: boolean
}

function withTimeout(ms: number): AbortSignal {
  return AbortSignal.timeout(ms)
}

async function json<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const text = await res.text().catch(() => '')
    throw new Error(text || `HTTP ${res.status}`)
  }
  return res.json() as Promise<T>
}

export async function fetchStatus(): Promise<StatusResponse> {
  return json(await fetch(apiUrl('/v1/status'), { signal: withTimeout(8000) }))
}

export async function createSession(): Promise<{ id: string }> {
  return json(
    await fetch(apiUrl('/v1/sessions'), {
      method: 'POST',
      signal: withTimeout(8000),
    }),
  )
}

export async function chat(sessionId: string, text: string): Promise<ChatResponse> {
  return json(
    await fetch(apiUrl('/v1/chat'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: sessionId, text }),
      signal: withTimeout(120000),
    }),
  )
}

export async function chatStream(
  sessionId: string,
  text: string,
  onToken: (chunk: string) => void,
  opts?: { regenerate?: boolean; continue_reply?: boolean },
): Promise<ChatResponse> {
  const res = await fetch(apiUrl('/v1/chat'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      session_id: sessionId,
      text,
      stream: true,
      regenerate: opts?.regenerate ?? false,
      continue_reply: opts?.continue_reply ?? false,
    }),
    signal: withTimeout(180000),
  })
  if (!res.ok || !res.body) {
    const t = await res.text().catch(() => '')
    throw new Error(t || `HTTP ${res.status}`)
  }
  const reader = res.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  let finalPayload: ChatResponse | null = null
  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    const parts = buffer.split('\n\n')
    buffer = parts.pop() ?? ''
    for (const block of parts) {
      const lines = block.split('\n')
      let event = 'message'
      let data = ''
      for (const line of lines) {
        if (line.startsWith('event:')) event = line.slice(6).trim()
        if (line.startsWith('data:')) data += line.slice(5).trim()
      }
      if (!data) continue
      try {
        const parsed = JSON.parse(data)
        if (event === 'token' && parsed.text) onToken(String(parsed.text))
        if (event === 'done') finalPayload = parsed as ChatResponse
        if (event === 'error') throw new Error(parsed.error || parsed.reply || 'stream error')
      } catch (e) {
        if (e instanceof SyntaxError) continue
        throw e
      }
    }
  }
  if (!finalPayload) throw new Error('Stream terminou sem payload final')
  return finalPayload
}

export async function sendFeedback(payload: {
  session_id: string
  message_id?: string
  rating: 'up' | 'down'
  reply_text?: string
  user_text?: string
  comment?: string
  grounding_score?: number | null
}): Promise<{ ok: boolean }> {
  return json(
    await fetch(apiUrl('/v1/feedback'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
      signal: withTimeout(10000),
    }),
  )
}

export async function fetchPrefs(): Promise<{
  prefs: Record<string, unknown>
  prompt_version?: string
}> {
  return json(await fetch(apiUrl('/v1/prefs'), { signal: withTimeout(8000) }))
}

export async function savePrefs(patch: Record<string, unknown>): Promise<{
  prefs: Record<string, unknown>
}> {
  return json(
    await fetch(apiUrl('/v1/prefs'), {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(patch),
      signal: withTimeout(8000),
    }),
  )
}

export async function listSessions(): Promise<{
  sessions: Array<{
    id: string
    updated_at?: number
    message_count?: number
    preview?: string
    last_country?: string | null
    last_language?: string
  }>
}> {
  return json(await fetch(apiUrl('/v1/sessions'), { signal: withTimeout(8000) }))
}

export async function getSession(sessionId: string): Promise<{
  id: string
  messages: Array<{ role: string; content: string }>
  session_summary?: string
  last_country?: string | null
  last_language?: string
}> {
  return json(
    await fetch(apiUrl(`/v1/sessions/${encodeURIComponent(sessionId)}`), {
      signal: withTimeout(8000),
    }),
  )
}

export async function uploadAttachment(
  sessionId: string,
  file: File,
): Promise<{
  ok: boolean
  filename: string
  kind: string
  preview: string
  vision?: boolean
  pending?: number
}> {
  const form = new FormData()
  form.append('file', file)
  return json(
    await fetch(apiUrl(`/v1/uploads?session_id=${encodeURIComponent(sessionId)}`), {
      method: 'POST',
      body: form,
      signal: withTimeout(60000),
    }),
  )
}

export async function confirm(
  sessionId: string,
  decision: 'confirm' | 'cancel',
): Promise<{ reply: string; decision: string }> {
  return json(
    await fetch(apiUrl('/v1/confirm'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: sessionId, decision }),
      signal: withTimeout(15000),
    }),
  )
}

export async function seedDemoConfirmation(sessionId: string): Promise<{
  reply: string
  pending_confirmation: PendingConfirmation
}> {
  const url = apiUrl(`/v1/demo/pending-confirmation?session_id=${encodeURIComponent(sessionId)}`)
  return json(await fetch(url, { method: 'POST', signal: withTimeout(10000) }))
}

export async function stt(blob: Blob, sessionId?: string, language = 'pt'): Promise<{ text: string }> {
  const form = new FormData()
  form.append('audio', blob, 'speech.wav')
  const q = new URLSearchParams({ language })
  if (sessionId) q.set('session_id', sessionId)
  return json(
    await fetch(apiUrl(`/v1/stt?${q}`), {
      method: 'POST',
      body: form,
      signal: withTimeout(120000),
    }),
  )
}

export async function tts(
  text: string,
  sessionId?: string,
  opts?: { rate?: number; language?: 'pt' | 'en' },
): Promise<ArrayBuffer> {
  const res = await fetch(apiUrl('/v1/tts'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      text,
      session_id: sessionId,
      rate: opts?.rate,
      language: opts?.language,
    }),
    signal: withTimeout(60000),
  })
  if (!res.ok) throw new Error(`TTS HTTP ${res.status}`)
  return res.arrayBuffer()
}

export function subscribeEvents(
  sessionId: string,
  onEvent: (type: string, data: unknown) => void,
): () => void {
  let closed = false
  let es: EventSource | null = null
  let retryMs = 1000
  let timer: ReturnType<typeof setTimeout> | null = null

  const types = ['state', 'activity', 'partial_transcript', 'token', 'tool', 'error', 'done', 'ping']

  const attach = () => {
    if (closed) return
    es = new EventSource(apiUrl(`/v1/sessions/${sessionId}/events`))
    for (const t of types) {
      es.addEventListener(t, (ev) => {
        retryMs = 1000
        try {
          const parsed = JSON.parse((ev as MessageEvent).data)
          onEvent(t, parsed)
        } catch {
          onEvent(t, (ev as MessageEvent).data)
        }
      })
    }
    es.onopen = () => {
      retryMs = 1000
      onEvent('sse', { status: 'connected' })
    }
    es.onerror = () => {
      onEvent('error', { message: 'SSE disconnected', recoverable: true })
      es?.close()
      es = null
      if (closed) return
      const wait = Math.min(15000, retryMs)
      retryMs = Math.min(15000, retryMs * 1.8)
      timer = setTimeout(attach, wait)
    }
  }

  attach()

  return () => {
    closed = true
    if (timer) clearTimeout(timer)
    es?.close()
  }
}
