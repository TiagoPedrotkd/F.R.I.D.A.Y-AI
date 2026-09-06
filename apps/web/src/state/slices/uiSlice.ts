import type { StateCreator } from 'zustand'
import type { AppStore, UiSliceActions, UiSliceState } from '../types'

export type UiSlice = UiSliceState & UiSliceActions

export const createUiSlice: StateCreator<AppStore, [], [], UiSlice> = (set) => ({
  error: null,
  draft: '',
  settingsOpen: false,
  casaOpen: false,
  saudeOpen: false,
  financasOpen: false,
  agendaOpen: false,
  mailOpen: false,
  sidebarOpen: false,

  setDraft: (v) => set({ draft: v }),
  setSettingsOpen: (v) => set({ settingsOpen: v }),
  setCasaOpen: (v) => set({ casaOpen: v }),
  setSaudeOpen: (v) => set({ saudeOpen: v }),
  setFinancasOpen: (v) => set({ financasOpen: v }),
  setAgendaOpen: (v) => set({ agendaOpen: v }),
  setMailOpen: (v) => set({ mailOpen: v }),
  setSidebarOpen: (v) => set({ sidebarOpen: v }),
  clearError: () => set({ error: null }),
})
