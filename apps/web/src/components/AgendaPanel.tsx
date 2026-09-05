import { useCallback, useEffect, useState } from 'react'
import * as api from '../api/client'

export function AgendaPanel({ onClose }: { onClose: () => void }) {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [events, setEvents] = useState<
    { uid?: string; summary?: string; start?: string; end?: string }[]
  >([])

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await api.fetchAgendaEvents(7)
      setEvents(res.events || [])
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Falha a ler agenda')
      setEvents([])
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void load()
    const id = window.setInterval(() => void load(), 30000)
    return () => window.clearInterval(id)
  }, [load])

  return (
    <div className="fixed inset-0 z-40 flex justify-end bg-black/60" role="presentation">
      <div
        role="dialog"
        aria-modal="true"
        aria-label="Agenda"
        className="hud-panel h-full w-full max-w-md overflow-y-auto border-l border-cyan/30 p-5"
        style={{ clipPath: 'none', borderRadius: 0 }}
      >
        <div className="mb-5 flex items-center justify-between">
          <div>
            <p className="hud-label">Produtividade</p>
            <h2 className="font-display text-lg font-semibold tracking-wide text-cyan">Agenda</h2>
          </div>
          <button type="button" className="hud-btn" onClick={onClose}>
            Fechar
          </button>
        </div>
        <p className="mb-3 text-xs text-[var(--text-muted)]">
          Criar/cancelar eventos: usa o chat (com confirmação).
        </p>
        {error ? <p className="mb-3 text-xs text-amber">{error}</p> : null}
        <button type="button" className="hud-btn mb-4 text-xs" disabled={loading} onClick={() => void load()}>
          {loading ? 'A actualizar…' : 'Actualizar'}
        </button>
        {events.length === 0 && !error ? (
          <p className="text-sm text-[var(--text-muted)]">Sem eventos nos próximos 7 dias.</p>
        ) : (
          <ul>
            {events.map((ev) => (
              <li key={ev.uid || `${ev.start}-${ev.summary}`} className="border-b border-cyan/10 py-2">
                <p className="text-sm text-cyan">{ev.summary || '(sem título)'}</p>
                <p className="text-[10px] text-[var(--text-muted)]">
                  {ev.start || '—'}
                  {ev.end ? ` → ${ev.end}` : ''}
                </p>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  )
}
