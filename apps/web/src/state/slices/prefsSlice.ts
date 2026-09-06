import type { StateCreator } from 'zustand'
import * as api from '@/api/client'
import { defaultPrefs } from '@/demo/fixtures'
import { getJson, setJson } from '@/platform/storage'
import { applyPrefsDom } from '../helpers'
import type { AppStore, PrefsSliceActions, PrefsSliceState } from '../types'
import { safeParsePrefsPatch } from '../validators'

export type PrefsSlice = PrefsSliceState & PrefsSliceActions

export const createPrefsSlice: StateCreator<AppStore, [], [], PrefsSlice> = (set, get) => ({
  prefs: { ...defaultPrefs, ...getJson<Partial<typeof defaultPrefs>>('prefs', {}) },

  setPrefs: (p) => {
    const parsed = safeParsePrefsPatch(p)
    if (!parsed.ok) {
      set({ error: parsed.message })
      return
    }
    const prefs = { ...get().prefs, ...parsed.data }
    setJson('prefs', prefs)
    applyPrefsDom(prefs)
    set({ prefs, error: null })
    void api
      .savePrefs({
        language: prefs.language,
        theme: prefs.theme,
        user_address: prefs.userAddress,
        tts_enabled: prefs.ttsEnabled,
        volume: prefs.volume,
        rate: prefs.rate,
        autoplay: prefs.autoplay,
        interrupt: prefs.interrupt,
        auto_open_monitors: prefs.autoOpenMonitors,
        high_contrast: prefs.highContrast,
        reduced_motion: prefs.reducedMotion,
        productivity_patterns: {
          working_hours: prefs.workingHours,
          preferred_meeting_duration: prefs.preferredMeetingDuration,
          do_not_disturb: prefs.doNotDisturb,
        },
        user_profile: {
          goals: prefs.profileGoals,
          habits: prefs.profileHabits,
          preferences: prefs.profilePreferences,
          constraints: prefs.profileConstraints,
          domains_of_interest: prefs.domainsOfInterest
            .split(',')
            .map((s) => s.trim())
            .filter(Boolean),
        },
        integrations_enabled: {
          weather: true,
          health_file: true,
          notion_export: true,
          strava_file: true,
          home_assistant: prefs.homeAssistantEnabled,
          open_banking: prefs.openBankingEnabled,
        },
      })
      .catch(() => undefined)
  },
})
