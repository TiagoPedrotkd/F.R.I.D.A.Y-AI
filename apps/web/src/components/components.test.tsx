import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { MessageBubble } from '../components/MessageBubble'
import { DemoBanner } from '../components/DemoBanner'
import { CountryContextChip } from '../components/CountryContextChip'
import { ConfirmationDialog } from '../components/ConfirmationDialog'
import { AppShell } from '../components/AppShell'
import { DEMO_FIXTURES } from '../demo/fixtures'
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

describe('Demo fixtures (LM off path)', () => {
  it('labels chat and news with [DEMO]', () => {
    expect(DEMO_FIXTURES.chat.reply).toMatch(/\[DEMO\]/)
    expect(DEMO_FIXTURES.news.reply).toMatch(/\[DEMO\]/)
    expect(DEMO_FIXTURES.banner).toMatch(/demonstração/i)
  })
})

describe('Mobile drawer (Data panel)', () => {
  it('toggles sidebar content on narrow header control', () => {
    Element.prototype.scrollIntoView = vi.fn()
    useAppStore.setState({
      sidebarOpen: false,
      settingsOpen: false,
      bootstrap: vi.fn(async () => undefined),
      prefs: { ...useAppStore.getState().prefs, reducedMotion: true },
    })
    render(<AppShell />)
    const toggle = screen.getByRole('button', { name: 'Data' })
    fireEvent.click(toggle)
    expect(useAppStore.getState().sidebarOpen).toBe(true)
    expect(screen.getByRole('button', { name: 'Fechar' })).toBeInTheDocument()
    expect(screen.getAllByText(/Contexto/i).length).toBeGreaterThan(0)
  })
})
