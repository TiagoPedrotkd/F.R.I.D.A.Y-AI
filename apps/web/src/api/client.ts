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
  }
  session?: {
    last_country?: string | null
    last_news_context?: string | null
    last_language?: string
  }
  pending_confirmation?: PendingConfirmation | null
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
  const es = new EventSource(apiUrl(`/v1/sessions/${sessionId}/events`))
  const types = ['state', 'activity', 'partial_transcript', 'tool', 'error', 'done', 'ping']
  for (const t of types) {
    es.addEventListener(t, (ev) => {
      try {
        const parsed = JSON.parse((ev as MessageEvent).data)
        onEvent(t, parsed)
      } catch {
        onEvent(t, (ev as MessageEvent).data)
      }
    })
  }
  es.onerror = () => onEvent('error', { message: 'SSE disconnected' })
  return () => es.close()
}
