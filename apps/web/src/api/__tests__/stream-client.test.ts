import { afterEach, describe, expect, it, vi } from 'vitest'
import { HttpError, ValidationError } from '../errors'
import { HttpClient } from '../http-client'
import { chatStream, feedSseBuffer, parseSseBlock, streamRequest } from '../stream-client'

describe('SSE parser', () => {
  it('feedSseBuffer splits complete blocks and keeps remainder', () => {
    const a = feedSseBuffer('', 'event: token\ndata: {"text":"Olá"}\n\nevent: done\ndata: {"re')
    expect(a.blocks).toHaveLength(1)
    expect(a.buffer).toBe('event: done\ndata: {"re')
    const b = feedSseBuffer(a.buffer, 'ply":"Olá"}\n\n')
    expect(b.blocks).toHaveLength(1)
    expect(b.buffer).toBe('')
  })

  it('parseSseBlock reads event and data lines', () => {
    expect(parseSseBlock('event: token\ndata: {"text":"x"}')).toEqual({
      event: 'token',
      data: '{"text":"x"}',
    })
    expect(parseSseBlock('data: only')).toEqual({ event: 'message', data: 'only' })
    expect(parseSseBlock('event: ping\n')).toBeNull()
  })
})

describe('streamRequest / chatStream', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
    vi.restoreAllMocks()
  })

  function sseResponse(chunks: string[], status = 200): Response {
    const encoder = new TextEncoder()
    let i = 0
    const stream = new ReadableStream<Uint8Array>({
      pull(controller) {
        if (i >= chunks.length) {
          controller.close()
          return
        }
        controller.enqueue(encoder.encode(chunks[i++]))
      },
    })
    return new Response(stream, {
      status,
      headers: { 'Content-Type': 'text/event-stream' },
    })
  }

  it('streamRequest dispatches token and done events', async () => {
    vi.stubGlobal(
      'fetch',
      vi
        .fn()
        .mockResolvedValue(
          sseResponse([
            'event: token\ndata: {"text":"Hi"}\n\n',
            'event: done\ndata: {"reply":"Hi","metadata":{},"activity":[],"ui":{}}\n\n',
          ]),
        ),
    )
    const events: Array<{ event: string; data: unknown }> = []
    await streamRequest({
      path: '/v1/chat',
      body: { stream: true },
      client: new HttpClient({ retries: 1 }),
      onEvent: (event, data) => events.push({ event, data }),
    })
    expect(events.map((e) => e.event)).toEqual(['token', 'done'])
    expect(events[0]?.data).toEqual({ text: 'Hi' })
  })

  it('chatStream aggregates tokens and returns Zod-validated done payload', async () => {
    vi.stubGlobal(
      'fetch',
      vi
        .fn()
        .mockResolvedValue(
          sseResponse([
            'event: token\ndata: {"text":"A"}\n\n',
            'event: token\ndata: {"text":"B"}\n\n',
            'event: done\ndata: {"reply":"AB","metadata":{},"activity":[],"ui":{}}\n\n',
          ]),
        ),
    )
    const tokens: string[] = []
    const result = await chatStream('s1', 'ola', (t) => tokens.push(t), {
      client: new HttpClient({ retries: 1 }),
    })
    expect(tokens).toEqual(['A', 'B'])
    expect(result.reply).toBe('AB')
  })

  it('chatStream throws HttpError on non-OK response', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response('boom', { status: 502 })))
    await expect(
      chatStream('s1', 'x', () => undefined, { client: new HttpClient({ retries: 1 }) }),
    ).rejects.toBeInstanceOf(HttpError)
  })

  it('chatStream throws ValidationError when done payload is invalid', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(sseResponse(['event: done\ndata: {"metadata":{}}\n\n'])),
    )
    await expect(
      chatStream('s1', 'x', () => undefined, { client: new HttpClient({ retries: 1 }) }),
    ).rejects.toBeInstanceOf(ValidationError)
  })

  it('chatStream throws on event:error', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(sseResponse(['event: error\ndata: {"error":"LLM down"}\n\n'])),
    )
    await expect(
      chatStream('s1', 'x', () => undefined, { client: new HttpClient({ retries: 1 }) }),
    ).rejects.toThrow('LLM down')
  })
})
