import { beforeEach, describe, expect, it } from 'vitest'
import { resetAppStore } from '@/test/mockApi'
import {
  selectAnyPanelOpen,
  selectBusy,
  selectCoreLoad,
  selectDemo,
  selectIsAwaitingConfirm,
  selectIsListening,
  selectMessageCount,
} from '../selectors'
import { useAppStore } from '../store'

describe('selectors', () => {
  beforeEach(() => {
    resetAppStore({
      state: 'idle',
      messages: [],
      demoForced: false,
      settingsOpen: false,
      casaOpen: false,
      saudeOpen: false,
      financasOpen: false,
      agendaOpen: false,
      mailOpen: false,
      prefs: { ...useAppStore.getState().prefs, demoMode: false },
    })
  })

  it('selectBusy / listening / confirm', () => {
    expect(selectBusy(useAppStore.getState())).toBe(false)
    resetAppStore({ state: 'thinking' })
    expect(selectBusy(useAppStore.getState())).toBe(true)
    resetAppStore({ state: 'listening' })
    expect(selectIsListening(useAppStore.getState())).toBe(true)
    resetAppStore({ state: 'awaiting_confirmation' })
    expect(selectIsAwaitingConfirm(useAppStore.getState())).toBe(true)
  })

  it('selectDemo and selectCoreLoad', () => {
    expect(selectDemo(useAppStore.getState())).toBe(false)
    resetAppStore({ demoForced: true })
    expect(selectDemo(useAppStore.getState())).toBe(true)
    resetAppStore({ state: 'error' })
    expect(selectCoreLoad(useAppStore.getState())).toBe(18)
    resetAppStore({ state: 'connecting' })
    expect(selectCoreLoad(useAppStore.getState())).toBe(40)
    resetAppStore({ state: 'idle' })
    expect(selectCoreLoad(useAppStore.getState())).toBe(64)
    resetAppStore({ state: 'speaking' })
    expect(selectCoreLoad(useAppStore.getState())).toBe(84)
  })

  it('selectMessageCount and selectAnyPanelOpen', () => {
    expect(selectMessageCount(useAppStore.getState())).toBe(0)
    expect(selectAnyPanelOpen(useAppStore.getState())).toBe(false)
    useAppStore.getState().setSettingsOpen(true)
    expect(selectAnyPanelOpen(useAppStore.getState())).toBe(true)
  })
})

describe('ui slice setters', () => {
  beforeEach(() => {
    resetAppStore()
  })

  it('toggles panels, draft, and sidebar', () => {
    const s = useAppStore.getState()
    s.setDraft('hello')
    s.setCasaOpen(true)
    s.setSaudeOpen(true)
    s.setFinancasOpen(true)
    s.setAgendaOpen(true)
    s.setMailOpen(true)
    s.setSidebarOpen(true)
    const n = useAppStore.getState()
    expect(n.draft).toBe('hello')
    expect(n.casaOpen && n.saudeOpen && n.financasOpen && n.agendaOpen && n.mailOpen).toBe(true)
    expect(n.sidebarOpen).toBe(true)
  })
})
