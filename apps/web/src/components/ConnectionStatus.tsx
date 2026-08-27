import { useAppStore } from '../state/store'

export function ConnectionStatus() {
  const backendOk = useAppStore((s) => s.backendOk)
  const llmOk = useAppStore((s) => s.llmOk)
  const demo = useAppStore((s) => s.demoForced || s.prefs.demoMode)

  const Dot = ({ ok, label }: { ok: boolean; label: string }) => (
    <span
      className="inline-flex items-center gap-1.5 font-display text-[10px] tracking-[0.18em] text-[var(--text-muted)]"
      title={label}
    >
      <span
        className={`h-2 w-2 rounded-full ${ok ? 'bg-cyan' : 'bg-danger'}`}
        style={ok ? { boxShadow: '0 0 8px var(--color-cyan)' } : undefined}
        aria-hidden
      />
      <span className="sr-only">{label}: </span>
      {label}
    </span>
  )

  return (
    <div className="flex flex-wrap items-center gap-4" role="status" aria-label="Estado da ligação">
      <Dot ok={backendOk || demo} label="API" />
      <Dot ok={llmOk || demo} label="LM" />
      {demo && (
        <span className="border border-amber/50 bg-amber/15 px-2 py-0.5 font-display text-[10px] font-semibold tracking-[0.2em] text-amber">
          DEMO
        </span>
      )}
    </div>
  )
}
