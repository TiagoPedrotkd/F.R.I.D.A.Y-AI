import { useEffect, useRef } from 'react'
import { stateLabel } from '../state/machine'
import { useAppStore } from '../state/store'
import { MessageBubble } from './MessageBubble'

const BUSY_STATES = new Set(['thinking', 'tool_calling', 'transcribing', 'speaking', 'listening'])

export function ConversationPanel({ compact }: { compact?: boolean }) {
  const messages = useAppStore((s) => s.messages)
  const state = useAppStore((s) => s.state)
  const lang = useAppStore((s) => s.prefs.language)
  const endRef = useRef<HTMLDivElement>(null)
  const busy = BUSY_STATES.has(state)

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, state])

  return (
    <section
      className={`holo holo-frame flex flex-col overflow-hidden ${
        compact ? 'h-[min(32vh,260px)] md:h-[min(34vh,300px)]' : 'h-[min(36vh,300px)]'
      }`}
      aria-label="Conversa"
    >
      <div className="flex items-center justify-between border-b border-cyan/15 px-4 py-1.5">
        <p className="holo-label">Comms</p>
        <div className="flex items-center gap-3">
          {busy && (
            <span className="hidden font-display text-[10px] tracking-[0.22em] text-cyan/70 sm:inline">
              {stateLabel(state, lang)}
            </span>
          )}
          <span className="font-display text-[10px] tracking-[0.3em] text-cyan/50">
            {String(messages.length).padStart(2, '0')}
          </span>
        </div>
      </div>
      <div className="hud-scroll flex-1 space-y-2.5 overflow-y-auto px-3 py-3" role="log" aria-live="polite">
        {messages.length === 0 && !busy && (
          <div className="flex h-full min-h-[88px] flex-col items-center justify-center gap-1.5 text-center">
            <p className="font-display text-sm tracking-[0.2em] text-cyan/85">Aguardando instruções…</p>
            <p className="max-w-xs text-xs leading-relaxed text-[var(--text-muted)]">
              Fala ou escreve. Hora, notícias, pesquisa e mais.
            </p>
            <p className="mt-1 font-display text-[10px] tracking-[0.18em] text-cyan/40">
              Enter envia · Shift+Enter nova linha
            </p>
          </div>
        )}
        {messages.map((m) => (
          <MessageBubble key={m.id} message={m} />
        ))}
        {busy && (
          <div
            className="mr-auto flex max-w-[90%] items-center gap-3 border border-cyan/25 bg-cyan/5 px-3.5 py-2.5"
            style={{
              clipPath: 'polygon(0 0, calc(100% - 8px) 0, 100% 8px, 100% 100%, 8px 100%, 0 calc(100% - 8px))',
            }}
            aria-label={stateLabel(state, lang)}
          >
            <span className="hud-typing" aria-hidden>
              <span />
              <span />
              <span />
            </span>
            <span className="font-display text-[11px] uppercase tracking-[0.28em] text-cyan/80">
              {stateLabel(state, lang)}
            </span>
          </div>
        )}
        <div ref={endRef} />
      </div>
    </section>
  )
}
