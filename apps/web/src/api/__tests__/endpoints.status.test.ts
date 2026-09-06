import { afterEach, describe, expect, it, vi } from 'vitest'
import { ValidationError } from '../errors'
import { fetchStatus } from '../endpoints/status'
import { HttpClient } from '../http-client'
import { StatusResponseSchema } from '../schemas'

const statusBody = {
  status: 'ok',
  backend: true,
  demo: false,
  llm: { ok: true, model: 'test' },
}

describe('endpoints/status', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
    vi.restoreAllMocks()
  })

  it('fetchStatus returns typed StatusResponse', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify(statusBody), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        }),
      ),
    )
    const data = await fetchStatus()
    expect(data.backend).toBe(true)
    expect(data.llm.ok).toBe(true)
  })

  it('fetchStatus with custom client throws ValidationError', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ status: 'ok' }), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        }),
      ),
    )
    const client = new HttpClient({ retries: 1 })
    await expect(fetchStatus({ client })).rejects.toBeInstanceOf(ValidationError)
  })

  it('StatusResponseSchema rejects incomplete payloads', () => {
    expect(StatusResponseSchema.safeParse({ status: 'ok' }).success).toBe(false)
  })
})
