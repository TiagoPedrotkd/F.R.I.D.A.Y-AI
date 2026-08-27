import { describe, expect, it } from 'vitest'
import { canTransition, transition } from '../state/machine'

describe('state machine', () => {
  it('allows listening after idle', () => {
    expect(canTransition('idle', 'listening')).toBe(true)
    expect(transition('idle', 'listening')).toBe('listening')
  })

  it('rejects listening while speaking', () => {
    expect(canTransition('speaking', 'listening')).toBe(true) // interrupt path allowed
    expect(canTransition('listening', 'speaking')).toBe(false)
    expect(transition('listening', 'speaking')).toBe('listening')
  })

  it('idempotent same state', () => {
    expect(transition('idle', 'idle')).toBe('idle')
  })
})
