import { useCallback, useEffect, useState } from 'react'
import * as api from '../api/client'
import type { HealthDay } from '../api/client'

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="border-b border-cyan/10 py-2">
      <p className="text-[10px] uppercase tracking-wide text-[var(--text-muted)]">{label}</p>
      <p className="font-mono text-sm text-cyan">{value}</p>
    </div>
  )
}

function fmt(v: number | null | undefined, suffix = ''): string {
  if (v == null || Number.isNaN(v)) return '—'
  return `${v}${suffix}`
}

export function SaudePanel({ onClose }: { onClose: () => void }) {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [summary, setSummary] = useState<HealthDay | null>(null)
  const [days, setDays] = useState<HealthDay[]>([])
  const [googleOk, setGoogleOk] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const [st, list] = await Promise.all([api.fetchHealthStatus(), api.fetchHealthDays(10)])
      setGoogleOk(Boolean(st.google_connected))
      setSummary(st.summary || null)
      setDays(list.days || [])
      if (st.error && !st.summary) setError(st.error)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Falha a ler saúde')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void load()
  }, [load])

  const onSync = async () => {
    setLoading(true)
    setError(null)
    try {
      await api.syncHealth(7)
      await load()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Sync falhou')
      setLoading(false)
    }
  }

  return (
    <div className="fixed inset-0 z-40 flex justify-end bg-black/60" role="presentation">
      <div
        role="dialog"
        aria-modal="true"
        aria-label="Saúde"
        className="hud-panel h-full w-full max-w-md overflow-y-auto border-l border-cyan/30 p-5"
        style={{ clipPath: 'none', borderRadius: 0 }}
      >
        <div className="mb-5 flex items-center justify-between">
          <div>
            <p className="hud-label">Integração</p>
            <h2 className="font-display text-lg font-semibold tracking-wide text-cyan">Saúde</h2>
          </div>
          <button type="button" className="hud-btn" onClick={onClose}>
            Fechar
          </button>
        </div>

        <p className="mb-3 text-sm text-[var(--text-muted)]">
          Google: {googleOk ? 'ligado' : 'não ligado'} · cache local
        </p>
        {error ? <p className="mb-3 text-xs text-amber">{error}</p> : null}
        <div className="mb-4 flex gap-2">
          <button type="button" className="hud-btn text-xs" disabled={loading} onClick={() => void load()}>
            Actualizar
          </button>
          <button type="button" className="hud-btn hud-btn-primary text-xs" disabled={loading} onClick={() => void onSync()}>
            Sync Google
          </button>
        </div>

        <section className="mb-5">
          <p className="hud-label mb-1">Hoje</p>
          <Metric label="Passos" value={fmt(summary?.steps)} />
          <Metric label="Sono (h)" value={fmt(summary?.sleep_hours)} />
          <Metric label="FC repouso" value={fmt(summary?.resting_hr)} />
          <Metric label="HRV" value={fmt(summary?.hrv)} />
          <Metric label="Min. activos" value={fmt(summary?.active_minutes)} />
          <p className="mt-2 text-[10px] text-[var(--text-muted)]">
            Fonte: {summary?.source || '—'} · {summary?.synced_at || 'sem sync'}
          </p>
        </section>

        <section>
          <p className="hud-label mb-1">Últimos dias</p>
          {days.length === 0 ? (
            <p className="text-xs text-[var(--text-muted)]">Sem histórico. Corre Sync ou coloca JSON em data/integrations/health.</p>
          ) : (
            <ul className="space-y-1 text-sm">
              {days.map((d) => (
                <li key={d.date} className="flex justify-between border-b border-cyan/10 py-1.5">
                  <span className="text-[var(--text-muted)]">{d.date}</span>
                  <span className="font-mono text-cyan">{fmt(d.steps)} passos</span>
                </li>
              ))}
            </ul>
          )}
        </section>
      </div>
    </div>
  )
}
