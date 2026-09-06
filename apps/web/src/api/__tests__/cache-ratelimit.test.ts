import { afterEach, describe, expect, it, vi } from 'vitest'
import { z } from 'zod'
import { HttpClient } from '../http-client'

const OkSchema = z.object({ ok: z.boolean(), n: z.number().optional() })

function jsonOk(body: unknown) {
  return new Response(JSON.stringify(body), {
    status: 200,
    headers: { 'Content-Type': 'application/json' },
  })
}

describe('HttpClient cache', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
    vi.restoreAllMocks()
    vi.useRealTimers()
  })

  it('returns cached GET within TTL', async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonOk({ ok: true }))
    vi.stubGlobal('fetch', fetchMock)
    const client = new HttpClient({ retries: 1 })

    const a = await client.request({
      path: '/v1/cached',
      schema: OkSchema,
      cache: { ttlMs: 60_000 },
    })
    const b = await client.request({
      path: '/v1/cached',
      schema: OkSchema,
      cache: { ttlMs: 60_000 },
    })
    expect(a).toEqual({ ok: true })
    expect(b).toEqual({ ok: true })
    expect(fetchMock).toHaveBeenCalledTimes(1)
  })

  it('misses cache after TTL expiry', async () => {
    vi.useFakeTimers()
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonOk({ ok: true, n: 1 }))
      .mockResolvedValueOnce(jsonOk({ ok: true, n: 2 }))
    vi.stubGlobal('fetch', fetchMock)
    const client = new HttpClient({ retries: 1 })

    await client.request({
      path: '/v1/ttl',
      schema: OkSchema,
      cache: { ttlMs: 1000 },
    })
    await vi.advanceTimersByTimeAsync(1001)
    const second = await client.request({
      path: '/v1/ttl',
      schema: OkSchema,
      cache: { ttlMs: 1000 },
    })
    expect(second).toEqual({ ok: true, n: 2 })
    expect(fetchMock).toHaveBeenCalledTimes(2)
  })

  it('skipCache bypasses store', async () => {
    const fetchMock = vi.fn().mockImplementation(() => jsonOk({ ok: true }))
    vi.stubGlobal('fetch', fetchMock)
    const client = new HttpClient({ retries: 1 })

    await client.request({
      path: '/v1/skip',
      schema: OkSchema,
      cache: { ttlMs: 60_000 },
    })
    await client.request({
      path: '/v1/skip',
      schema: OkSchema,
      cache: { ttlMs: 60_000 },
      skipCache: true,
    })
    expect(fetchMock).toHaveBeenCalledTimes(2)
  })
})

describe('HttpClient rate limit', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
    vi.restoreAllMocks()
    vi.useRealTimers()
  })

  it('respects Retry-After on 429 before retry', async () => {
    vi.useFakeTimers()
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(
        new Response('slow down', {
          status: 429,
          headers: { 'Retry-After': '2' },
        }),
      )
      .mockImplementationOnce(() => jsonOk({ ok: true }))
    vi.stubGlobal('fetch', fetchMock)

    const client = new HttpClient({ retryBaseMs: 1 })
    const pending = client.request({
      path: '/v1/limited',
      schema: OkSchema,
      retries: 2,
    })

    await vi.advanceTimersByTimeAsync(2500)
    await expect(pending).resolves.toEqual({ ok: true })
    expect(fetchMock).toHaveBeenCalledTimes(2)
  })

  it('enforces minIntervalMs between requests', async () => {
    vi.useFakeTimers()
    const fetchMock = vi.fn().mockImplementation(() => jsonOk({ ok: true }))
    vi.stubGlobal('fetch', fetchMock)
    const client = new HttpClient({ retries: 1, minIntervalMs: 100 })

    const p1 = client.request({ path: '/v1/a', schema: OkSchema })
    await vi.advanceTimersByTimeAsync(0)
    await p1

    const p2 = client.request({ path: '/v1/b', schema: OkSchema })
    expect(fetchMock).toHaveBeenCalledTimes(1)
    await vi.advanceTimersByTimeAsync(100)
    await p2
    expect(fetchMock).toHaveBeenCalledTimes(2)
  })
})
