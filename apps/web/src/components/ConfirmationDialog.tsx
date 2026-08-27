import { useEffect, useRef } from 'react'
import { useAppStore } from '../state/store'

export function ConfirmationDialog() {
  const pending = useAppStore((s) => s.pending)
  const resolveConfirm = useAppStore((s) => s.resolveConfirm)
  const cancelRef = useRef<HTMLButtonElement>(null)

  useEffect(() => {
    if (pending) cancelRef.current?.focus()
  }, [pending])

  useEffect(() => {
    if (!pending) return
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        e.preventDefault()
        void resolveConfirm('cancel')
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [pending, resolveConfirm])

  if (!pending) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4" role="presentation">
      <div
        role="alertdialog"
        aria-modal="true"
        aria-labelledby="confirm-title"
        aria-describedby="confirm-desc"
        className="hud-panel max-w-md border-amber/50 p-5"
        style={{ boxShadow: '0 0 40px rgba(255,176,32,0.2)' }}
      >
        <p className="hud-label" style={{ color: 'var(--color-amber)' }}>
          Autorização
        </p>
        <h2 id="confirm-title" className="mt-1 font-display text-lg font-semibold tracking-wide text-amber">
          Confirmação necessária
        </h2>
        <p id="confirm-desc" className="mt-3 text-sm text-[var(--text-primary)]">
          Vou <strong>{pending.summary}</strong>.
          <br />
          Alvo: {pending.target}
          {pending.consequences ? (
            <>
              <br />
              Consequências: {pending.consequences}
            </>
          ) : null}
        </p>
        <p className="mt-2 text-xs text-[var(--text-muted)]">
          Enter não confirma esta acção. Usa os botões ou Escape para cancelar.
        </p>
        <div className="mt-4 flex justify-end gap-2">
          <button ref={cancelRef} type="button" className="hud-btn" onClick={() => void resolveConfirm('cancel')}>
            Cancelar
          </button>
          <button
            type="button"
            className="hud-btn"
            style={{ borderColor: 'var(--color-amber)', background: 'rgba(255,176,32,0.85)', color: '#1a1000' }}
            onClick={() => void resolveConfirm('confirm')}
          >
            Confirmar
          </button>
        </div>
      </div>
    </div>
  )
}
