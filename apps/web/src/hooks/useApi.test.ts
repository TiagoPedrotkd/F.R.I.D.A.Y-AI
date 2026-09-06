import { renderHook, waitFor } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import * as report from '@/api/report'
import { useApi } from './useApi'

describe('useApi', () => {
  it('loads data', async () => {
    const { result } = renderHook(() => useApi(async () => ({ value: 1 }), { deps: [] }))
    await waitFor(() => expect(result.current.loading).toBe(false))
    expect(result.current.data).toEqual({ value: 1 })
    expect(result.current.error).toBeNull()
  })

  it('surfaces errors', async () => {
    const { result } = renderHook(() =>
      useApi(
        async () => {
          throw new Error('fail')
        },
        { deps: [] },
      ),
    )
    await waitFor(() => expect(result.current.loading).toBe(false))
    expect(result.current.error?.message).toBe('fail')
    expect(result.current.data).toBeNull()
  })

  it('notifies on error when enabled', async () => {
    const spy = vi.spyOn(report, 'reportApiError').mockImplementation(() => {})
    const { result } = renderHook(() =>
      useApi(
        async () => {
          throw new Error('notify-me')
        },
        { deps: [], notifyOnError: true },
      ),
    )
    await waitFor(() => expect(result.current.error?.message).toBe('notify-me'))
    expect(spy).toHaveBeenCalled()
    spy.mockRestore()
  })
})
