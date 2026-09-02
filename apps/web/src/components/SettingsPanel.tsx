import { useAppStore } from '../state/store'
import type { Prefs } from '../demo/fixtures'

export function SettingsPanel({ onClose }: { onClose: () => void }) {
  const prefs = useAppStore((s) => s.prefs)
  const setPrefs = useAppStore((s) => s.setPrefs)

  const toggle = (key: keyof Prefs) => {
    const v = prefs[key]
    if (typeof v === 'boolean') setPrefs({ [key]: !v } as Partial<Prefs>)
  }

  return (
    <div className="fixed inset-0 z-40 flex justify-end bg-black/60" role="presentation">
      <div
        role="dialog"
        aria-modal="true"
        aria-label="Definições"
        className="hud-panel h-full w-full max-w-sm overflow-y-auto border-l border-cyan/30 p-5"
        style={{ clipPath: 'none', borderRadius: 0 }}
      >
        <div className="mb-5 flex items-center justify-between">
          <div>
            <p className="hud-label">Sistema</p>
            <h2 className="font-display text-lg font-semibold tracking-wide text-cyan">Configuração</h2>
          </div>
          <button type="button" className="hud-btn" onClick={onClose}>
            Fechar
          </button>
        </div>
        <div className="space-y-4 text-sm">
          <label className="flex items-center justify-between gap-3">
            <span className="text-[var(--text-muted)]">Tema</span>
            <select
              className="border border-cyan/30 bg-[var(--color-night-950)] px-2 py-1 text-cyan"
              value={prefs.theme}
              onChange={(e) => setPrefs({ theme: e.target.value as 'dark' | 'light' })}
            >
              <option value="dark">Escuro (HUD)</option>
              <option value="light">Claro</option>
            </select>
          </label>
          <label className="flex flex-col gap-2">
            <span className="text-[var(--text-muted)]">Tratamento formal</span>
            <input
              className="border border-cyan/30 bg-[var(--color-night-950)] px-2 py-1 text-cyan"
              value={prefs.userAddress}
              onChange={(e) => setPrefs({ userAddress: e.target.value })}
              placeholder="Senhor"
            />
          </label>
          <label className="flex items-center justify-between gap-3">
            <span className="text-[var(--text-muted)]">Idioma UI</span>
            <select
              className="border border-cyan/30 bg-[var(--color-night-950)] px-2 py-1 text-cyan"
              value={prefs.language}
              onChange={(e) => setPrefs({ language: e.target.value as 'pt' | 'en' })}
            >
              <option value="pt">Português</option>
              <option value="en">English</option>
            </select>
          </label>
          {(
            [
              ['ttsEnabled', 'TTS activo'],
              ['autoplay', 'Reproduzir resposta'],
              ['interrupt', 'Interromper fala'],
              ['autoOpenMonitors', 'Abrir monitores automaticamente'],
              ['highContrast', 'Alto contraste'],
              ['reducedMotion', 'Reduzir movimento'],
              ['demoMode', 'Forçar modo demo'],
            ] as const
          ).map(([key, label]) => (
            <label key={key} className="flex items-center justify-between gap-3 border-b border-cyan/10 py-2">
              <span>{label}</span>
              <input type="checkbox" checked={prefs[key]} onChange={() => toggle(key)} />
            </label>
          ))}
          <label className="flex flex-col gap-2">
            <span className="text-[var(--text-muted)]">Volume TTS ({Math.round(prefs.volume * 100)}%)</span>
            <input
              type="range"
              min={0}
              max={1}
              step={0.05}
              value={prefs.volume}
              onChange={(e) => setPrefs({ volume: Number(e.target.value) })}
            />
          </label>
          <label className="flex flex-col gap-2">
            <span className="text-[var(--text-muted)]">
              Velocidade TTS ({prefs.rate.toFixed(2)}×)
            </span>
            <input
              type="range"
              min={0.75}
              max={1.35}
              step={0.05}
              value={prefs.rate}
              onChange={(e) => setPrefs({ rate: Number(e.target.value) })}
            />
          </label>
        </div>
      </div>
    </div>
  )
}
