import type { FridayAlert } from '../api/client'
import { useAppStore } from '../state/store'

function ctaPrompt(a: FridayAlert): string | null {
  if (a.kind === 'imminent_meeting' || a.kind === 'scheduled_reminder') {
    return 'Prepara a reuniao com o que tiveres na agenda e emails recentes.'
  }
  if (a.kind === 'email_overdue') {
    return 'Prepara um rascunho de resposta ao email urgente.'
  }
  return a.cta ? String(a.cta).replace(/\?$/, '.') : null
}

export function AlertsBanner() {
  const alerts = useAppStore((s) => s.alerts)
  const dismissAlert = useAppStore((s) => s.dismissAlert)
  const sendText = useAppStore((s) => s.sendText)
  if (!alerts.length) return null

  return (
    <div className="pointer-events-auto relative z-40 mx-auto w-full max-w-3xl space-y-2 px-3 pt-2 md:px-6">
      {alerts.slice(0, 3).map((a, i) => (
        <div
          key={`${a.kind}-${i}`}
          className="holo holo-frame flex items-start gap-3 border-amber/40 p-3 text-sm"
          role="status"
        >
          <div className="min-w-0 flex-1">
            <p className="hud-label" style={{ color: 'var(--color-amber)' }}>
              FRIDAY sugere · {a.severity}
            </p>
            <p className="mt-1 text-[var(--text-primary)]">{a.message}</p>
            {a.cta ? <p className="mt-1 text-xs text-cyan/80">{a.cta}</p> : null}
          </div>
          <div className="flex shrink-0 flex-col gap-1">
            {ctaPrompt(a) ? (
              <button
                type="button"
                className="hud-btn"
                onClick={() => {
                  const prompt = ctaPrompt(a)
                  dismissAlert(i)
                  if (prompt) void sendText(prompt)
                }}
              >
                Sim
              </button>
            ) : null}
            <button type="button" className="hud-btn" onClick={() => dismissAlert(i)}>
              Ok
            </button>
          </div>
        </div>
      ))}
    </div>
  )
}
