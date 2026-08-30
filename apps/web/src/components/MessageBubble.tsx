import type { Message } from '../state/store'

export function MessageBubble({ message }: { message: Message }) {
  const isUser = message.role === 'user'
  const isSystem = message.role === 'system'
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
    </article>
  )
}
