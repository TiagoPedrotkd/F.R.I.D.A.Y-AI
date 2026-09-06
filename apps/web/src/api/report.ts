import { isApiError, toUserMessage } from './errors'

export type ReportContext = Record<string, unknown>

/**
 * Log + surface error via store.error (ErrorNotice).
 * Dynamic store import avoids circular deps (store → client → http → report).
 */
export function reportApiError(err: unknown, context?: ReportContext): void {
  const message = toUserMessage(err)
  const payload = {
    message,
    code: isApiError(err) ? err.code : undefined,
    status: isApiError(err) ? err.status : undefined,
    retryable: isApiError(err) ? err.retryable : undefined,
    context,
    error: err,
  }
  console.error('[friday/api]', payload)

  if (typeof globalThis.reportError === 'function' && err instanceof Error) {
    try {
      globalThis.reportError(err)
    } catch {
      /* ignore */
    }
  }

  void import('@/state/store')
    .then(({ useAppStore }) => {
      useAppStore.setState({ error: message })
    })
    .catch(() => {
      /* store unavailable in isolated tests */
    })
}
