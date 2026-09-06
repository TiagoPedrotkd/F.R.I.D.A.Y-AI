import { beforeEach, describe, expect, it, vi } from 'vitest'
import { chatReplyOk } from '@/test/fixtures'
import { resetAppStore } from '@/test/mockApi'

vi.mock('@/api/client', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/api/client')>()
  return {
    ...actual,
    chatStream: vi.fn(),
  }
})

import * as api from '@/api/client'
import { useAppStore } from '../store'

describe('store chat integration', () => {
  beforeEach(() => {
    resetAppStore({
      state: 'idle',
      sessionId: 'sess-1',
      messages: [],
      prefs: {
        ...useAppStore.getState().prefs,
        ttsEnabled: false,
        autoplay: false,
        demoMode: false,
      },
      demoForced: false,
    })
    vi.mocked(api.chatStream).mockReset()
  })

  it('sendText streams reply into messages and returns to idle', async () => {
    const reply = chatReplyOk({ reply: 'São quinze horas.' })
    vi.mocked(api.chatStream).mockImplementation(async (_sid, _text, onToken) => {
      onToken('São ')
      onToken('quinze horas.')
      return reply
    })

    await useAppStore.getState().sendText('Que horas são?')

    const { messages, state, error } = useAppStore.getState()
    expect(api.chatStream).toHaveBeenCalledWith('sess-1', 'Que horas são?', expect.any(Function))
    expect(messages.some((m) => m.role === 'user' && m.text === 'Que horas são?')).toBe(true)
    expect(messages.some((m) => m.role === 'assistant' && m.text === 'São quinze horas.')).toBe(
      true,
    )
    expect(state).toBe('idle')
    expect(error).toBeNull()
  })

  it('sendText sets error state when chatStream fails', async () => {
    vi.mocked(api.chatStream).mockRejectedValue(new Error('LM offline'))

    await useAppStore.getState().sendText('ping')

    const { state, error, messages } = useAppStore.getState()
    expect(state).toBe('error')
    expect(error).toMatch(/LM offline/i)
    expect(messages.some((m) => m.role === 'assistant')).toBe(true)
  })
})
