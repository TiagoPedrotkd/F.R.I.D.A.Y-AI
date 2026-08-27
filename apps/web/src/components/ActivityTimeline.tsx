import { useAppStore } from '../state/store'

export function ActivityTimeline() {
  const activity = useAppStore((s) => s.activity)
  return (
    <section className="holo holo-frame p-3" aria-label="Actividade">
      <p className="holo-label mb-2">Actividade</p>
      {!activity.length ? (
        <p className="text-xs text-[var(--text-muted)]">Sem actividade recente.</p>
      ) : (
        <ol className="space-y-2">
          {activity.map((step, i) => (
            <li key={`${step.label}-${i}`} className="flex gap-2 text-sm">
              <span className="font-display text-[10px] tabular-nums text-cyan/50">
                {String(i + 1).padStart(2, '0')}
              </span>
              <span
                className={`mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full ${
                  step.status === 'failed' ? 'bg-danger' : 'bg-cyan'
                }`}
                style={{ boxShadow: step.status === 'failed' ? undefined : '0 0 8px var(--color-cyan)' }}
                aria-hidden
              />
              <span>{step.label}</span>
            </li>
          ))}
        </ol>
      )}
    </section>
  )
}
