import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { ErrorBoundary } from './ErrorBoundary'

describe('ErrorBoundary', () => {
  it('shows fallback and resets', () => {
    const spy = vi.spyOn(console, 'error').mockImplementation(() => {})
    let shouldThrow = true
    function Boom() {
      if (shouldThrow) throw new Error('explode')
      return <p>ok</p>
    }

    render(
      <ErrorBoundary>
        <Boom />
      </ErrorBoundary>,
    )
    expect(screen.getByTestId('error-boundary-fallback')).toBeInTheDocument()
    expect(screen.getByText(/Algo falhou/i)).toBeInTheDocument()

    shouldThrow = false
    fireEvent.click(screen.getByRole('button', { name: /Tentar de novo/i }))
    expect(screen.getByText('ok')).toBeInTheDocument()
    spy.mockRestore()
  })

  it('supports custom fallback render', () => {
    const spy = vi.spyOn(console, 'error').mockImplementation(() => {})
    function Boom(): never {
      throw new Error('explode')
    }
    render(
      <ErrorBoundary
        fallback={(err, reset) => (
          <div>
            <span>{err.message}</span>
            <button type="button" onClick={reset}>
              reset
            </button>
          </div>
        )}
      >
        <Boom />
      </ErrorBoundary>,
    )
    expect(screen.getByText('explode')).toBeInTheDocument()
    spy.mockRestore()
  })
})
