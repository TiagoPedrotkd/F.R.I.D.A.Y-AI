import { useCallback, useEffect } from 'react'
import type { HaEntity } from '../api/client'
import { useAppStore } from '../state/store'

function labelOf(e: HaEntity): string {
  return e.friendly_name || e.entity_id
}

function EntityRow({
  entity,
  onAction,
  busy,
}: {
  entity: HaEntity
  onAction: (eid: string, service: 'turn_on' | 'turn_off' | 'toggle') => void
  busy: boolean
}) {
  const on = String(entity.state || '').toLowerCase() === 'on'
  return (
    <li className="flex items-center justify-between gap-2 border-b border-cyan/10 py-2">
      <div className="min-w-0">
        <p className="truncate text-sm text-cyan">{labelOf(entity)}</p>
        <p className="truncate text-[10px] text-[var(--text-muted)]">
          {entity.entity_id} · {entity.state ?? '—'}
        </p>
      </div>
      <div className="flex shrink-0 gap-1">
        <button
          type="button"
          className="hud-btn px-2 py-0.5 text-[10px]"
          disabled={busy || on}
          onClick={() => onAction(entity.entity_id, 'turn_on')}
        >
          On
        </button>
        <button
          type="button"
          className="hud-btn px-2 py-0.5 text-[10px]"
          disabled={busy || !on}
          onClick={() => onAction(entity.entity_id, 'turn_off')}
        >
          Off
        </button>
        <button
          type="button"
          className="hud-btn px-2 py-0.5 text-[10px]"
          disabled={busy}
          onClick={() => onAction(entity.entity_id, 'toggle')}
        >
          ⇄
        </button>
      </div>
    </li>
  )
}

function SensorRow({ entity }: { entity: HaEntity }) {
  const unit = entity.unit_of_measurement ? ` ${entity.unit_of_measurement}` : ''
  return (
    <li className="flex items-baseline justify-between gap-2 border-b border-cyan/10 py-1.5 text-sm">
      <span className="min-w-0 truncate text-[var(--text-muted)]">{labelOf(entity)}</span>
      <span className="shrink-0 font-mono text-cyan">
        {entity.state ?? '—'}
        {unit}
      </span>
    </li>
  )
}

export function CasaPanel({ onClose }: { onClose: () => void }) {
  const haEnabled = useAppStore((s) => s.haEnabled)
  const haOk = useAppStore((s) => s.haOk)
  const haUrl = useAppStore((s) => s.haUrl)
  const casaLoading = useAppStore((s) => s.casaLoading)
  const casaError = useAppStore((s) => s.casaError)
  const casaLights = useAppStore((s) => s.casaLights)
  const casaSwitches = useAppStore((s) => s.casaSwitches)
  const casaEnergy = useAppStore((s) => s.casaEnergy)
  const casaSensors = useAppStore((s) => s.casaSensors)
  const pending = useAppStore((s) => s.pending)
  const refreshCasa = useAppStore((s) => s.refreshCasa)
  const requestCasaAction = useAppStore((s) => s.requestCasaAction)

  const load = useCallback(() => {
    void refreshCasa()
  }, [refreshCasa])

  useEffect(() => {
    load()
    const id = window.setInterval(load, 12000)
    return () => window.clearInterval(id)
  }, [load])

  const busy = Boolean(pending) || casaLoading

  return (
    <div className="fixed inset-0 z-40 flex justify-end bg-black/60" role="presentation">
      <div
        role="dialog"
        aria-modal="true"
        aria-label="Casa"
        className="hud-panel h-full w-full max-w-md overflow-y-auto border-l border-cyan/30 p-5"
        style={{ clipPath: 'none', borderRadius: 0 }}
      >
        <div className="mb-5 flex items-center justify-between">
          <div>
            <p className="hud-label">Integração</p>
            <h2 className="font-display text-lg font-semibold tracking-wide text-cyan">Casa</h2>
          </div>
          <button type="button" className="hud-btn" onClick={onClose}>
            Fechar
          </button>
        </div>

        <section className="mb-5 space-y-2 text-sm">
          <p className="hud-label">Home Assistant</p>
          {!haEnabled ? (
            <p className="text-[var(--text-muted)]">
              HA desactivado no servidor (`HA_ENABLED`). Activa no `.env` e reinicia o agent-api.
            </p>
          ) : (
            <>
              <p>
                Estado:{' '}
                <span className={haOk ? 'text-cyan' : 'text-amber'}>
                  {haOk === null ? 'a verificar…' : haOk ? 'online' : 'offline / erro'}
                </span>
              </p>
              {haUrl ? (
                <a
                  className="inline-block text-xs text-cyan underline underline-offset-2"
                  href={haUrl}
                  target="_blank"
                  rel="noreferrer"
                >
                  Abrir Home Assistant
                </a>
              ) : null}
            </>
          )}
          {casaError ? <p className="text-xs text-amber">{casaError}</p> : null}
          <button type="button" className="hud-btn text-xs" disabled={casaLoading} onClick={load}>
            {casaLoading ? 'A actualizar…' : 'Actualizar'}
          </button>
        </section>

        <section className="mb-5">
          <p className="hud-label mb-1">Luzes</p>
          {casaLights.length === 0 ? (
            <p className="text-xs text-[var(--text-muted)]">Sem luzes no HA.</p>
          ) : (
            <ul>
              {casaLights.map((e) => (
                <EntityRow key={e.entity_id} entity={e} onAction={requestCasaAction} busy={busy} />
              ))}
            </ul>
          )}
        </section>

        <section className="mb-5">
          <p className="hud-label mb-1">Switches</p>
          {casaSwitches.length === 0 ? (
            <p className="text-xs text-[var(--text-muted)]">Sem switches no HA.</p>
          ) : (
            <ul>
              {casaSwitches.map((e) => (
                <EntityRow key={e.entity_id} entity={e} onAction={requestCasaAction} busy={busy} />
              ))}
            </ul>
          )}
        </section>

        <section className="mb-5">
          <p className="hud-label mb-1">Energia</p>
          {casaEnergy.length === 0 ? (
            <p className="text-xs text-[var(--text-muted)]">
              Sem sensores de energia/potência. Liga um contador (P1/óptico) no HA.
            </p>
          ) : (
            <ul>
              {casaEnergy.map((e) => (
                <SensorRow key={e.entity_id} entity={e} />
              ))}
            </ul>
          )}
        </section>

        <section>
          <p className="hud-label mb-1">Outros sensores</p>
          {casaSensors.length === 0 ? (
            <p className="text-xs text-[var(--text-muted)]">Sem sensores adicionais.</p>
          ) : (
            <ul>
              {casaSensors.slice(0, 40).map((e) => (
                <SensorRow key={e.entity_id} entity={e} />
              ))}
            </ul>
          )}
        </section>
      </div>
    </div>
  )
}
