import { afterEach, describe, expect, it, vi } from 'vitest'
import { z } from 'zod'
import { HttpError, ValidationError } from './errors'
import { apiRequest } from './http'

const OkSchema = z.object({ ok: z.boolean() })

describe('apiRequest', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
    vi.restoreAllMocks()
  })

  it('retries 500 then succeeds', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(new Response('err', { status: 500 }))
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ ok: true }), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        }),
      )
    vi.stubGlobal('fetch', fetchMock)

    const data = await apiRequest({
      path: '/v1/test',
      schema: OkSchema,
      retries: 3,
      retryBaseMs: 1,
      timeoutMs: 5000,
    })
    expect(data).toEqual({ ok: true })
    expect(fetchMock).toHaveBeenCalledTimes(2)
  })

  it('does not retry 400', async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response('bad', { status: 400 }))
    vi.stubGlobal('fetch', fetchMock)

    await expect(
      apiRequest({
        path: '/v1/test',
        schema: OkSchema,
        retries: 3,
        retryBaseMs: 1,
      }),
    ).rejects.toBeInstanceOf(HttpError)
    expect(fetchMock).toHaveBeenCalledTimes(1)
  })

  it('throws ValidationError on bad body shape', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ nope: true }), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        }),
      ),
    )

    await expect(
      apiRequest({ path: '/v1/test', schema: OkSchema, retries: 1 }),
    ).rejects.toBeInstanceOf(ValidationError)
  })
})
