import { create } from 'zustand'
import type {
  ActivityStep,
  FridayAlert,
  HaEntity,
  PendingConfirmation,
  SourceItem,
} from '../api/client'
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
  groundingScore?: number | null
  confidenceScore?: number | null
  confidenceLevel?: string | null
  hallucinationRisk?: string | null
  feedback?: 'up' | 'down' | null
}

type AppStore = {
  state: FridayState
  sessionId: string | null
  messages: Message[]
  activity: ActivityStep[]
  country: string | null
  sources: SourceItem[]
  pending: PendingConfirmation | null
  alerts: FridayAlert[]
  offerMonitorPath: string | null
  prefs: Prefs
  backendOk: boolean
  llmOk: boolean
  haEnabled: boolean
  haOk: boolean | null
  haUrl: string | null
  demoForced: boolean
  error: string | null
  draft: string
  mic: MicRecorder | null
  ttsAbort: AbortController | null
  settingsOpen: boolean
  casaOpen: boolean
  saudeOpen: boolean
  agendaOpen: boolean
  mailOpen: boolean
  sidebarOpen: boolean
  googleEnabled: boolean
  googleConfigured: boolean
  casaLoading: boolean
  casaError: string | null
  casaLights: HaEntity[]
  casaSwitches: HaEntity[]
  casaEnergy: HaEntity[]
  casaSensors: HaEntity[]

  setDraft: (v: string) => void
  setState: (s: FridayState) => void
  setPrefs: (p: Partial<Prefs>) => void
  setSettingsOpen: (v: boolean) => void
  setCasaOpen: (v: boolean) => void
  setSaudeOpen: (v: boolean) => void
  setAgendaOpen: (v: boolean) => void
  setMailOpen: (v: boolean) => void
  setSidebarOpen: (v: boolean) => void
  connectGoogle: () => Promise<void>
  disconnectGoogle: () => Promise<void>
  dismissAlert: (index: number) => void
  bootstrap: () => Promise<void>
  refreshCasa: () => Promise<void>
  requestCasaAction: (
    entityId: string,
    service: 'turn_on' | 'turn_off' | 'toggle',
  ) => Promise<void>
  sendText: (text?: string) => Promise<void>
  toggleMic: () => Promise<void>
  stopSpeaking: () => void
  resolveConfirm: (decision: 'confirm' | 'cancel') => Promise<void>
  openMonitor: () => void
  seedDemoConfirm: () => Promise<void>
  rateMessage: (messageId: string, rating: 'up' | 'down') => Promise<void>
  regenerateLast: () => Promise<void>
  continueLast: () => Promise<void>
  restoreSession: (sessionId: string) => Promise<void>
  uploadFile: (file: File) => Promise<void>
}

function uid() {
  return Math.random().toString(36).slice(2, 10)
}

function applyPrefsDom(prefs: Prefs) {
  document.documentElement.classList.toggle('high-contrast', prefs.highContrast)
  document.documentElement.classList.toggle('reduce-motion', prefs.reducedMotion)
  document.documentElement.dataset.theme = prefs.theme || 'dark'
  document.documentElement.style.colorScheme = prefs.theme === 'light' ? 'light' : 'dark'
}

export const useAppStore = create<AppStore>((set, get) => ({
  state: 'connecting',
  sessionId: null,
  messages: [],
  activity: [],
  country: null,
  sources: [],
  pending: null,
  alerts: [],
  offerMonitorPath: null,
  prefs: { ...defaultPrefs, ...getJson<Partial<Prefs>>('prefs', {}) },
  backendOk: false,
  llmOk: false,
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
  agendaOpen: false,
  mailOpen: false,
  sidebarOpen: false,
  googleEnabled: false,
  googleConfigured: false,
  casaLoading: false,
  casaError: null,
  casaLights: [],
  casaSwitches: [],
  casaEnergy: [],
  casaSensors: [],

  setDraft: (v) => set({ draft: v }),
  setState: (s) => set((st) => ({ state: transition(st.state, s) })),
  setPrefs: (p) => {
    const prefs = { ...get().prefs, ...p }
    setJson('prefs', prefs)
    applyPrefsDom(prefs)
    set({ prefs })
    // Best-effort sync to server (structured prefs, Etapa 3)
    void api
      .savePrefs({
        language: prefs.language,
        theme: prefs.theme,
        user_address: prefs.userAddress,
        tts_enabled: prefs.ttsEnabled,
        volume: prefs.volume,
        rate: prefs.rate,
        autoplay: prefs.autoplay,
        interrupt: prefs.interrupt,
        auto_open_monitors: prefs.autoOpenMonitors,
        high_contrast: prefs.highContrast,
        reduced_motion: prefs.reducedMotion,
        productivity_patterns: {
          working_hours: prefs.workingHours,
          preferred_meeting_duration: prefs.preferredMeetingDuration,
          do_not_disturb: prefs.doNotDisturb,
        },
        user_profile: {
          goals: prefs.profileGoals,
          habits: prefs.profileHabits,
          preferences: prefs.profilePreferences,
          constraints: prefs.profileConstraints,
          domains_of_interest: prefs.domainsOfInterest
            .split(',')
            .map((s) => s.trim())
            .filter(Boolean),
        },
        integrations_enabled: {
          weather: true,
          health_file: true,
          notion_export: true,
          strava_file: true,
          home_assistant: prefs.homeAssistantEnabled,
        },
      })
      .catch(() => undefined)
  },
  setSettingsOpen: (v) => set({ settingsOpen: v }),
  setCasaOpen: (v) => set({ casaOpen: v }),
  setSaudeOpen: (v) => set({ saudeOpen: v }),
  setAgendaOpen: (v) => set({ agendaOpen: v }),
  setMailOpen: (v) => set({ mailOpen: v }),
  setSidebarOpen: (v) => set({ sidebarOpen: v }),

  connectGoogle: async () => {
    try {
      const { url } = await api.fetchGoogleAuthUrl()
      window.open(url, '_blank', 'noopener,noreferrer')
    } catch (e) {
      set({ error: e instanceof Error ? e.message : 'Falha ao abrir OAuth Google' })
    }
  },

  disconnectGoogle: async () => {
    try {
      await api.disconnectGoogle()
      set({ googleConfigured: get().googleConfigured })
    } catch (e) {
      set({ error: e instanceof Error ? e.message : 'Falha ao desligar Google' })
    }
  },

  dismissAlert: (index) =>
    set({ alerts: get().alerts.filter((_, i) => i !== index) }),

  refreshCasa: async () => {
    if (!get().prefs.homeAssistantEnabled) {
      set({
        casaError: 'Integração Home Assistant desactivada nas definições.',
        casaLights: [],
        casaSwitches: [],
        casaEnergy: [],
        casaSensors: [],
      })
      return
    }
    set({ casaLoading: true, casaError: null })
    try {
      const [st, lights, switches, energy, sensors] = await Promise.all([
        api.fetchHaStatus(),
        api.fetchHaEntities('light'),
        api.fetchHaEntities('switch'),
        api.fetchHaEnergy(),
        api.fetchHaEntities('sensor', 80),
      ])
      const energyIds = new Set((energy.entities || []).map((e) => e.entity_id))
      set({
        haEnabled: true,
        haOk: Boolean(st.ok),
        haUrl: st.url || get().haUrl,
        casaLights: lights.entities || [],
        casaSwitches: switches.entities || [],
        casaEnergy: energy.entities || [],
        casaSensors: (sensors.entities || []).filter((e) => !energyIds.has(e.entity_id)),
        casaLoading: false,
        casaError: null,
      })
    } catch (e) {
      const msg = e instanceof Error ? e.message : 'Falha ao ler Home Assistant'
      set({
        casaLoading: false,
        casaError: msg,
        haOk: false,
      })
    }
  },

  requestCasaAction: async (entityId, service) => {
    const { sessionId, prefs } = get()
    if (!sessionId) {
      set({ error: 'Sem sessão activa.' })
      return
    }
    if (prefs.demoMode || get().demoForced) {
      set({
        pending: {
          action: 'ha_call_service',
          target: entityId,
          summary: `${service} ${entityId}`,
          consequences: 'Demo — não altera dispositivos reais.',
          preview: { entity_id: entityId, service },
        },
        state: transition(get().state, 'awaiting_confirmation'),
      })
      return
    }
    try {
      const res = await api.requestHaAction(sessionId, entityId, service)
      set({
        pending: res.pending_confirmation,
        state: transition(get().state, 'awaiting_confirmation'),
        messages: [...get().messages, { id: uid(), role: 'assistant', text: res.reply }],
      })
    } catch (e) {
      set({
        error: e instanceof Error ? e.message : 'Falha ao pedir acção HA',
        state: transition(get().state, 'error'),
      })
    }
  },

  bootstrap: async () => {
    applyPrefsDom(get().prefs)
    set({ state: transition(get().state, 'connecting'), error: null })
    try {
      const status = await api.fetchStatus()
      const session = await api.createSession()
      let prefs = {
        ...get().prefs,
        autoOpenMonitors: status.auto_open_monitors ?? get().prefs.autoOpenMonitors,
      }
      try {
        const remote = await api.fetchPrefs()
        const rp = remote.prefs || {}
        prefs = {
          ...prefs,
          language: (rp.language as 'pt' | 'en') || prefs.language,
          theme: rp.theme === 'light' || rp.theme === 'dark' ? rp.theme : prefs.theme,
          userAddress:
            typeof rp.user_address === 'string' && rp.user_address
              ? rp.user_address
              : prefs.userAddress,
          ttsEnabled: typeof rp.tts_enabled === 'boolean' ? rp.tts_enabled : prefs.ttsEnabled,
          volume: typeof rp.volume === 'number' ? rp.volume : prefs.volume,
          rate: typeof rp.rate === 'number' ? rp.rate : prefs.rate,
          autoplay: typeof rp.autoplay === 'boolean' ? rp.autoplay : prefs.autoplay,
          interrupt: typeof rp.interrupt === 'boolean' ? rp.interrupt : prefs.interrupt,
          autoOpenMonitors:
            typeof rp.auto_open_monitors === 'boolean'
              ? rp.auto_open_monitors
              : prefs.autoOpenMonitors,
          highContrast:
            typeof rp.high_contrast === 'boolean' ? rp.high_contrast : prefs.highContrast,
          reducedMotion:
            typeof rp.reduced_motion === 'boolean' ? rp.reduced_motion : prefs.reducedMotion,
        }
        const pp = rp.productivity_patterns
        if (pp && typeof pp === 'object') {
          const patterns = pp as Record<string, unknown>
          if (typeof patterns.working_hours === 'string') {
            prefs.workingHours = patterns.working_hours
          }
          if (typeof patterns.preferred_meeting_duration === 'number') {
            prefs.preferredMeetingDuration = patterns.preferred_meeting_duration
          }
          if (typeof patterns.do_not_disturb === 'string') {
            prefs.doNotDisturb = patterns.do_not_disturb
          }
        }
        const up = rp.user_profile
        if (up && typeof up === 'object') {
          const profile = up as Record<string, unknown>
          if (typeof profile.goals === 'string') prefs.profileGoals = profile.goals
          if (typeof profile.habits === 'string') prefs.profileHabits = profile.habits
          if (typeof profile.preferences === 'string') prefs.profilePreferences = profile.preferences
          if (typeof profile.constraints === 'string') prefs.profileConstraints = profile.constraints
          if (Array.isArray(profile.domains_of_interest)) {
            prefs.domainsOfInterest = profile.domains_of_interest.map(String).join(', ')
          }
        }
        const integ = rp.integrations_enabled
        if (integ && typeof integ === 'object') {
          const ie = integ as Record<string, unknown>
          if (typeof ie.home_assistant === 'boolean') {
            prefs.homeAssistantEnabled = ie.home_assistant
          }
        }
        setJson('prefs', prefs)
        applyPrefsDom(prefs)
      } catch {
        /* local prefs remain */
      }
      const demoForced = status.demo || prefs.demoMode
      let alerts: import('../api/client').FridayAlert[] = []
      if (!demoForced) {
        try {
          const ar = await api.fetchAlerts()
          alerts = ar.alerts || []
        } catch {
          /* optional */
        }
      }
      set({
        sessionId: session.id,
        backendOk: true,
        llmOk: status.llm.ok,
        haEnabled: Boolean(status.ha?.enabled),
        haOk: status.ha?.enabled ? (status.ha.ok ?? null) : null,
        haUrl: status.ha?.url ?? null,
        googleEnabled: Boolean(status.google?.enabled),
        googleConfigured: Boolean(status.google?.configured),
        demoForced,
        state: transition(get().state, 'idle'),
        prefs,
        alerts,
      })
      api.subscribeEvents(session.id, (type, raw) => {
        const data = (raw as { data?: Record<string, unknown> })?.data ?? raw
        if (type === 'state' && data && typeof data === 'object' && 'state' in (data as object)) {
          const s = (data as { state: FridayState }).state
          if (s) get().setState(s)
        }
        if (type === 'alerts' && data && typeof data === 'object' && 'alerts' in (data as object)) {
          const list = (data as { alerts: FridayAlert[] }).alerts
          if (Array.isArray(list) && list.length) {
            set({ alerts: list })
          }
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
        const assistantId = uid()
        set({
          messages: [
            ...get().messages,
            { id: assistantId, role: 'assistant', text: '', sources: [] },
          ],
        })
        const res = await api.chatStream(sessionId!, content, (chunk) => {
          set({
            messages: get().messages.map((m) =>
              m.id === assistantId ? { ...m, text: m.text + chunk } : m,
            ),
          })
        })
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
        set({
          messages: get().messages.map((m) =>
            m.id === assistantId
              ? {
                  ...m,
                  text: replyText,
                  sources,
                  groundingScore: res.ui?.grounding_score ?? res.grounding?.score ?? null,
                  confidenceScore:
                    (res.ui as { confidence_score?: number })?.confidence_score ??
                    (res.confidence as { score?: number } | undefined)?.score ??
                    null,
                  confidenceLevel:
                    (res.ui as { confidence_level?: string })?.confidence_level ??
                    (res.confidence as { level?: string } | undefined)?.level ??
                    null,
                  hallucinationRisk:
                    (res.ui as { hallucination_risk?: string })?.hallucination_risk ??
                    (res.confidence as { hallucination_risk?: string } | undefined)
                      ?.hallucination_risk ??
                    null,
                }
              : m,
          ),
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
        return
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
    const { sessionId, prefs, pending: prevPending } = get()
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
      const nextPending =
        (res as { pending_confirmation?: PendingConfirmation | null }).pending_confirmation ?? null
      set({
        pending: nextPending,
        messages: [...get().messages, { id: uid(), role: 'assistant', text: res.reply }],
        state: transition(
          get().state,
          nextPending ? 'awaiting_confirmation' : 'idle',
        ),
      })
      if (
        decision === 'confirm' &&
        !nextPending &&
        prevPending?.action === 'ha_call_service' &&
        get().casaOpen
      ) {
        void get().refreshCasa()
      }
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

  rateMessage: async (messageId, rating) => {
    const { sessionId, messages, demoForced, prefs } = get()
    const msg = messages.find((m) => m.id === messageId)
    if (!msg || msg.role !== 'assistant') return
    set({
      messages: messages.map((m) => (m.id === messageId ? { ...m, feedback: rating } : m)),
    })
    if (!sessionId || demoForced || prefs.demoMode) return
    const userText = [...messages].reverse().find((m) => m.role === 'user')?.text
    try {
      await api.sendFeedback({
        session_id: sessionId,
        message_id: messageId,
        rating,
        reply_text: msg.text,
        user_text: userText,
        grounding_score: msg.groundingScore ?? null,
      })
    } catch {
      /* feedback best-effort */
    }
  },

  regenerateLast: async () => {
    const { sessionId, messages, demoForced, prefs } = get()
    if (!sessionId || demoForced || prefs.demoMode) return
    const lastAssistant = [...messages].reverse().find((m) => m.role === 'assistant' && !m.demo)
    const lastUser = [...messages].reverse().find((m) => m.role === 'user')
    if (!lastAssistant || !lastUser) return
    set({
      messages: messages.filter((m) => m.id !== lastAssistant.id),
      state: transition(get().state, 'thinking'),
    })
    const assistantId = uid()
    set({
      messages: [...get().messages, { id: assistantId, role: 'assistant', text: '', sources: [] }],
    })
    try {
      const res = await api.chatStream(
        sessionId,
        lastUser.text || '.',
        (chunk) => {
          set({
            messages: get().messages.map((m) =>
              m.id === assistantId ? { ...m, text: m.text + chunk } : m,
            ),
          })
        },
        { regenerate: true },
      )
      set({
        messages: get().messages.map((m) =>
          m.id === assistantId
            ? {
                ...m,
                text: res.reply,
                sources: res.ui?.sources ?? [],
                groundingScore: res.ui?.grounding_score ?? null,
                confidenceScore: res.ui?.confidence_score ?? null,
                confidenceLevel: res.ui?.confidence_level ?? null,
                hallucinationRisk: res.ui?.hallucination_risk ?? null,
              }
            : m,
        ),
        sources: res.ui?.sources ?? [],
        state: transition(get().state, 'idle'),
      })
    } catch (e) {
      set({
        error: e instanceof Error ? e.message : 'Falha ao regenerar',
        state: transition(get().state, 'error'),
      })
    }
  },

  continueLast: async () => {
    const { sessionId, demoForced, prefs } = get()
    if (!sessionId || demoForced || prefs.demoMode) return
    await get().sendText('continua')
  },

  restoreSession: async (id) => {
    try {
      const data = await api.getSession(id)
      const messages: Message[] = (data.messages || []).map((m) => ({
        id: uid(),
        role: m.role === 'assistant' || m.role === 'system' ? m.role : 'user',
        text: m.content,
      }))
      set({
        sessionId: data.id,
        messages,
        country: data.last_country ?? null,
        state: transition(get().state, 'idle'),
        error: null,
      })
      api.subscribeEvents(data.id, (type, raw) => {
        const eventData = (raw as { data?: Record<string, unknown> })?.data ?? raw
        if (type === 'state' && eventData && typeof eventData === 'object' && 'state' in (eventData as object)) {
          const s = (eventData as { state: FridayState }).state
          if (s) get().setState(s)
        }
        if (
          type === 'alerts' &&
          eventData &&
          typeof eventData === 'object' &&
          'alerts' in (eventData as object)
        ) {
          const list = (eventData as { alerts: FridayAlert[] }).alerts
          if (Array.isArray(list) && list.length) {
            set({ alerts: list })
          }
        }
      })
    } catch (e) {
      set({ error: e instanceof Error ? e.message : 'Nao foi possivel restaurar a sessao' })
    }
  },

  uploadFile: async (file) => {
    const { sessionId, demoForced, prefs } = get()
    if (!sessionId || demoForced || prefs.demoMode) {
      set({ error: 'Upload indisponivel em modo demo.' })
      return
    }
    try {
      const res = await api.uploadAttachment(sessionId, file)
      const visionHint =
        res.kind === 'image' && res.vision
          ? ' — vision activo na proxima mensagem'
          : ''
      set({
        messages: [
          ...get().messages,
          {
            id: uid(),
            role: 'system',
            text: `Anexo recebido (${res.kind}): ${res.filename}${visionHint}`,
          },
        ],
      })
    } catch (e) {
      set({ error: e instanceof Error ? e.message : 'Falha no upload' })
    }
  },
}))
