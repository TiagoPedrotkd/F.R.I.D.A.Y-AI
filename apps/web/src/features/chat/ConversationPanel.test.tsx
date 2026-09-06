import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { ConversationPanel } from './ConversationPanel'
import { makeMessage } from '@/test/fixtures'
import { resetAppStore } from '@/test/mockApi'

describe('ConversationPanel', () => {
  it('shows empty state when idle with no messages', () => {
    // Arrange
    resetAppStore({ state: 'idle', messages: [] })

    // Act
    render(<ConversationPanel />)

    // Assert
    expect(screen.getByText(/Aguardando instruções/i)).toBeInTheDocument()
    expect(screen.getByLabelText('Conversa')).toBeInTheDocument()
  })

  it('renders messages and hides empty state', () => {
    // Arrange
    resetAppStore({
      state: 'idle',
      messages: [makeMessage({ id: 'u1', role: 'user', text: 'Olá Friday' })],
    })

    // Act
    render(<ConversationPanel />)

    // Assert
    expect(screen.queryByText(/Aguardando instruções/i)).not.toBeInTheDocument()
    expect(screen.getByText('Olá Friday')).toBeInTheDocument()
    expect(screen.getByText('01')).toBeInTheDocument()
  })

  it('shows typing indicator while busy', () => {
    // Arrange
    resetAppStore({
      state: 'thinking',
      messages: [makeMessage({ id: 'u1', role: 'user', text: 'Que horas são?' })],
    })

    // Act
    render(<ConversationPanel />)

    // Assert
    expect(screen.getByLabelText(/pensar/i)).toBeInTheDocument()
    expect(screen.queryByText(/Aguardando instruções/i)).not.toBeInTheDocument()
  })
})
