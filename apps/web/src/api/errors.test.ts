import { describe, expect, it } from 'vitest'
import { HttpError, NetworkError, ValidationError, isRetryable, toUserMessage } from './errors'

describe('api errors', () => {
  it('marks 5xx and network as retryable', () => {
    expect(isRetryable(new HttpError(500, 'boom'))).toBe(true)
    expect(isRetryable(new HttpError(429, 'slow'))).toBe(true)
    expect(isRetryable(new NetworkError('offline'))).toBe(true)
  })

  it('does not retry client errors or validation', () => {
    expect(isRetryable(new HttpError(400, 'bad'))).toBe(false)
    expect(isRetryable(new ValidationError('bad', []))).toBe(false)
  })

  it('returns short PT messages', () => {
    expect(toUserMessage(new NetworkError('x'))).toMatch(/ligação|rede/i)
    expect(toUserMessage(new ValidationError('x', []))).toMatch(/inválida/i)
    expect(toUserMessage(new HttpError(503, '{}'))).toMatch(/Servidor/i)
  })
})
