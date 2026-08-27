export type FridayState =
  | 'offline'
  | 'connecting'
  | 'idle'
  | 'listening'
  | 'transcribing'
  | 'thinking'
  | 'tool_calling'
  | 'awaiting_confirmation'
  | 'speaking'
  | 'error'

/** Valid transitions — single source of truth. */
const ALLOWED: Record<FridayState, FridayState[]> = {
  offline: ['connecting', 'idle', 'error'],
  connecting: ['idle', 'offline', 'error'],
  idle: [
    'listening',
    'thinking',
    'speaking',
    'awaiting_confirmation',
    'offline',
    'error',
    'connecting',
  ],
  listening: ['transcribing', 'idle', 'error'],
  transcribing: ['thinking', 'idle', 'error'],
  thinking: ['tool_calling', 'speaking', 'idle', 'awaiting_confirmation', 'error'],
  tool_calling: ['thinking', 'speaking', 'idle', 'awaiting_confirmation', 'error'],
  awaiting_confirmation: ['idle', 'thinking', 'error'],
  speaking: ['idle', 'listening', 'error'],
  error: ['idle', 'connecting', 'offline'],
}

export function canTransition(from: FridayState, to: FridayState): boolean {
  if (from === to) return true
  return ALLOWED[from]?.includes(to) ?? false
}

export function transition(from: FridayState, to: FridayState): FridayState {
  if (canTransition(from, to)) return to
  console.warn(`Invalid FRIDAY state transition: ${from} -> ${to}`)
  return from
}

export function stateLabel(state: FridayState, lang: 'pt' | 'en' = 'pt'): string {
  const pt: Record<FridayState, string> = {
    offline: 'Offline',
    connecting: 'A ligar…',
    idle: 'Pronta',
    listening: 'A ouvir…',
    transcribing: 'A transcrever…',
    thinking: 'A pensar…',
    tool_calling: 'A usar ferramentas…',
    awaiting_confirmation: 'A aguardar confirmação…',
    speaking: 'A falar…',
    error: 'Erro',
  }
  const en: Record<FridayState, string> = {
    offline: 'Offline',
    connecting: 'Connecting…',
    idle: 'Ready',
    listening: 'Listening…',
    transcribing: 'Transcribing…',
    thinking: 'Thinking…',
    tool_calling: 'Using tools…',
    awaiting_confirmation: 'Awaiting confirmation…',
    speaking: 'Speaking…',
    error: 'Error',
  }
  return (lang === 'en' ? en : pt)[state]
}
