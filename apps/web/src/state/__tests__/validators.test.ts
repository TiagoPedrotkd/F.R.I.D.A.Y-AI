import { describe, expect, it } from 'vitest'
import {
  FridayStateSchema,
  MessageRatingSchema,
  PrefsPatchSchema,
  parseFridayState,
  parseMessageRating,
  safeParsePrefsPatch,
} from '../validators'

describe('validators', () => {
  it('accepts valid FridayState and rating', () => {
    expect(parseFridayState('idle')).toBe('idle')
    expect(FridayStateSchema.safeParse('speaking').success).toBe(true)
    expect(parseMessageRating('up')).toBe('up')
    expect(MessageRatingSchema.safeParse('down').success).toBe(true)
  })

  it('rejects invalid FridayState and rating', () => {
    expect(FridayStateSchema.safeParse('flying').success).toBe(false)
    expect(MessageRatingSchema.safeParse('meh').success).toBe(false)
  })

  it('accepts valid prefs patch', () => {
    const r = safeParsePrefsPatch({
      theme: 'light',
      volume: 0.5,
      rate: 1.2,
      workingHours: '9:00-18:00',
      doNotDisturb: '22:00-8:00',
      preferredMeetingDuration: 45,
    })
    expect(r.ok).toBe(true)
    if (r.ok) {
      expect(r.data.theme).toBe('light')
      expect(r.data.volume).toBe(0.5)
    }
  })

  it('allows empty working hours / DND', () => {
    const r = safeParsePrefsPatch({ workingHours: '', doNotDisturb: '' })
    expect(r.ok).toBe(true)
  })

  it('rejects volume outside 0–1', () => {
    const high = safeParsePrefsPatch({ volume: 1.5 })
    expect(high.ok).toBe(false)
    if (!high.ok) expect(high.message.length).toBeGreaterThan(0)

    const low = safeParsePrefsPatch({ volume: -0.1 })
    expect(low.ok).toBe(false)
  })

  it('rejects invalid workingHours format', () => {
    const r = safeParsePrefsPatch({ workingHours: '9am-5pm' })
    expect(r.ok).toBe(false)
    if (!r.ok) expect(r.message).toMatch(/H:MM-H:MM/i)
  })

  it('rejects non-positive preferredMeetingDuration', () => {
    expect(safeParsePrefsPatch({ preferredMeetingDuration: 0 }).ok).toBe(false)
    expect(safeParsePrefsPatch({ preferredMeetingDuration: -5 }).ok).toBe(false)
  })

  it('rejects unknown keys (strict)', () => {
    expect(PrefsPatchSchema.safeParse({ notAPref: true }).success).toBe(false)
  })
})
