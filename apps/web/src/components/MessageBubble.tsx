import type { Message } from '../state/store'
import { useAppStore } from '../state/store'

export function MessageBubble({ message }: { message: Message }) {
  const rateMessage = useAppStore((s) => s.rateMessage)
  const regenerateLast = useAppStore((s) => s.regenerateLast)
  const continueLast = useAppStore((s) => s.continueLast)
  const messages = useAppStore((s) => s.messages)
  const isUser = message.role === 'user'
  const isSystem = message.role === 'system'
  const isLastAssistant =
    !isUser &&
    !isSystem &&
    [...messages].reverse().find((m) => m.role === 'assistant')?.id === message.id

  return (
    <article
      className={`max-w-[94%] px-3.5 py-2.5 text-sm leading-relaxed ${
        isUser
          ? 'ml-auto border border-electric/45 bg-electric/15'
          : isSystem
            ? 'mx-auto border border-amber/40 bg-amber/10 text-amber'
            : 'mr-auto border border-cyan/30 bg-cyan/5'
      }`}
      style={{
        clipPath: isUser
          ? 'polygon(8px 0, 100% 0, 100% calc(100% - 8px), calc(100% - 8px) 100%, 0 100%, 0 8px)'
          : 'polygon(0 0, calc(100% - 8px) 0, 100% 8px, 100% 100%, 8px 100%, 0 calc(100% - 8px))',
        boxShadow: isSystem
          ? undefined
          : isUser
            ? '0 0 18px rgba(74,163,255,0.12)'
            : '0 0 16px rgba(61,227,255,0.08)',
      }}
      data-role={message.role}
      data-demo={message.demo ? 'true' : undefined}
    >
      <div className="mb-1 flex items-center justify-between gap-2">
        {isUser ? (
          <span className="font-display text-[9px] tracking-[0.25em] text-electric/80">VOCÊ</span>
        ) : isSystem ? (
          <span className="font-display text-[9px] tracking-[0.25em] text-amber/90">SISTEMA</span>
        ) : (
          <span className="font-display text-[9px] tracking-[0.25em] text-cyan/70">F.R.I.D.A.Y.</span>
        )}
        {message.demo && (
          <span className="font-display text-[9px] font-semibold uppercase tracking-[0.2em] text-amber">
            Demo
          </span>
        )}
      </div>
      <p className="whitespace-pre-wrap text-[var(--text-primary)]">{message.text}</p>
      {!isUser && !isSystem && message.text && (
        <div className="mt-2 flex flex-wrap items-center gap-2">
          {typeof message.groundingScore === 'number' && (
            <span className="font-display text-[9px] tracking-[0.15em] text-cyan/60">
              GROUND {message.groundingScore.toFixed(2)}
            </span>
          )}
          {typeof message.confidenceScore === 'number' && (
            <span className="font-display text-[9px] tracking-[0.15em] text-electric/70">
              CONF {message.confidenceScore.toFixed(2)}
              {message.confidenceLevel ? `/${message.confidenceLevel}` : ''}
            </span>
          )}
          {message.hallucinationRisk && message.hallucinationRisk !== 'low' && (
            <span className="font-display text-[9px] tracking-[0.15em] text-amber">
              RISK {message.hallucinationRisk}
            </span>
          )}
          <button
            type="button"
            className={`font-display text-[10px] tracking-wider ${
              message.feedback === 'up' ? 'text-cyan' : 'text-[var(--text-muted)]'
            }`}
            aria-label="Útil"
            onClick={() => rateMessage(message.id, 'up')}
          >
            +1
          </button>
          <button
            type="button"
            className={`font-display text-[10px] tracking-wider ${
              message.feedback === 'down' ? 'text-amber' : 'text-[var(--text-muted)]'
            }`}
            aria-label="Pouco útil"
            onClick={() => rateMessage(message.id, 'down')}
          >
            -1
          </button>
          {isLastAssistant && (
            <>
              <button
                type="button"
                className="font-display text-[10px] tracking-wider text-[var(--text-muted)] hover:text-cyan"
                onClick={() => void regenerateLast()}
              >
                Regenerar
              </button>
              <button
                type="button"
                className="font-display text-[10px] tracking-wider text-[var(--text-muted)] hover:text-cyan"
                onClick={() => void continueLast()}
              >
                Continuar
              </button>
            </>
          )}
        </div>
      )}
    </article>
  )
}
