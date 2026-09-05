import { useCallback, useEffect, useState } from 'react'
import * as api from '../api/client'

export function MailPanel({ onClose }: { onClose: () => void }) {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [messages, setMessages] = useState<
    { id: string; subject?: string; from?: string; date?: string }[]
  >([])
  const [body, setBody] = useState<string | null>(null)
  const [selected, setSelected] = useState<string | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await api.fetchMailMessages(20)
      setMessages(res.messages || [])
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Falha a ler mail')
      setMessages([])
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void load()
  }, [load])

  const openMsg = async (id: string) => {
    setSelected(id)
    setBody(null)
    try {
      const msg = await api.fetchMailMessage(id)
      setBody(msg.body || '(vazio)')
    } catch (e) {
      setBody(e instanceof Error ? e.message : 'Erro ao ler')
    }
  }

  return (
    <div className="fixed inset-0 z-40 flex justify-end bg-black/60" role="presentation">
      <div
        role="dialog"
        aria-modal="true"
        aria-label="Mail"
        className="hud-panel h-full w-full max-w-md overflow-y-auto border-l border-cyan/30 p-5"
        style={{ clipPath: 'none', borderRadius: 0 }}
      >
        <div className="mb-5 flex items-center justify-between">
          <div>
            <p className="hud-label">Produtividade</p>
            <h2 className="font-display text-lg font-semibold tracking-wide text-cyan">Mail</h2>
          </div>
          <button type="button" className="hud-btn" onClick={onClose}>
            Fechar
          </button>
        </div>
        <p className="mb-3 text-xs text-[var(--text-muted)]">Enviar emails: usa o chat (com confirmação).</p>
        {error ? <p className="mb-3 text-xs text-amber">{error}</p> : null}
        <button type="button" className="hud-btn mb-4 text-xs" disabled={loading} onClick={() => void load()}>
          {loading ? 'A actualizar…' : 'Actualizar'}
        </button>
        <ul className="mb-4">
          {messages.map((m) => (
            <li key={m.id}>
              <button
                type="button"
                className="w-full border-b border-cyan/10 py-2 text-left"
                onClick={() => void openMsg(m.id)}
              >
                <p className="truncate text-sm text-cyan">{m.subject || '(sem assunto)'}</p>
                <p className="truncate text-[10px] text-[var(--text-muted)]">
                  {m.from} · {m.date}
                </p>
              </button>
            </li>
          ))}
        </ul>
        {selected && body != null ? (
          <section>
            <p className="hud-label mb-1">Corpo</p>
            <pre className="whitespace-pre-wrap text-xs text-[var(--text-primary)] opacity-90">{body}</pre>
          </section>
        ) : null}
      </div>
    </div>
  )
}
