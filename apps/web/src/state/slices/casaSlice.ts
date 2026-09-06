import type { StateCreator } from 'zustand'
import * as api from '@/api/client'
import { transition } from '../machine'
import { uid } from '../helpers'
import { withRollback } from '../middleware'
import type { AppStore, CasaSliceActions, CasaSliceState } from '../types'

export type CasaSlice = CasaSliceState & CasaSliceActions

export const createCasaSlice: StateCreator<AppStore, [], [], CasaSlice> = (set, get) => ({
  casaLoading: false,
  casaError: null,
  casaLights: [],
  casaSwitches: [],
  casaEnergy: [],
  casaSensors: [],

  refreshCasa: async () => {
    if (!get().prefs.homeAssistantEnabled) {
      set({
        casaError: 'Integração Home Assistant desactivada nas definições.',
        casaLights: [],
        casaSwitches: [],
        casaEnergy: [],
        casaSensors: [],
      })
      return
    }
    set({ casaLoading: true, casaError: null })
    try {
      const [st, lights, switches, energy, sensors] = await Promise.all([
        api.fetchHaStatus(),
        api.fetchHaEntities('light'),
        api.fetchHaEntities('switch'),
        api.fetchHaEnergy(),
        api.fetchHaEntities('sensor', 80),
      ])
      const energyIds = new Set((energy.entities || []).map((e) => e.entity_id))
      set({
        haEnabled: true,
        haOk: Boolean(st.ok),
        haUrl: st.url || get().haUrl,
        casaLights: lights.entities || [],
        casaSwitches: switches.entities || [],
        casaEnergy: energy.entities || [],
        casaSensors: (sensors.entities || []).filter((e) => !energyIds.has(e.entity_id)),
        casaLoading: false,
        casaError: null,
      })
    } catch (e) {
      const msg = e instanceof Error ? e.message : 'Falha ao ler Home Assistant'
      set({
        casaLoading: false,
        casaError: msg,
        haOk: false,
      })
    }
  },

  requestCasaAction: async (entityId, service) => {
    const { sessionId, prefs } = get()
    if (!sessionId) {
      set({ error: 'Sem sessão activa.' })
      return
    }
    if (prefs.demoMode || get().demoForced) {
      set({
        pending: {
          action: 'ha_call_service',
          target: entityId,
          summary: `${service} ${entityId}`,
          consequences: 'Demo — não altera dispositivos reais.',
          preview: { entity_id: entityId, service },
        },
        state: transition(get().state, 'awaiting_confirmation'),
      })
      return
    }
    try {
      await withRollback(get, set, async () => {
        const res = await api.requestHaAction(sessionId, entityId, service)
        set({
          pending: res.pending_confirmation,
          state: transition(get().state, 'awaiting_confirmation'),
          messages: [...get().messages, { id: uid(), role: 'assistant', text: res.reply }],
        })
      })
    } catch (e) {
      set({
        error: e instanceof Error ? e.message : 'Falha ao pedir acção HA',
        state: transition(get().state, 'error'),
      })
    }
  },
})
