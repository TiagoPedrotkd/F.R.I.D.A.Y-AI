import { useAppStore } from '../state/store'

const ACTIONS = [
  { label: 'Hora', short: '⏱', text: 'Que horas são?' },
  { label: 'News', short: '◈', text: 'Quais as notícias de Portugal?' },
  { label: 'Fin', short: '◎', text: 'Notícias financeiras mundiais' },
  { label: 'Piada', short: '◇', text: 'Conta uma piada' },
  { label: 'OK?', short: '⚠', text: '__demo_confirm__' },
]

export function QuickActions({ orbit = false }: { orbit?: boolean }) {
  const sendText = useAppStore((s) => s.sendText)
  const seedDemoConfirm = useAppStore((s) => s.seedDemoConfirm)

  const run = (text: string) => {
    if (text === '__demo_confirm__') void seedDemoConfirm()
    else void sendText(text)
  }

  if (orbit) {
    return (
      <div className="flex flex-wrap items-center justify-center gap-3" aria-label="Acções rápidas">
        {ACTIONS.map((a) => (
          <button key={a.label} type="button" className="orb-btn" onClick={() => run(a.text)} title={a.label}>
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
        {ACTIONS.map((a) => (
          <button key={a.label} type="button" className="hud-btn w-full text-left" onClick={() => run(a.text)}>
            {a.label}
          </button>
        ))}
      </div>
    </section>
  )
}
