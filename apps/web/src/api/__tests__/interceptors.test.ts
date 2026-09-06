import { afterEach, describe, expect, it, vi } from 'vitest'
import { z } from 'zod'
import { HttpClient } from '../http-client'

const OkSchema = z.object({ ok: z.boolean() })

describe('interceptors', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
    vi.restoreAllMocks()
  })

  it('response interceptor can reshape data before Zod', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ value: true }), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        }),
      ),
    )
    const client = new HttpClient({ retries: 1 })
    client.onResponse.push((ctx) => ({
      ...ctx,
      data: { ok: (ctx.data as { value: boolean }).value },
    }))

    const data = await client.request({ path: '/v1/wrap', schema: OkSchema })
    expect(data).toEqual({ ok: true })
  })

  it('error interceptor runs on failure', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response('x', { status: 500 })))
    const client = new HttpClient({ retries: 1, retryBaseMs: 1 })
    const spy = vi.fn(async (err: unknown) => err)
    client.onError = [spy]

    await expect(client.request({ path: '/v1/fail', schema: OkSchema })).rejects.toBeTruthy()
    expect(spy).toHaveBeenCalled()
  })
})
