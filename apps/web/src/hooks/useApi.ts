import { useCallback, useEffect, useRef, useState, type DependencyList } from 'react'
import { reportApiError } from '@/api/report'
import { toUserMessage } from '@/api/errors'

export type UseApiOptions = {
  /** When false, skip fetch. Default true. */
  enabled?: boolean
  /** Re-run when these change (like useEffect deps). */
  deps?: DependencyList
  /** Surface final error via ErrorNotice. Default false. */
  notifyOnError?: boolean
}

export type UseApiResult<T> = {
  data: T | null
  error: Error | null
  loading: boolean
  refetch: () => Promise<void>
}

/**
 * Lightweight data-fetch hook for panel-level API calls.
 * Prefer validated helpers from `api/client` / `api/endpoints` and pass `signal`:
 * `useApi((signal) => fetchFinanceSummary(y, m, { signal }), { deps: [y, m] })`
 */
export function useApi<T>(
  fetcher: (signal: AbortSignal) => Promise<T>,
  options: UseApiOptions = {},
): UseApiResult<T> {
  const { enabled = true, deps = [], notifyOnError = false } = options
  const [data, setData] = useState<T | null>(null)
  const [error, setError] = useState<Error | null>(null)
  const [loading, setLoading] = useState(false)
  const fetcherRef = useRef(fetcher)
  fetcherRef.current = fetcher

  const run = useCallback(async () => {
    if (!enabled) return
    const ac = new AbortController()
    setLoading(true)
    setError(null)
    try {
      const result = await fetcherRef.current(ac.signal)
      if (ac.signal.aborted) return
      setData(result)
    } catch (err) {
      if (ac.signal.aborted) return
      const asError = err instanceof Error ? err : new Error(toUserMessage(err))
      setError(asError)
      if (notifyOnError) reportApiError(err)
    } finally {
      if (!ac.signal.aborted) setLoading(false)
    }
  }, [enabled, notifyOnError])

  useEffect(() => {
    if (!enabled) return
    const ac = new AbortController()
    let cancelled = false
    setLoading(true)
    setError(null)

    void (async () => {
      try {
        const result = await fetcherRef.current(ac.signal)
        if (cancelled || ac.signal.aborted) return
        setData(result)
      } catch (err) {
        if (cancelled || ac.signal.aborted) return
        const asError = err instanceof Error ? err : new Error(toUserMessage(err))
        setError(asError)
        if (notifyOnError) reportApiError(err)
      } finally {
        if (!cancelled && !ac.signal.aborted) setLoading(false)
      }
    })()

    return () => {
      cancelled = true
      ac.abort()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps -- deps owned by caller
  }, [enabled, notifyOnError, ...deps])

  return { data, error, loading, refetch: run }
}
