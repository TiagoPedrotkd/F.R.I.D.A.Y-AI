import type { AppStore } from './types'
import type { FridayState } from './machine'

const BUSY: ReadonlySet<FridayState> = new Set([
  'thinking',
  'tool_calling',
  'transcribing',
  'speaking',
  'listening',
])

export const selectBusy = (s: AppStore): boolean => BUSY.has(s.state)

export const selectDemo = (s: AppStore): boolean => s.demoForced || s.prefs.demoMode

export const selectIsListening = (s: AppStore): boolean => s.state === 'listening'

export const selectIsAwaitingConfirm = (s: AppStore): boolean => s.state === 'awaiting_confirmation'

export const selectMessageCount = (s: AppStore): number => s.messages.length

export const selectCoreLoad = (s: AppStore): number => {
  if (s.state === 'error') return 18
  if (s.state === 'connecting') return 40
  if (s.state === 'idle') return 64
  return 84
}

export const selectAnyPanelOpen = (s: AppStore): boolean =>
  s.settingsOpen || s.casaOpen || s.saudeOpen || s.financasOpen || s.agendaOpen || s.mailOpen
