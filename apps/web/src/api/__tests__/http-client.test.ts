import { afterEach, describe, expect, it, vi } from 'vitest'
import { z } from 'zod'
import { HttpError, ValidationError } from '../errors'
import { HttpClient } from '../http-client'
import { apiRequest } from '../http'

const OkSchema = z.object({ ok: z.boolean() })

function jsonOk(body: unknown, init?: ResponseInit) {
  return new Response(JSON.stringify(body), {
    status: 200,
    headers: { 'Content-Type': 'application/json' },
    ...init,
  })
}

describe('HttpClient', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
    vi.restoreAllMocks()
    vi.useRealTimers()
  })

  it('retries 503 then succeeds', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(new Response('err', { status: 503 }))
      .mockResolvedValueOnce(jsonOk({ ok: true }))
    vi.stubGlobal('fetch', fetchMock)

    const client = new HttpClient({ retryBaseMs: 1 })
    const data = await client.request({
      path: '/v1/test',
      schema: OkSchema,
      retries: 3,
      timeoutMs: 5000,
    })
    expect(data).toEqual({ ok: true })
    expect(fetchMock).toHaveBeenCalledTimes(2)
  })

  it('does not retry 400', async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response('bad', { status: 400 }))
    vi.stubGlobal('fetch', fetchMock)
    const client = new HttpClient({ retryBaseMs: 1 })

    await expect(
      client.request({ path: '/v1/test', schema: OkSchema, retries: 3 }),
    ).rejects.toBeInstanceOf(HttpError)
    expect(fetchMock).toHaveBeenCalledTimes(1)
  })

  it('throws ValidationError on bad body shape', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonOk({ nope: true })))
    const client = new HttpClient()
    await expect(
      client.request({ path: '/v1/test', schema: OkSchema, retries: 1 }),
    ).rejects.toBeInstanceOf(ValidationError)
  })

  it('includes path/method/status/body in HttpError context', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response('nope', { status: 502 })))
    const client = new HttpClient({ retries: 1 })
    try {
      await client.request({ path: '/v1/x', schema: OkSchema, method: 'GET' })
      expect.fail('should throw')
    } catch (e) {
      expect(e).toBeInstanceOf(HttpError)
      const err = e as HttpError
      expect(err.context?.path).toBe('/v1/x')
      expect(err.context?.method).toBe('GET')
      expect(err.context?.status).toBe(502)
      expect(err.context?.body).toBe('nope')
    }
  })

  it('apiRequest delegates to shared client', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonOk({ ok: true })))
    const data = await apiRequest({
      path: '/v1/compat',
      schema: OkSchema,
      retries: 1,
      retryBaseMs: 1,
    })
    expect(data.ok).toBe(true)
  })
})

describe('HttpClient request interceptor', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
    vi.restoreAllMocks()
  })

  it('allows request interceptor to inject headers', async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonOk({ ok: true }))
    vi.stubGlobal('fetch', fetchMock)
    const client = new HttpClient({ retries: 1 })
    client.onRequest.push((ctx) => ({
      ...ctx,
      headers: { ...ctx.headers, 'X-Trace': '1' },
    }))

    await client.request({ path: '/v1/test', schema: OkSchema })
    const init = fetchMock.mock.calls[0][1] as RequestInit
    expect((init.headers as Record<string, string>)['X-Trace']).toBe('1')
  })
})
