import { create } from 'zustand'
import { devtools, persist } from 'zustand/middleware'
import { logger } from './middleware'
import { fridayPrefsStorage } from './persistStorage'
import { createCasaSlice } from './slices/casaSlice'
import { createPrefsSlice } from './slices/prefsSlice'
import { createSessionSlice } from './slices/sessionSlice'
import { createUiSlice } from './slices/uiSlice'
import type { AppStore } from './types'

export type { Message } from './types'
export type { AppStore } from './types'

export const useAppStore = create<AppStore>()(
  devtools(
    persist(
      logger((...a) => ({
        ...createUiSlice(...a),
        ...createSessionSlice(...a),
        ...createPrefsSlice(...a),
        ...createCasaSlice(...a),
      })),
      {
        name: 'friday-prefs',
        partialize: (s) => ({ prefs: s.prefs }),
        storage: fridayPrefsStorage,
      },
    ),
    { name: 'FridayApp' },
  ),
)
