import { describe, expect, it, vi } from 'vitest'
import { ALLOWED, canTransition, stateLabel, transition, type FridayState } from '../machine'

const ALL_STATES = Object.keys(ALLOWED) as FridayState[]

describe('state machine', () => {
  it('allows listening after idle', () => {
    expect(canTransition('idle', 'listening')).toBe(true)
    expect(transition('idle', 'listening')).toBe('listening')
  })

  it('rejects listening while speaking path is one-way from listening', () => {
    expect(canTransition('speaking', 'listening')).toBe(true)
    expect(canTransition('listening', 'speaking')).toBe(false)
    expect(transition('listening', 'speaking')).toBe('listening')
  })

  it('idempotent same state', () => {
    expect(transition('idle', 'idle')).toBe('idle')
  })

  it.each(ALL_STATES.flatMap((from) => ALLOWED[from].map((to) => ({ from, to }))))(
    'allows $from → $to',
    ({ from, to }) => {
      expect(canTransition(from, to)).toBe(true)
      expect(transition(from, to)).toBe(to)
    },
  )

  it('blocks transitions not in ALLOWED', () => {
    const spy = vi.spyOn(console, 'warn').mockImplementation(() => {})
    expect(canTransition('offline', 'speaking')).toBe(false)
    expect(transition('offline', 'speaking')).toBe('offline')
    expect(spy).toHaveBeenCalled()
    spy.mockRestore()
  })

  it('returns PT and EN labels', () => {
    expect(stateLabel('thinking', 'pt')).toMatch(/pensar/i)
    expect(stateLabel('thinking', 'en')).toMatch(/thinking/i)
  })
})
