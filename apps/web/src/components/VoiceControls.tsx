import { useRef } from 'react'
import { useAppStore } from '../state/store'

export function VoiceControls() {
  const draft = useAppStore((s) => s.draft)
  const setDraft = useAppStore((s) => s.setDraft)
  const sendText = useAppStore((s) => s.sendText)
  const toggleMic = useAppStore((s) => s.toggleMic)
  const stopSpeaking = useAppStore((s) => s.stopSpeaking)
  const uploadFile = useAppStore((s) => s.uploadFile)
  const state = useAppStore((s) => s.state)
  const mic = useAppStore((s) => s.mic)
  const fileRef = useRef<HTMLInputElement>(null)
  const busy = ['thinking', 'tool_calling', 'transcribing', 'speaking'].includes(state)
  const listening = state === 'listening' || !!mic

  return (
    <form
      className="holo holo-frame flex flex-col gap-2 p-3 sm:flex-row sm:items-end"
      onSubmit={(e) => {
        e.preventDefault()
        void sendText()
      }}
    >
      <div className="min-w-0 flex-1">
        <div className="mb-1 flex items-center justify-between gap-2">
          <label className="holo-label block" htmlFor="friday-input">
            Entrada
          </label>
          {listening && (
            <span className="font-display text-[10px] tracking-[0.22em] text-danger hud-pulse">
              REC
            </span>
          )}
        </div>
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
            if (e.key === 'Escape' && state === 'speaking') {
              e.preventDefault()
              stopSpeaking()
            }
          }}
          placeholder={listening ? 'A ouvir…' : 'Fala, escreve ou anexa um ficheiro…'}
          className="min-h-[52px] w-full resize-none border border-cyan/30 bg-[var(--color-night-950)]/80 px-3 py-2.5 font-body text-sm text-[var(--text-primary)] placeholder:text-cyan/35 focus:border-cyan/70 focus:outline-none"
          style={{
            boxShadow: listening
              ? 'inset 0 0 24px rgba(255,77,106,0.12)'
              : 'inset 0 0 20px rgba(92,239,255,0.06)',
            borderColor: listening ? 'rgba(255,77,106,0.45)' : undefined,
          }}
          disabled={state === 'listening'}
          aria-describedby="friday-input-hint"
          autoComplete="off"
        />
        <p id="friday-input-hint" className="sr-only">
          Enter envia. Shift+Enter nova linha. Escape interrompe a fala.
        </p>
      </div>
      <div className="flex gap-2 sm:pb-0.5">
        <input
          ref={fileRef}
          type="file"
          className="hidden"
          accept=".txt,.md,.csv,.json,.py,.pdf,image/*"
          onChange={(e) => {
            const f = e.target.files?.[0]
            if (f) void uploadFile(f)
            e.target.value = ''
          }}
        />
        <button
          type="button"
          className="hud-btn min-w-[4.5rem]"
          onClick={() => fileRef.current?.click()}
          disabled={busy || listening}
          aria-label="Anexar ficheiro"
        >
          Anexo
        </button>
        <button
          type="button"
          onClick={() => void toggleMic()}
          className={`hud-btn min-w-[4.5rem] ${listening ? 'hud-btn-mic-live' : ''}`}
          aria-pressed={listening}
          aria-label={listening ? 'Parar microfone' : 'Iniciar microfone'}
        >
          {listening ? 'Parar' : 'Mic'}
        </button>
        {state === 'speaking' ? (
          <button
            type="button"
            onClick={stopSpeaking}
            className="hud-btn min-w-[4.5rem]"
            style={{ borderColor: 'var(--color-amber)', color: 'var(--color-amber)' }}
          >
            Stop
          </button>
        ) : (
          <button
            type="submit"
            disabled={!draft.trim() || busy || listening}
            className="hud-btn hud-btn-primary min-w-[4.5rem]"
          >
            Enviar
          </button>
        )}
      </div>
    </form>
  )
}
