import type {
  ActivityStep,
  FridayAlert,
  HaEntity,
  PendingConfirmation,
  SourceItem,
} from '@/api/client'
import type { Prefs } from '@/demo/fixtures'
import type { MicRecorder } from '@/platform/audio'
import type { FridayState } from './machine'

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

export type UiSliceState = {
  error: string | null
  draft: string
  settingsOpen: boolean
  casaOpen: boolean
  saudeOpen: boolean
  financasOpen: boolean
  agendaOpen: boolean
  mailOpen: boolean
  sidebarOpen: boolean
}

export type UiSliceActions = {
  setDraft: (v: string) => void
  setSettingsOpen: (v: boolean) => void
  setCasaOpen: (v: boolean) => void
  setSaudeOpen: (v: boolean) => void
  setFinancasOpen: (v: boolean) => void
  setAgendaOpen: (v: boolean) => void
  setMailOpen: (v: boolean) => void
  setSidebarOpen: (v: boolean) => void
  clearError: () => void
}

export type PrefsSliceState = {
  prefs: Prefs
}

export type PrefsSliceActions = {
  setPrefs: (p: Partial<Prefs>) => void
}

export type CasaSliceState = {
  casaLoading: boolean
  casaError: string | null
  casaLights: HaEntity[]
  casaSwitches: HaEntity[]
  casaEnergy: HaEntity[]
  casaSensors: HaEntity[]
}

export type CasaSliceActions = {
  refreshCasa: () => Promise<void>
  requestCasaAction: (entityId: string, service: 'turn_on' | 'turn_off' | 'toggle') => Promise<void>
}

export type SessionSliceState = {
  state: FridayState
  sessionId: string | null
  messages: Message[]
  activity: ActivityStep[]
  country: string | null
  sources: SourceItem[]
  pending: PendingConfirmation | null
  alerts: FridayAlert[]
  offerMonitorPath: string | null
  backendOk: boolean
  llmOk: boolean
  haEnabled: boolean
  haOk: boolean | null
  haUrl: string | null
  demoForced: boolean
  mic: MicRecorder | null
  ttsAbort: AbortController | null
  googleEnabled: boolean
  googleConfigured: boolean
  financeEnabled: boolean
  financeConfigured: boolean
}

export type SessionSliceActions = {
  setState: (s: FridayState) => void
  connectGoogle: () => Promise<void>
  disconnectGoogle: () => Promise<void>
  dismissAlert: (index: number) => void
  bootstrap: () => Promise<void>
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

export type AppStore = UiSliceState &
  UiSliceActions &
  PrefsSliceState &
  PrefsSliceActions &
  CasaSliceState &
  CasaSliceActions &
  SessionSliceState &
  SessionSliceActions
