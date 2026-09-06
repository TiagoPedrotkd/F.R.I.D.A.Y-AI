import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { makeMessage } from '@/test/fixtures'
import { resetAppStore } from '@/test/mockApi'
import { MessageBubble } from './MessageBubble'
import { useAppStore } from '@/state/store'

describe('MessageBubble', () => {
  beforeEach(() => {
    resetAppStore({
      messages: [
        makeMessage({ id: 'u1', role: 'user', text: 'Olá' }),
        makeMessage({ id: 'a1', role: 'assistant', text: 'Resposta Friday' }),
      ],
    })
  })

  it('renders user role without feedback controls', () => {
    render(<MessageBubble message={makeMessage({ id: 'u1', role: 'user', text: 'Olá' })} />)
    expect(screen.getByText('VOCÊ')).toBeInTheDocument()
    expect(screen.queryByLabelText('Útil')).not.toBeInTheDocument()
  })

  it('renders assistant feedback and Regenerar on last assistant', async () => {
    const user = userEvent.setup()
    const rate = vi.fn()
    const regen = vi.fn()
    useAppStore.setState({ rateMessage: rate, regenerateLast: regen })

    render(
      <MessageBubble
        message={makeMessage({ id: 'a1', role: 'assistant', text: 'Resposta Friday' })}
      />,
    )

    expect(screen.getByText('F.R.I.D.A.Y.')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Regenerar' })).toBeInTheDocument()
    await user.click(screen.getByLabelText('Útil'))
    expect(rate).toHaveBeenCalledWith('a1', 'up')
    await user.click(screen.getByRole('button', { name: 'Regenerar' }))
    expect(regen).toHaveBeenCalled()
  })

  it('hides Regenerar on non-last assistant', () => {
    resetAppStore({
      messages: [
        makeMessage({ id: 'a1', role: 'assistant', text: 'Antiga' }),
        makeMessage({ id: 'a2', role: 'assistant', text: 'Nova' }),
      ],
    })
    render(<MessageBubble message={makeMessage({ id: 'a1', role: 'assistant', text: 'Antiga' })} />)
    expect(screen.queryByRole('button', { name: 'Regenerar' })).not.toBeInTheDocument()
  })

  it('renders system banner without rating', () => {
    render(<MessageBubble message={makeMessage({ id: 's1', role: 'system', text: 'Modo demo' })} />)
    expect(screen.getByText('SISTEMA')).toBeInTheDocument()
    expect(screen.queryByLabelText('Útil')).not.toBeInTheDocument()
  })
})
