import { vi } from 'vitest'
import { defaultPrefs } from '@/demo/fixtures'
import { useAppStore } from '@/state/store'
import type { FridayState } from '@/state/machine'
import type { Message } from '@/state/store'
import { prefsPt } from './fixtures'

type StoreSlice = {
  state: FridayState
  sessionId: string | null
  messages: Message[]
  activity: never[]
  country: string | null
  sources: never[]
  pending: null
  alerts: never[]
  offerMonitorPath: string | null
  prefs: typeof defaultPrefs
  backendOk: boolean
  llmOk: boolean
  haEnabled: boolean
  haOk: boolean | null
  haUrl: string | null
  demoForced: boolean
  error: string | null
  draft: string
  mic: null
  ttsAbort: null
  settingsOpen: boolean
  casaOpen: boolean
  saudeOpen: boolean
  financasOpen: boolean
  agendaOpen: boolean
  mailOpen: boolean
  sidebarOpen: boolean
  googleEnabled: boolean
  googleConfigured: boolean
  financeEnabled: boolean
  financeConfigured: boolean
  casaLoading: boolean
  casaError: string | null
  casaLights: never[]
  casaSwitches: never[]
  casaEnergy: never[]
  casaSensors: never[]
}

const SAFE_DEFAULTS: StoreSlice = {
  state: 'idle',
  sessionId: 'test-session',
  messages: [],
  activity: [],
  country: null,
  sources: [],
  pending: null,
  alerts: [],
  offerMonitorPath: null,
  prefs: { ...prefsPt },
  backendOk: true,
  llmOk: true,
  haEnabled: false,
  haOk: null,
  haUrl: null,
  demoForced: false,
  error: null,
  draft: '',
  mic: null,
  ttsAbort: null,
  settingsOpen: false,
  casaOpen: false,
  saudeOpen: false,
  financasOpen: false,
  agendaOpen: false,
  mailOpen: false,
  sidebarOpen: false,
  googleEnabled: false,
  googleConfigured: false,
  financeEnabled: true,
  financeConfigured: true,
  casaLoading: false,
  casaError: null,
  casaLights: [],
  casaSwitches: [],
  casaEnergy: [],
  casaSensors: [],
}

/** Reset Zustand app store to deterministic defaults for isolation. */
export function resetAppStore(partial?: Partial<StoreSlice>): void {
  useAppStore.setState({ ...SAFE_DEFAULTS, ...partial, prefs: { ...prefsPt, ...partial?.prefs } })
}

type JsonHandler = (url: string, init?: RequestInit) => unknown | Promise<unknown>

/**
 * Stub global fetch with path→JSON handlers.
 * Keys match substring of the request URL (e.g. '/v1/status').
 */
export function mockFetchJson(handlers: Record<string, JsonHandler | unknown>): void {
  vi.stubGlobal(
    'fetch',
    vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input)
      for (const [key, handler] of Object.entries(handlers)) {
        if (!url.includes(key)) continue
        const body = typeof handler === 'function' ? await handler(url, init) : handler
        return new Response(JSON.stringify(body), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        })
      }
      return new Response(JSON.stringify({ error: `unmocked ${url}` }), { status: 404 })
    }),
  )
}
