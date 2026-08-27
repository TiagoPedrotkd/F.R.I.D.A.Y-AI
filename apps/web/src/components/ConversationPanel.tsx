import { useEffect, useRef } from 'react'
import { useAppStore } from '../state/store'
import { MessageBubble } from './MessageBubble'

export function ConversationPanel({ compact }: { compact?: boolean }) {
  const messages = useAppStore((s) => s.messages)
  const endRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  return (
    <section
      className={`holo holo-frame flex flex-col overflow-hidden ${
        compact ? 'h-[min(28vh,220px)]' : 'h-[min(32vh,260px)]'
      }`}
      aria-label="Conversa"
    >
      <div className="flex items-center justify-between border-b border-cyan/15 px-4 py-1.5">
        <p className="holo-label">Comms</p>
        <span className="font-display text-[10px] tracking-[0.3em] text-cyan/50">
          {String(messages.length).padStart(2, '0')}
        </span>
      </div>
      <div className="hud-scroll flex-1 space-y-2.5 overflow-y-auto px-3 py-3" role="log" aria-live="polite">
        {messages.length === 0 && (
          <div className="flex h-full min-h-[80px] flex-col items-center justify-center gap-1 text-center">
            <p className="font-display text-sm tracking-[0.2em] text-cyan/80">Aguardando instruções…</p>
            <p className="max-w-xs text-xs text-[var(--text-muted)]">
              Fala ou escreve. Hora, notícias, pesquisa e mais.
            </p>
          </div>
        )}
        {messages.map((m) => (
          <MessageBubble key={m.id} message={m} />
        ))}
        <div ref={endRef} />
      </div>
    </section>
  )
}
