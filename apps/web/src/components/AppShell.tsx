import { useEffect } from 'react'
import { stateLabel } from '../state/machine'
import { useAppStore } from '../state/store'
import { AgendaPanel } from './AgendaPanel'
import { ActivityTimeline } from './ActivityTimeline'
import { AlertsBanner } from './AlertsBanner'
import { CasaPanel } from './CasaPanel'
import { ConfirmationDialog } from './ConfirmationDialog'
import { ConnectionStatus } from './ConnectionStatus'
import { ConversationPanel } from './ConversationPanel'
import { CountryContextChip } from './CountryContextChip'
import { DemoBanner } from './DemoBanner'
import { ErrorNotice } from './ErrorNotice'
import { FridayCore } from './FridayCore'
import { HudDateGauge, HudRingMeter } from './HudWidgets'
import { MailPanel } from './MailPanel'
import { QuickActions } from './QuickActions'
import { SaudePanel } from './SaudePanel'
import { SessionList } from './SessionList'
import { SettingsPanel } from './SettingsPanel'
import { SourceCard } from './SourceCard'
import { VoiceControls } from './VoiceControls'

/** Thin holographic wires behind the stage */
function StageWires() {
  return (
    <svg className="pointer-events-none absolute inset-0 z-0 hidden h-full w-full lg:block" aria-hidden>
      <defs>
        <linearGradient id="wireGrad" x1="0" y1="0" x2="1" y2="0">
          <stop offset="0%" stopColor="#5cefff" stopOpacity="0" />
          <stop offset="40%" stopColor="#5cefff" stopOpacity="0.55" />
          <stop offset="100%" stopColor="#5cefff" stopOpacity="0" />
        </linearGradient>
      </defs>
      <path
        d="M 12% 22% L 28% 22% L 38% 38%"
        fill="none"
        stroke="url(#wireGrad)"
        strokeWidth="1"
        strokeDasharray="4 6"
      />
      <path
        d="M 88% 20% L 72% 20% L 62% 36%"
        fill="none"
        stroke="url(#wireGrad)"
        strokeWidth="1"
        strokeDasharray="4 6"
      />
      <path
        d="M 50% 8% L 50% 18%"
        fill="none"
        stroke="rgba(92,239,255,0.35)"
        strokeWidth="1"
      />
    </svg>
  )
}

export function AppShell() {
  const bootstrap = useAppStore((s) => s.bootstrap)
  const settingsOpen = useAppStore((s) => s.settingsOpen)
  const setSettingsOpen = useAppStore((s) => s.setSettingsOpen)
  const casaOpen = useAppStore((s) => s.casaOpen)
  const setCasaOpen = useAppStore((s) => s.setCasaOpen)
  const saudeOpen = useAppStore((s) => s.saudeOpen)
  const setSaudeOpen = useAppStore((s) => s.setSaudeOpen)
  const agendaOpen = useAppStore((s) => s.agendaOpen)
  const setAgendaOpen = useAppStore((s) => s.setAgendaOpen)
  const mailOpen = useAppStore((s) => s.mailOpen)
  const setMailOpen = useAppStore((s) => s.setMailOpen)
  const sidebarOpen = useAppStore((s) => s.sidebarOpen)
  const setSidebarOpen = useAppStore((s) => s.setSidebarOpen)
  const sources = useAppStore((s) => s.sources)
  const country = useAppStore((s) => s.country)
  const offerMonitor = useAppStore((s) => s.offerMonitorPath)
  const openMonitor = useAppStore((s) => s.openMonitor)
  const prefs = useAppStore((s) => s.prefs)
  const demo = useAppStore((s) => s.demoForced || s.prefs.demoMode)
  const backendOk = useAppStore((s) => s.backendOk)
  const llmOk = useAppStore((s) => s.llmOk)
  const haEnabled = useAppStore((s) => s.haEnabled)
  const state = useAppStore((s) => s.state)
  const lang = prefs.language
  const locale = prefs.language === 'en' ? 'en-GB' : 'pt-PT'
  const coreLoad =
    state === 'error' ? 18 : state === 'connecting' ? 40 : state === 'idle' ? 64 : 84
  const busy = ['thinking', 'tool_calling', 'transcribing', 'listening', 'speaking'].includes(state)
  const alert = state === 'awaiting_confirmation'
  const err = state === 'error'

  useEffect(() => {
    void bootstrap()
  }, [bootstrap])

  return (
    <div
      className={`hud-viewport ${prefs.reducedMotion ? 'reduce-motion' : ''} ${
        prefs.highContrast ? 'high-contrast' : ''
      }`}
    >
      <div className="hud-stage">
        <div className="pointer-events-none absolute inset-4 z-30 max-md:inset-2" aria-hidden>
          <span
            className="absolute left-0 top-0 h-6 w-6 border-l-2 border-t-2 border-cyan/70"
            style={{ filter: 'drop-shadow(0 0 6px #5cefff)' }}
          />
          <span
            className="absolute right-0 top-0 h-6 w-6 border-r-2 border-t-2 border-cyan/70"
            style={{ filter: 'drop-shadow(0 0 6px #5cefff)' }}
          />
          <span
            className="absolute bottom-0 left-0 h-6 w-6 border-b-2 border-l-2 border-cyan/70"
            style={{ filter: 'drop-shadow(0 0 6px #5cefff)' }}
          />
          <span
            className="absolute bottom-0 right-0 h-6 w-6 border-b-2 border-r-2 border-cyan/70"
            style={{ filter: 'drop-shadow(0 0 6px #5cefff)' }}
          />
        </div>

        {demo && <DemoBanner />}
        <AlertsBanner />

        <header className="relative z-20 flex items-center gap-3 px-5 py-3 md:px-8">
          <div className="min-w-0 flex-1">
            <p className="holo-label">Friday OS</p>
            <h1
              className="font-display text-2xl font-bold tracking-[0.35em] text-cyan md:text-3xl"
              style={{ textShadow: '0 0 22px rgba(92,239,255,0.75)' }}
            >
              F.R.I.D.A.Y.
            </h1>
          </div>
          <div
            className="hud-state-chip hidden sm:inline-flex"
            data-busy={busy || undefined}
            data-alert={alert || undefined}
            data-error={err || undefined}
            role="status"
          >
            <span className={`hud-state-dot ${busy && !prefs.reducedMotion ? 'hud-pulse' : ''}`} aria-hidden />
            {stateLabel(state, lang)}
          </div>
          <ConnectionStatus />
          <button type="button" className="hud-btn md:hidden" onClick={() => setSidebarOpen(!sidebarOpen)}>
            {sidebarOpen ? 'Fechar' : 'Data'}
          </button>
          {(prefs.homeAssistantEnabled || haEnabled) && (
            <button type="button" className="hud-btn" onClick={() => setCasaOpen(true)}>
              Casa
            </button>
          )}
          <button type="button" className="hud-btn" onClick={() => setSaudeOpen(true)}>
            Saúde
          </button>
          <button type="button" className="hud-btn hidden sm:inline-flex" onClick={() => setAgendaOpen(true)}>
            Agenda
          </button>
          <button type="button" className="hud-btn hidden sm:inline-flex" onClick={() => setMailOpen(true)}>
            Mail
          </button>
          <button type="button" className="hud-btn" onClick={() => setSettingsOpen(true)}>
            Config
          </button>
        </header>

        <ErrorNotice />

        <div className="relative z-10 flex min-h-0 flex-1 flex-col">
          <StageWires />

          <div className="pointer-events-none absolute inset-0 z-30 hidden md:block">
            <div className="pointer-events-auto absolute left-5 top-2 w-[210px] lg:left-8 lg:w-[228px]">
              <div className="holo holo-frame p-2">
                <HudDateGauge locale={locale} />
              </div>
              <div className="holo holo-frame mt-3 flex items-start justify-between gap-1 overflow-hidden px-2.5 py-2.5">
                <HudRingMeter label="API" value={backendOk || demo ? 92 : 14} ok={backendOk || demo} />
                <HudRingMeter label="LM" value={llmOk || demo ? 88 : 10} ok={llmOk || demo} />
                <HudRingMeter label="CORE" value={coreLoad} ok={state !== 'error'} />
              </div>
            </div>

            <div className="pointer-events-auto absolute right-5 top-2 w-[220px] space-y-3 lg:right-8 lg:w-[240px]">
              <div className="holo holo-frame p-3">
                <p className="holo-label mb-2">Contexto</p>
                <CountryContextChip country={country} />
                {!country && (
                  <p className="mt-1 text-xs tracking-wide text-[var(--text-muted)]">Sem país em sessão.</p>
                )}
              </div>
              {offerMonitor && (
                <button type="button" onClick={openMonitor} className="hud-btn hud-btn-primary w-full">
                  Abrir monitor
                </button>
              )}
              {sources.length > 0 && (
                <div className="holo holo-frame max-h-40 space-y-2 overflow-y-auto p-3">
                  <p className="holo-label">Fontes · Docs / Memória / Web</p>
                  {sources.map((s, i) => (
                    <SourceCard key={`${s.url}-${i}`} source={s} demo={demo} />
                  ))}
                </div>
              )}
              <div className="holo holo-frame p-3">
                <p className="holo-label mb-2">Sessões</p>
                <SessionList />
              </div>
              <ActivityTimeline />
            </div>
          </div>

          <div className="relative z-[1] flex flex-1 flex-col items-center justify-center px-3 pb-2 pt-1 pointer-events-none">
            <div className="pointer-events-auto">
              <FridayCore />
            </div>
            <div className="pointer-events-auto -mt-2 mb-3 w-full max-w-md">
              <QuickActions orbit />
            </div>
          </div>

          <div className="relative z-20 mx-auto w-full max-w-3xl space-y-2 px-3 pb-4 md:px-6">
            {offerMonitor && (
              <button
                type="button"
                onClick={openMonitor}
                className="hud-btn hud-btn-primary w-full md:hidden"
              >
                Abrir monitor
              </button>
            )}
            <ConversationPanel compact />
            <VoiceControls />
            <p
              className="text-center font-display text-[10px] tracking-[0.5em] text-cyan/40"
              style={{ textShadow: '0 0 10px rgba(92,239,255,0.3)' }}
            >
              FRIDAY SYSTEMS
            </p>
          </div>
        </div>

        {sidebarOpen && (
          <div className="absolute inset-x-3 bottom-28 z-30 max-h-[42vh] space-y-2 overflow-y-auto md:hidden">
            <div className="holo holo-frame p-3">
              <p className="holo-label mb-2">Contexto</p>
              <CountryContextChip country={country} />
            </div>
            {sources.length > 0 && (
              <div className="holo holo-frame space-y-2 p-3">
                <p className="holo-label">Fontes · Docs / Memória / Web</p>
                {sources.map((s, i) => (
                  <SourceCard key={`m-${s.url}-${i}`} source={s} demo={demo} />
                ))}
              </div>
            )}
            <ActivityTimeline />
          </div>
        )}
      </div>

      {settingsOpen && <SettingsPanel onClose={() => setSettingsOpen(false)} />}
      {casaOpen && <CasaPanel onClose={() => setCasaOpen(false)} />}
      {saudeOpen && <SaudePanel onClose={() => setSaudeOpen(false)} />}
      {agendaOpen && <AgendaPanel onClose={() => setAgendaOpen(false)} />}
      {mailOpen && <MailPanel onClose={() => setMailOpen(false)} />}
      <ConfirmationDialog />
    </div>
  )
}
