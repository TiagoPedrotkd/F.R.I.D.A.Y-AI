import { beforeEach, describe, expect, it, vi } from 'vitest'
import { resetAppStore } from '@/test/mockApi'
import { useAppStore } from '../store'

describe('store transitions', () => {
  beforeEach(() => {
    resetAppStore({ state: 'idle', error: null })
    vi.spyOn(console, 'warn').mockImplementation(() => {})
  })

  it('setState idle → listening', () => {
    useAppStore.getState().setState('listening')
    expect(useAppStore.getState().state).toBe('listening')
  })

  it('setState listening → speaking is rejected (stays listening)', () => {
    resetAppStore({ state: 'listening' })
    useAppStore.getState().setState('speaking')
    expect(useAppStore.getState().state).toBe('listening')
  })

  it('setState speaking → idle is allowed', () => {
    resetAppStore({ state: 'speaking' })
    useAppStore.getState().setState('idle')
    expect(useAppStore.getState().state).toBe('idle')
  })

  it('clearError clears ui error', () => {
    resetAppStore({ error: 'x' })
    useAppStore.getState().clearError()
    expect(useAppStore.getState().error).toBeNull()
  })
})
