import { createJSONStorage, type StateStorage } from 'zustand/middleware'
import { getItem, setItem } from '@/platform/storage'

/**
 * Zustand persist adapter on top of `friday.prefs.*` localStorage keys.
 * Migrates legacy raw `friday.prefs.prefs` JSON into the persist envelope.
 */
const adapter: StateStorage = {
  getItem: (name) => {
    const raw = getItem(name)
    if (raw) return raw
    const legacy = getItem('prefs')
    if (!legacy) return null
    try {
      const prefs = JSON.parse(legacy) as unknown
      return JSON.stringify({ state: { prefs }, version: 0 })
    } catch {
      return null
    }
  },
  setItem: (name, value) => {
    setItem(name, value)
    try {
      const parsed = JSON.parse(value) as { state?: { prefs?: unknown } }
      if (parsed?.state?.prefs != null) {
        setItem('prefs', JSON.stringify(parsed.state.prefs))
      }
    } catch {
      /* ignore */
    }
  },
  removeItem: (name) => {
    try {
      localStorage.removeItem(`friday.prefs.${name}`)
    } catch {
      /* ignore */
    }
  },
}

export const fridayPrefsStorage = createJSONStorage(() => adapter)
