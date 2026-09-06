import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { create } from 'zustand'
import { logger, withRollback } from '../middleware'
import type { AppStore } from '../types'
import { useAppStore } from '../store'
import { resetAppStore } from '@/test/mockApi'

describe('logger middleware', () => {
  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('logs FridayState transitions in DEV', () => {
    const warn = vi.spyOn(console, 'warn').mockImplementation(() => {})
    type Mini = { state: string; setState: (s: string) => void }
    // Minimal store to exercise logger without full AppStore shape
    const useMini = create<Mini>()(
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      (logger as any)((set: (p: Partial<Mini>) => void) => ({
        state: 'idle',
        setState: (s: string) => set({ state: s }),
      })),
    )
    useMini.getState().setState('listening')
    expect(warn).toHaveBeenCalledWith(
      '[friday/store] state',
      expect.objectContaining({ from: 'idle', to: 'listening' }),
    )
  })
})

describe('withRollback', () => {
  beforeEach(() => {
    resetAppStore({
      state: 'idle',
      draft: 'keep-me',
      error: null,
      messages: [],
    })
  })

  it('restores snapshot and sets error when mutate throws', async () => {
    const get = () => useAppStore.getState()
    const set = (partial: Partial<AppStore>) => useAppStore.setState(partial)

    await expect(
      withRollback(get, set, async () => {
        set({ draft: 'mutated', state: 'thinking' })
        throw new Error('boom')
      }),
    ).rejects.toThrow(/boom/)

    const s = useAppStore.getState()
    expect(s.draft).toBe('keep-me')
    expect(s.state).toBe('idle')
    expect(s.error).toMatch(/boom/)
  })

  it('keeps changes when mutate succeeds', async () => {
    const get = () => useAppStore.getState()
    const set = (partial: Partial<AppStore>) => useAppStore.setState(partial)

    await withRollback(get, set, async () => {
      set({ draft: 'ok' })
    })

    expect(useAppStore.getState().draft).toBe('ok')
    expect(useAppStore.getState().error).toBeNull()
  })
})
