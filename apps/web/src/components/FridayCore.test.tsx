import { act, render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { FridayCore } from './FridayCore'
import { resetAppStore } from '@/test/mockApi'

describe('FridayCore', () => {
  it('exposes thinking state on the core aria-label', () => {
    // Arrange
    resetAppStore({ state: 'thinking' })

    // Act
    render(<FridayCore />)

    // Assert
    expect(screen.getByRole('img', { name: /pensar/i })).toBeInTheDocument()
  })

  it('updates label when store state becomes listening', () => {
    // Arrange
    resetAppStore({ state: 'idle' })
    render(<FridayCore />)
    expect(screen.getByRole('img', { name: /pronta/i })).toBeInTheDocument()

    // Act
    act(() => {
      resetAppStore({ state: 'listening' })
    })

    // Assert
    expect(screen.getByRole('img', { name: /ouvir/i })).toBeInTheDocument()
  })

  it('shows error label in error state', () => {
    // Arrange
    resetAppStore({ state: 'error' })

    // Act
    render(<FridayCore />)

    // Assert
    expect(screen.getByRole('img', { name: /^erro$/i })).toBeInTheDocument()
  })
})
