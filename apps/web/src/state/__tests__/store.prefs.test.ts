import { beforeEach, describe, expect, it, vi } from 'vitest'
import { getJson } from '@/platform/storage'
import { resetAppStore } from '@/test/mockApi'
import { useAppStore } from '../store'

vi.mock('@/api/client', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/api/client')>()
  return {
    ...actual,
    savePrefs: vi.fn().mockResolvedValue({ ok: true }),
  }
})

describe('store prefs', () => {
  beforeEach(() => {
    localStorage.clear()
    resetAppStore({
      error: null,
      prefs: {
        ...useAppStore.getState().prefs,
        theme: 'dark',
        volume: 0.9,
        workingHours: '9:00-18:00',
      },
    })
  })

  it('valid patch updates prefs and persists', () => {
    useAppStore.getState().setPrefs({ theme: 'light', volume: 0.4 })
    const { prefs, error } = useAppStore.getState()
    expect(error).toBeNull()
    expect(prefs.theme).toBe('light')
    expect(prefs.volume).toBe(0.4)
    expect(getJson<{ theme?: string }>('prefs', {}).theme).toBe('light')
  })

  it('invalid volume does not alter prefs and sets error', () => {
    const before = useAppStore.getState().prefs
    useAppStore.getState().setPrefs({ volume: 9 })
    const after = useAppStore.getState()
    expect(after.prefs.volume).toBe(before.volume)
    expect(after.prefs.theme).toBe(before.theme)
    expect(after.error).toBeTruthy()
  })

  it('invalid workingHours does not alter prefs', () => {
    const before = useAppStore.getState().prefs.workingHours
    useAppStore.getState().setPrefs({ workingHours: 'all-day' })
    expect(useAppStore.getState().prefs.workingHours).toBe(before)
    expect(useAppStore.getState().error).toMatch(/H:MM-H:MM/i)
  })
})
