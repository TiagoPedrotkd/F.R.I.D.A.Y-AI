import { stateLabel } from '@/state/machine'
import { useAppStore } from '@/state/store'
import { BUSY_STATES } from './constants'
import { ConversationEmpty } from './ConversationEmpty'
import { MessageBubble } from './MessageBubble'
import { TypingIndicator } from './TypingIndicator'
import { useAutoScroll } from './useAutoScroll'

export function ConversationPanel({ compact }: { compact?: boolean }) {
  const messages = useAppStore((s) => s.messages)
  const state = useAppStore((s) => s.state)
  const lang = useAppStore((s) => s.prefs.language)
  const busy = BUSY_STATES.has(state)
  const endRef = useAutoScroll([messages, state])

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
      <div
        className="hud-scroll flex-1 space-y-2.5 overflow-y-auto px-3 py-3"
        role="log"
        aria-live="polite"
      >
        {messages.length === 0 && !busy && <ConversationEmpty />}
        {messages.map((m) => (
          <MessageBubble key={m.id} message={m} />
        ))}
        {busy && <TypingIndicator label={stateLabel(state, lang)} />}
        <div ref={endRef} />
      </div>
    </section>
  )
}
