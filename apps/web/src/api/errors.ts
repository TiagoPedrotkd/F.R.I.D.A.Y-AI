/** Typed API / transport errors for FRIDAY web client. */

export type ApiErrorContext = Record<string, unknown>

export class ApiError extends Error {
  readonly code: string
  readonly status?: number
  readonly cause?: unknown
  readonly retryable: boolean
  readonly context?: ApiErrorContext

  constructor(
    message: string,
    opts: {
      code: string
      status?: number
      cause?: unknown
      retryable?: boolean
      context?: ApiErrorContext
    },
  ) {
    super(message)
    this.name = 'ApiError'
    this.code = opts.code
    this.status = opts.status
    this.cause = opts.cause
    this.retryable = opts.retryable ?? false
    this.context = opts.context
  }
}

export class HttpError extends ApiError {
  readonly bodyText: string

  constructor(
    status: number,
    bodyText: string,
    opts?: { context?: ApiErrorContext; cause?: unknown },
  ) {
    const retryable = status === 408 || status === 429 || status >= 500
    super(bodyText || `HTTP ${status}`, {
      code: 'HTTP_ERROR',
      status,
      retryable,
      cause: opts?.cause,
      context: opts?.context,
    })
    this.name = 'HttpError'
    this.bodyText = bodyText
  }
}

export class NetworkError extends ApiError {
  constructor(message: string, opts?: { cause?: unknown; context?: ApiErrorContext }) {
    super(message || 'Falha de rede', {
      code: 'NETWORK_ERROR',
      retryable: true,
      cause: opts?.cause,
      context: opts?.context,
    })
    this.name = 'NetworkError'
  }
}

export class ValidationError extends ApiError {
  readonly issues: unknown

  constructor(message: string, issues: unknown, opts?: { context?: ApiErrorContext }) {
    super(message, {
      code: 'VALIDATION_ERROR',
      retryable: false,
      context: { ...opts?.context, issues },
    })
    this.name = 'ValidationError'
    this.issues = issues
  }
}

export function isApiError(err: unknown): err is ApiError {
  return err instanceof ApiError
}

export function isRetryable(err: unknown): boolean {
  if (isApiError(err)) return err.retryable
  if (err instanceof TypeError) return true
  if (err instanceof DOMException && err.name === 'AbortError') return false
  if (err instanceof DOMException && err.name === 'TimeoutError') return true
  return false
}

/** Short PT message for UI — no stack dumps. */
export function toUserMessage(err: unknown): string {
  if (err instanceof ValidationError) {
    return 'Resposta inválida do servidor. Tenta novamente.'
  }
  if (err instanceof NetworkError) {
    return 'Sem ligação ao servidor. Verifica a rede ou se a API está a correr.'
  }
  if (err instanceof HttpError) {
    if (err.status === 401 || err.status === 403) return 'Sem permissão para esta operação.'
    if (err.status === 404) return 'Recurso não encontrado.'
    if (err.status === 429) return 'Demasiados pedidos. Aguarda um momento.'
    if (err.status && err.status >= 500) return 'Servidor indisponível. Tenta novamente.'
    const trimmed = err.bodyText?.trim()
    if (trimmed && trimmed.length < 160 && !trimmed.startsWith('{')) return trimmed
    return `Erro HTTP ${err.status ?? ''}`.trim()
  }
  if (err instanceof ApiError) return err.message
  if (err instanceof Error) {
    if (err.name === 'TimeoutError' || err.message.includes('Timeout')) {
      return 'API sem resposta (timeout).'
    }
    return err.message || 'Erro inesperado.'
  }
  return 'Erro inesperado.'
}
