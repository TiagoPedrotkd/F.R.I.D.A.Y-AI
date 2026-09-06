import type { StateCreator } from 'zustand'
import type { AppStore } from './types'

type SetState = (
  partial: AppStore | Partial<AppStore> | ((state: AppStore) => AppStore | Partial<AppStore>),
  replace?: boolean,
) => void

/**
 * Dev-only middleware: logs FridayState transitions.
 * Pair with zustand `devtools` for Redux DevTools time-travel.
 */
export function logger<T extends AppStore>(f: StateCreator<T, [], []>): StateCreator<T, [], []> {
  return (set, get, api) => {
    const loggedSet: SetState = (partial, replace) => {
      const prev = get()
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      ;(set as any)(partial, replace)
      const next = get()
      if (import.meta.env.DEV && prev.state !== next.state) {
        console.warn('[friday/store] state', { from: prev.state, to: next.state })
      }
    }
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    return f(loggedSet as any, get, api)
  }
}

/**
 * Snapshot store, run mutate; on throw restore snapshot and set error.
 * Shallow clone of top-level fields (enough for prefs / casa / flags).
 */
export async function withRollback(
  get: () => AppStore,
  set: (partial: Partial<AppStore>) => void,
  mutate: () => Promise<void>,
): Promise<void> {
  const snap = get()
  const snapshot: Partial<AppStore> = {
    state: snap.state,
    sessionId: snap.sessionId,
    messages: snap.messages,
    activity: snap.activity,
    country: snap.country,
    sources: snap.sources,
    pending: snap.pending,
    alerts: snap.alerts,
    offerMonitorPath: snap.offerMonitorPath,
    prefs: snap.prefs,
    error: snap.error,
    draft: snap.draft,
    casaLoading: snap.casaLoading,
    casaError: snap.casaError,
    casaLights: snap.casaLights,
    casaSwitches: snap.casaSwitches,
    casaEnergy: snap.casaEnergy,
    casaSensors: snap.casaSensors,
    backendOk: snap.backendOk,
    llmOk: snap.llmOk,
    haOk: snap.haOk,
    demoForced: snap.demoForced,
  }
  try {
    await mutate()
  } catch (e) {
    set({
      ...snapshot,
      error: e instanceof Error ? e.message : 'Falha — estado restaurado',
    })
    throw e
  }
}
