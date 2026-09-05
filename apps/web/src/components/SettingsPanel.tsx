import { useEffect, useState } from 'react'
import { useAppStore } from '../state/store'
import type { Prefs } from '../demo/fixtures'
import * as api from '../api/client'

function GoogleConnectBlock() {
  const googleEnabled = useAppStore((s) => s.googleEnabled)
  const googleConfigured = useAppStore((s) => s.googleConfigured)
  const connectGoogle = useAppStore((s) => s.connectGoogle)
  const disconnectGoogle = useAppStore((s) => s.disconnectGoogle)
  const [connected, setConnected] = useState(false)
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    void api
      .fetchGoogleStatus()
      .then((s) => setConnected(Boolean(s.connected)))
      .catch(() => setConnected(false))
  }, [googleEnabled, googleConfigured])

  if (!googleEnabled) {
    return (
      <p className="text-xs text-[var(--text-muted)]">
        Google desactivado (`GOOGLE_ENABLED=false` no .env).
      </p>
    )
  }

  return (
    <div className="space-y-2 border-b border-cyan/10 py-2">
      <p className="text-[var(--text-muted)]">
        Google: {connected ? 'ligado' : googleConfigured ? 'não ligado' : 'sem Client ID'}
      </p>
      <div className="flex gap-2">
        <button
          type="button"
          className="hud-btn text-xs"
          disabled={busy || !googleConfigured}
          onClick={() => {
            setBusy(true)
            void connectGoogle().finally(() => setBusy(false))
          }}
        >
          Conectar Google
        </button>
        <button
          type="button"
          className="hud-btn text-xs"
          disabled={busy || !connected}
          onClick={() => {
            setBusy(true)
            void disconnectGoogle()
              .then(() => setConnected(false))
              .finally(() => setBusy(false))
          }}
        >
          Desligar
        </button>
      </div>
    </div>
  )
}

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

          <h3 className="pt-2 text-sm font-semibold uppercase tracking-wide text-[var(--text-muted)]">
            Perfil pessoal
          </h3>
          {(
            [
              ['profileGoals', 'Objectivos'],
              ['profileHabits', 'Hábitos'],
              ['profilePreferences', 'Preferências'],
              ['profileConstraints', 'Restrições'],
              ['domainsOfInterest', 'Domínios (vírgulas)'],
            ] as const
          ).map(([key, label]) => (
            <label key={key} className="flex flex-col gap-1">
              <span className="text-[var(--text-muted)]">{label}</span>
              <textarea
                className="min-h-[56px] rounded border border-cyan/30 bg-[var(--color-night-950)] px-2 py-1.5 text-cyan"
                value={prefs[key]}
                onChange={(e) => setPrefs({ [key]: e.target.value } as Partial<Prefs>)}
              />
            </label>
          ))}

          <h3 className="pt-2 text-sm font-semibold uppercase tracking-wide text-[var(--text-muted)]">
            Integrações
          </h3>
          <label className="flex items-center gap-2">
            <input
              type="checkbox"
              checked={prefs.homeAssistantEnabled}
              onChange={(e) => setPrefs({ homeAssistantEnabled: e.target.checked })}
            />
            <span className="text-[var(--text-muted)]">
              Home Assistant (consulta; requer HA_ENABLED no .env)
            </span>
          </label>
          <GoogleConnectBlock />

          <h3 className="pt-2 text-sm font-semibold uppercase tracking-wide text-[var(--text-muted)]">
            Agenda e padrões
          </h3>
          <label className="flex flex-col gap-1">
            <span className="text-[var(--text-muted)]">Horário de trabalho</span>
            <input
              className="rounded border border-cyan/30 bg-[var(--color-night-950)] px-2 py-1.5 text-cyan"
              value={prefs.workingHours}
              placeholder="9:00-18:00"
              onChange={(e) => setPrefs({ workingHours: e.target.value })}
            />
          </label>
          <label className="flex flex-col gap-1">
            <span className="text-[var(--text-muted)]">Duração preferida de reunião (min)</span>
            <input
              type="number"
              min={15}
              max={180}
              step={15}
              className="rounded border border-cyan/30 bg-[var(--color-night-950)] px-2 py-1.5 text-cyan"
              value={prefs.preferredMeetingDuration}
              onChange={(e) => setPrefs({ preferredMeetingDuration: Number(e.target.value) })}
            />
          </label>
          <label className="flex flex-col gap-1">
            <span className="text-[var(--text-muted)]">Não incomodar</span>
            <input
              className="rounded border border-cyan/30 bg-[var(--color-night-950)] px-2 py-1.5 text-cyan"
              value={prefs.doNotDisturb}
              placeholder="22:00-8:00"
              onChange={(e) => setPrefs({ doNotDisturb: e.target.value })}
            />
          </label>
        </div>
      </div>
    </div>
  )
}
