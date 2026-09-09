import { afterEach, describe, expect, it, vi } from 'vitest'
import { ValidationError } from '../errors'
import {
  confirm,
  createSession,
  fetchAlerts,
  fetchPrefs,
  getSession,
  listSessions,
  savePrefs,
  sendFeedback,
} from '../endpoints'
import { HttpClient } from '../http-client'

describe('hot-path endpoints', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
    vi.restoreAllMocks()
  })

  function stubJson(body: unknown, status = 200) {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify(body), {
          status,
          headers: { 'Content-Type': 'application/json' },
        }),
      ),
    )
  }

  it('createSession / listSessions / getSession', async () => {
    stubJson({ id: 's1' })
    await expect(createSession()).resolves.toEqual({ id: 's1' })

    stubJson({ sessions: [{ id: 's1', preview: 'oi' }] })
    const listed = await listSessions()
    expect(listed.sessions).toHaveLength(1)

    stubJson({
      id: 's1',
      messages: [{ role: 'user', content: 'oi' }],
    })
    const sess = await getSession({ sessionId: 's1' })
    expect(sess.messages[0]?.content).toBe('oi')
  })

  it('fetchPrefs / savePrefs', async () => {
    stubJson({ prefs: { theme: 'dark' }, prompt_version: 'v6' })
    const prefs = await fetchPrefs()
    expect(prefs.prefs.theme).toBe('dark')

    stubJson({ prefs: { theme: 'light' } })
    const saved = await savePrefs({ patch: { theme: 'light' } })
    expect(saved.prefs.theme).toBe('light')
  })

  it('confirm / sendFeedback / fetchAlerts', async () => {
    stubJson({ reply: 'feito', decision: 'confirm' })
    await expect(confirm({ sessionId: 's1', decision: 'confirm' })).resolves.toMatchObject({
      decision: 'confirm',
    })

    stubJson({ ok: true })
    await expect(sendFeedback({ session_id: 's1', rating: 'up' })).resolves.toEqual({ ok: true })

    stubJson({
      alerts: [{ severity: 'info', kind: 'calendar', message: 'reuniao' }],
      context_time: '2026-09-09T22:00:00Z',
    })
    const alerts = await fetchAlerts()
    expect(alerts.alerts[0]?.kind).toBe('calendar')
  })

  it('rejects invalid createSession payload', async () => {
    stubJson({ nope: true })
    const client = new HttpClient({ retries: 1 })
    await expect(createSession({ client })).rejects.toBeInstanceOf(ValidationError)
  })
})
