import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { MessageBubble } from '../components/MessageBubble'
import { DemoBanner } from '../components/DemoBanner'
import { CountryContextChip } from '../components/CountryContextChip'
import { ConfirmationDialog } from '../components/ConfirmationDialog'
import { useAppStore } from '../state/store'

describe('MessageBubble', () => {
  it('marks demo messages', () => {
    render(
      <MessageBubble
        message={{ id: '1', role: 'assistant', text: 'Olá', demo: true }}
      />,
    )
    expect(screen.getByText('Demo')).toBeInTheDocument()
    expect(screen.getByText('Olá')).toBeInTheDocument()
  })
})

describe('DemoBanner', () => {
  it('shows demo warning', () => {
    render(<DemoBanner />)
    expect(screen.getByTestId('demo-banner')).toHaveTextContent(/demonstração/i)
  })
})

describe('CountryContextChip', () => {
  it('renders country label', () => {
    render(<CountryContextChip country="PT" />)
    expect(screen.getByTestId('country-chip')).toHaveTextContent('Portugal')
  })

  it('hides when null', () => {
    const { container } = render(<CountryContextChip country={null} />)
    expect(container).toBeEmptyDOMElement()
  })
})

describe('ConfirmationDialog a11y', () => {
  it('exposes alertdialog when pending', () => {
    useAppStore.setState({
      pending: {
        action: 'send_email',
        target: 'a@b.c',
        summary: 'enviar email',
        consequences: 'demo',
      },
    })
    render(<ConfirmationDialog />)
    const dialog = screen.getByRole('alertdialog')
    expect(dialog).toHaveAttribute('aria-modal', 'true')
    expect(screen.getByText(/Enter não confirma/i)).toBeInTheDocument()
  })
})
