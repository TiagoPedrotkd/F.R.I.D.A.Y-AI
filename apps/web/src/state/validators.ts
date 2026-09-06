import { z } from 'zod'
import type { FridayState } from './machine'

/** HH:MM-HH:MM or empty (working hours / DND strings in Settings). */
const timeRangeRegex = /^$|^\d{1,2}:\d{2}-\d{1,2}:\d{2}$/

export const FridayStateSchema = z.enum([
  'offline',
  'connecting',
  'idle',
  'listening',
  'transcribing',
  'thinking',
  'tool_calling',
  'awaiting_confirmation',
  'speaking',
  'error',
])

export const MessageRatingSchema = z.enum(['up', 'down'])

export const PrefsPatchSchema = z
  .object({
    language: z.enum(['pt', 'en']).optional(),
    theme: z.enum(['dark', 'light']).optional(),
    userAddress: z.string().optional(),
    ttsEnabled: z.boolean().optional(),
    volume: z.number().min(0).max(1).optional(),
    rate: z.number().min(0.5).max(2).optional(),
    autoplay: z.boolean().optional(),
    interrupt: z.boolean().optional(),
    autoOpenMonitors: z.boolean().optional(),
    highContrast: z.boolean().optional(),
    reducedMotion: z.boolean().optional(),
    demoMode: z.boolean().optional(),
    workingHours: z.string().regex(timeRangeRegex, 'Use H:MM-H:MM (ex. 9:00-18:00)').optional(),
    preferredMeetingDuration: z.number().int().positive().max(480).optional(),
    doNotDisturb: z.string().regex(timeRangeRegex, 'Use H:MM-H:MM (ex. 22:00-8:00)').optional(),
    profileGoals: z.string().optional(),
    profileHabits: z.string().optional(),
    profilePreferences: z.string().optional(),
    profileConstraints: z.string().optional(),
    domainsOfInterest: z.string().optional(),
    homeAssistantEnabled: z.boolean().optional(),
    openBankingEnabled: z.boolean().optional(),
  })
  .strict()

export type PrefsPatch = z.infer<typeof PrefsPatchSchema>

export function parseFridayState(value: unknown): FridayState {
  return FridayStateSchema.parse(value)
}

export function parseMessageRating(value: unknown): 'up' | 'down' {
  return MessageRatingSchema.parse(value)
}

export function safeParsePrefsPatch(value: unknown):
  | {
      ok: true
      data: PrefsPatch
    }
  | {
      ok: false
      message: string
    } {
  const r = PrefsPatchSchema.safeParse(value)
  if (r.success) return { ok: true, data: r.data }
  const first = r.error.issues[0]
  return {
    ok: false,
    message: first?.message || 'Preferências inválidas',
  }
}
