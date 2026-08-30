import { create } from 'zustand'
import type { ActivityStep, PendingConfirmation, SourceItem } from '../api/client'
import * as api from '../api/client'
import { DEMO_FIXTURES, defaultPrefs, type Prefs } from '../demo/fixtures'
import { playWavBytes, startMicRecording, type MicRecorder } from '../platform/audio'
import { getAgentApiBase } from '../platform/config'
import { openMonitorPath } from '../platform/links'
import { getJson, setJson } from '../platform/storage'
import { type FridayState, transition } from './machine'

export type Message = {
  id: string
  role: 'user' | 'assistant' | 'system'
  text: string
  demo?: boolean
  sources?: SourceItem[]
}

type AppStore = {
  state: FridayState
  sessionId: string | null
  messages: Message[]
  activity: ActivityStep[]
  country: string | null
  sources: SourceItem[]
  pending: PendingConfirmation | null
  offerMonitorPath: string | null
  prefs: Prefs
  backendOk: boolean
  llmOk: boolean
  demoForced: boolean
  error: string | null
  draft: string
  mic: MicRecorder | null
  ttsAbort: AbortController | null
  settingsOpen: boolean
  sidebarOpen: boolean

  setDraft: (v: string) => void
  setState: (s: FridayState) => void
  setPrefs: (p: Partial<Prefs>) => void
  setSettingsOpen: (v: boolean) => void
  setSidebarOpen: (v: boolean) => void
  bootstrap: () => Promise<void>
  sendText: (text?: string) => Promise<void>
  toggleMic: () => Promise<void>
  stopSpeaking: () => void
  resolveConfirm: (decision: 'confirm' | 'cancel') => Promise<void>
  openMonitor: () => void
  seedDemoConfirm: () => Promise<void>
}

function uid() {
  return Math.random().toString(36).slice(2, 10)
}

function applyPrefsDom(prefs: Prefs) {
  document.documentElement.classList.toggle('high-contrast', prefs.highContrast)
  document.documentElement.classList.toggle('reduce-motion', prefs.reducedMotion)
}

export const useAppStore = create<AppStore>((set, get) => ({
  state: 'connecting',
  sessionId: null,
  messages: [],
  activity: [],
  country: null,
  sources: [],
  pending: null,
  offerMonitorPath: null,
  prefs: { ...defaultPrefs, ...getJson<Partial<Prefs>>('prefs', {}) },
  backendOk: false,
  llmOk: false,
  demoForced: false,
  error: null,
  draft: '',
  mic: null,
  ttsAbort: null,
  settingsOpen: false,
  sidebarOpen: false,

  setDraft: (v) => set({ draft: v }),
  setState: (s) => set((st) => ({ state: transition(st.state, s) })),
  setPrefs: (p) => {
    const prefs = { ...get().prefs, ...p }
    setJson('prefs', prefs)
    applyPrefsDom(prefs)
    set({ prefs })
  },
  setSettingsOpen: (v) => set({ settingsOpen: v }),
  setSidebarOpen: (v) => set({ sidebarOpen: v }),

  bootstrap: async () => {
    applyPrefsDom(get().prefs)
    set({ state: transition(get().state, 'connecting'), error: null })
    try {
      const status = await api.fetchStatus()
      const session = await api.createSession()
      const demoForced = status.demo || get().prefs.demoMode
      set({
        sessionId: session.id,
        backendOk: true,
        llmOk: status.llm.ok,
        demoForced,
        state: transition(get().state, 'idle'),
        prefs: {
          ...get().prefs,
          autoOpenMonitors: status.auto_open_monitors ?? get().prefs.autoOpenMonitors,
        },
      })
      api.subscribeEvents(session.id, (type, raw) => {
        const data = (raw as { data?: Record<string, unknown> })?.data ?? raw
        if (type === 'state' && data && typeof data === 'object' && 'state' in (data as object)) {
          const s = (data as { state: FridayState }).state
          if (s) get().setState(s)
        }
      })
    } catch (e) {
      const msg =
        e instanceof Error && (e.name === 'TimeoutError' || e.name === 'AbortError')
          ? 'API sem resposta (timeout). Reinicia o agent-api.'
          : e instanceof Error
            ? e.message
            : 'Falha ao ligar'
      set({
        backendOk: false,
        llmOk: false,
        demoForced: true,
        state: transition(get().state, 'idle'),
        error: msg,
        messages: [
          {
            id: uid(),
            role: 'system',
            text: 'Backend indisponível. Modo demonstração activo — reinicia o agent-api se estiveres a usar a API real.',
            demo: true,
          },
        ],
      })
    }
  },

  sendText: async (text) => {
    const content = (text ?? get().draft).trim()
    if (!content) return
    const { sessionId, prefs, demoForced, state } = get()
    if (state === 'speaking' && prefs.interrupt) get().stopSpeaking()

    set({
      draft: '',
      messages: [...get().messages, { id: uid(), role: 'user', text: content }],
      state: transition(get().state, 'thinking'),
      error: null,
      activity: [{ label: 'A interpretar o pedido…', status: 'running' }],
    })

    const useDemo = demoForced || prefs.demoMode || !sessionId
    try {
      let replyText: string
      let activity: ActivityStep[]
      let sources: SourceItem[] = []
      let country: string | null = get().country
      let pending: PendingConfirmation | null = null
      let offerMonitorPath: string | null = null
      let demo = false

      if (useDemo) {
        demo = true
        const fixture =
          /not[ií]cia|news|financ/i.test(content) ? DEMO_FIXTURES.news : DEMO_FIXTURES.chat
        replyText = fixture.reply
        activity = fixture.activity
        sources = fixture.ui.sources ?? []
        country = fixture.ui.country ?? country
        offerMonitorPath = fixture.ui.monitor_path ?? null
        await new Promise((r) => setTimeout(r, 400))
      } else {
        const res = await api.chat(sessionId!, content)
        replyText = res.reply
        activity = res.activity ?? []
        sources = res.ui?.sources ?? []
        country = res.ui?.country ?? res.session?.last_country ?? country
        pending = res.pending_confirmation ?? null
        offerMonitorPath =
          res.ui?.monitor_path ??
          (res.ui?.offer_monitor
            ? `${res.ui?.monitor_kind === 'finance' ? '/monitors/finance_snapshot.html' : '/monitors/world_snapshot.html'}${
                country && country !== 'WW' ? `?country=${country}` : ''
              }`
            : null)
        if (res.error) set({ error: res.error })
      }

      set({
        messages: [
          ...get().messages,
          { id: uid(), role: 'assistant', text: replyText, demo, sources },
        ],
        activity,
        sources,
        country,
        pending,
        offerMonitorPath,
        state: transition(
          get().state,
          pending ? 'awaiting_confirmation' : prefs.ttsEnabled && prefs.autoplay ? 'speaking' : 'idle',
        ),
      })

      if (prefs.autoOpenMonitors && offerMonitorPath) {
        openMonitorPath(offerMonitorPath, getAgentApiBase())
      }

      if (prefs.ttsEnabled && prefs.autoplay && !pending && !useDemo && sessionId) {
        try {
          const abort = new AbortController()
          set({ ttsAbort: abort })
          const bytes = await api.tts(replyText, sessionId, {
            rate: prefs.rate,
            language: prefs.language,
          })
          await playWavBytes(bytes, { volume: prefs.volume, signal: abort.signal })
        } catch {
          /* TTS optional */
        } finally {
          set({ ttsAbort: null, state: transition(get().state, pending ? 'awaiting_confirmation' : 'idle') })
        }
      } else if (!pending) {
        set({ state: transition(get().state, 'idle') })
      }
    } catch (e) {
      set({
        state: transition(get().state, 'error'),
        error: e instanceof Error ? e.message : 'Erro no chat',
        messages: [
          ...get().messages,
          {
            id: uid(),
            role: 'assistant',
            text: 'Não consegui completar o pedido. Verifica o LM Studio e tenta novamente.',
          },
        ],
      })
    }
  },

  toggleMic: async () => {
    const { mic, state, prefs } = get()
    if (mic) {
      set({ state: transition(state, 'transcribing') })
      try {
        const blob = await mic.stop()
        set({ mic: null })
        if (get().demoForced || prefs.demoMode) {
          set({ draft: '[DEMO] Que horas são?', state: transition(get().state, 'idle') })
          await get().sendText('[DEMO] Que horas são?')
          return
        }
        const { text } = await api.stt(blob, get().sessionId ?? undefined, prefs.language)
        if (!text.trim()) {
          set({
            state: transition(get().state, 'idle'),
            error: 'Não percebi. Podes repetir?',
          })
          return
        }
        set({ draft: text })
        await get().sendText(text)
      } catch (e) {
        set({
          mic: null,
          state: transition(get().state, 'error'),
          error: e instanceof Error ? e.message : 'Erro no microfone',
        })
      }
      return
    }
    if (state === 'speaking' && prefs.interrupt) get().stopSpeaking()
    try {
      const recorder = await startMicRecording()
      set({ mic: recorder, state: transition(get().state, 'listening'), error: null })
    } catch (e) {
      set({
        state: transition(get().state, 'error'),
        error: e instanceof Error ? e.message : 'Sem acesso ao microfone',
      })
    }
  },

  stopSpeaking: () => {
    get().ttsAbort?.abort()
    set({ ttsAbort: null, state: transition(get().state, 'idle') })
  },

  resolveConfirm: async (decision) => {
    const { sessionId, prefs } = get()
    if (!sessionId || get().demoForced || prefs.demoMode) {
      const reply =
        decision === 'confirm'
          ? '[DEMO] Confirmado (simulação — nenhuma acção real).'
          : '[DEMO] Cancelado.'
      set({
        pending: null,
        messages: [...get().messages, { id: uid(), role: 'assistant', text: reply, demo: true }],
        state: transition(get().state, 'idle'),
      })
      return
    }
    try {
      const res = await api.confirm(sessionId, decision)
      set({
        pending: null,
        messages: [...get().messages, { id: uid(), role: 'assistant', text: res.reply }],
        state: transition(get().state, 'idle'),
      })
    } catch (e) {
      set({
        error: e instanceof Error ? e.message : 'Falha na confirmação',
        state: transition(get().state, 'error'),
      })
    }
  },

  openMonitor: () => {
    const path = get().offerMonitorPath
    if (!path) {
      set({ error: 'Nenhum monitor disponivel nesta resposta.' })
      return
    }
    openMonitorPath(path, getAgentApiBase())
  },

  seedDemoConfirm: async () => {
    const { sessionId, prefs } = get()
    if (!sessionId || prefs.demoMode || get().demoForced) {
      set({
        pending: {
          action: 'send_email',
          target: 'demo@example.com',
          summary: 'enviar um email de teste',
          consequences: 'Demo — não envia de verdade.',
        },
        state: transition(get().state, 'awaiting_confirmation'),
        messages: [
          ...get().messages,
          {
            id: uid(),
            role: 'assistant',
            text: '[DEMO] Antes de continuar: vou enviar um email de teste. Confirmas?',
            demo: true,
          },
        ],
      })
      return
    }
    const res = await api.seedDemoConfirmation(sessionId)
    set({
      pending: res.pending_confirmation,
      state: transition(get().state, 'awaiting_confirmation'),
      messages: [...get().messages, { id: uid(), role: 'assistant', text: res.reply }],
    })
  },
}))
