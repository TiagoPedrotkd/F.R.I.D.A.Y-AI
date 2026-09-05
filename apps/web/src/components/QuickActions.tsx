import { useAppStore } from '../state/store'

const ACTIONS = [
  { label: 'Hora', short: '◷', text: 'Que horas são?' },
  { label: 'News', short: '◈', text: 'Quais as notícias de Portugal?' },
  { label: 'Saúde', short: '♥', text: '__open_saude__' },
  { label: 'Agenda', short: '▣', text: '__open_agenda__' },
  { label: 'Casa', short: '⌂', text: '__open_casa__' },
  { label: 'Piada', short: '◇', text: 'Conta uma piada' },
  { label: 'OK?', short: '⚠', text: '__demo_confirm__' },
]

export function QuickActions({ orbit = false }: { orbit?: boolean }) {
  const sendText = useAppStore((s) => s.sendText)
  const seedDemoConfirm = useAppStore((s) => s.seedDemoConfirm)
  const setCasaOpen = useAppStore((s) => s.setCasaOpen)
  const setSaudeOpen = useAppStore((s) => s.setSaudeOpen)
  const setAgendaOpen = useAppStore((s) => s.setAgendaOpen)
  const homeAssistantEnabled = useAppStore((s) => s.prefs.homeAssistantEnabled)
  const state = useAppStore((s) => s.state)
  const disabled = ['listening', 'thinking', 'tool_calling', 'transcribing'].includes(state)

  const actions = ACTIONS.filter(
    (a) => a.text !== '__open_casa__' || homeAssistantEnabled,
  )

  const run = (text: string) => {
    if (disabled) return
    if (text === '__demo_confirm__') void seedDemoConfirm()
    else if (text === '__open_casa__') setCasaOpen(true)
    else if (text === '__open_saude__') setSaudeOpen(true)
    else if (text === '__open_agenda__') setAgendaOpen(true)
    else void sendText(text)
  }

  if (orbit) {
    return (
      <div className="flex flex-wrap items-center justify-center gap-2.5 sm:gap-3" aria-label="Acções rápidas">
        {actions.map((a) => (
          <button
            key={a.label}
            type="button"
            className="orb-btn"
            onClick={() => run(a.text)}
            title={a.label}
            disabled={disabled}
          >
            <span className="text-sm leading-none opacity-90">{a.short}</span>
            <span>{a.label}</span>
          </button>
        ))}
      </div>
    )
  }

  return (
    <section aria-label="Acções rápidas">
      <p className="holo-label mb-2">Atalhos</p>
      <div className="flex flex-col gap-1.5">
        {actions.map((a) => (
          <button
            key={a.label}
            type="button"
            className="hud-btn w-full text-left"
            onClick={() => run(a.text)}
            disabled={disabled}
          >
            {a.label}
          </button>
        ))}
      </div>
    </section>
  )
}
