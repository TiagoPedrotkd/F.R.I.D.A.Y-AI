import { useAppStore } from '../state/store'

export function VoiceControls() {
  const draft = useAppStore((s) => s.draft)
  const setDraft = useAppStore((s) => s.setDraft)
  const sendText = useAppStore((s) => s.sendText)
  const toggleMic = useAppStore((s) => s.toggleMic)
  const stopSpeaking = useAppStore((s) => s.stopSpeaking)
  const state = useAppStore((s) => s.state)
  const mic = useAppStore((s) => s.mic)
  const busy = ['thinking', 'tool_calling', 'transcribing', 'speaking'].includes(state)

  return (
    <form
      className="holo holo-frame flex flex-col gap-2 p-3 sm:flex-row sm:items-end"
      onSubmit={(e) => {
        e.preventDefault()
        void sendText()
      }}
    >
      <div className="min-w-0 flex-1">
        <label className="holo-label mb-1 block" htmlFor="friday-input">
          Entrada
        </label>
        <textarea
          id="friday-input"
          rows={2}
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault()
              void sendText()
            }
          }}
          placeholder="Fala ou escreve um pedido…"
          className="min-h-[48px] w-full resize-none border border-cyan/30 bg-[#04101c]/80 px-3 py-2 font-body text-sm text-[var(--text-primary)] placeholder:text-cyan/35 focus:border-cyan/70 focus:outline-none"
          style={{
            boxShadow: 'inset 0 0 20px rgba(92,239,255,0.06)',
            colorScheme: 'dark',
          }}
          disabled={state === 'listening'}
        />
      </div>
      <div className="flex gap-2 sm:pb-0.5">
        <button
          type="button"
          onClick={() => void toggleMic()}
          className={`hud-btn ${mic ? 'hud-btn-danger' : ''}`}
          aria-pressed={!!mic}
        >
          {mic ? 'Parar' : 'Mic'}
        </button>
        {state === 'speaking' ? (
          <button
            type="button"
            onClick={stopSpeaking}
            className="hud-btn"
            style={{ borderColor: 'var(--color-amber)', color: 'var(--color-amber)' }}
          >
            Stop
          </button>
        ) : (
          <button type="submit" disabled={!draft.trim() || busy} className="hud-btn hud-btn-primary">
            Enviar
          </button>
        )}
      </div>
    </form>
  )
}
