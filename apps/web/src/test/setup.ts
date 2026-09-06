import '@testing-library/jest-dom/vitest'
import { cleanup } from '@testing-library/react'
import { afterEach, vi } from 'vitest'

afterEach(() => {
  cleanup()
  vi.restoreAllMocks()
  vi.unstubAllGlobals()
})

/** jsdom may lack AbortSignal.timeout — provide a minimal polyfill for API client. */
if (typeof AbortSignal !== 'undefined' && typeof AbortSignal.timeout !== 'function') {
  AbortSignal.timeout = (ms: number) => {
    const ac = new AbortController()
    setTimeout(() => ac.abort(new DOMException('TimeoutError', 'TimeoutError')), ms)
    return ac.signal
  }
}

/** jsdom often lacks a working scrollIntoView (chat auto-scroll). */
Element.prototype.scrollIntoView = vi.fn()
