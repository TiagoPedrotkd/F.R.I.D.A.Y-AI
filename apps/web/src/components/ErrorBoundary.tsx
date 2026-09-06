import { Component, type ErrorInfo, type ReactNode } from 'react'
import { reportApiError } from '@/api/report'
import { HudButton } from '@/components/ui'

type FallbackRender = (error: Error, reset: () => void) => ReactNode

export type ErrorBoundaryProps = {
  children: ReactNode
  fallback?: ReactNode | FallbackRender
  onError?: (error: Error, info: ErrorInfo) => void
}

type State = {
  error: Error | null
}

function DefaultFallback({ error, reset }: { error: Error; reset: () => void }) {
  return (
    <div
      className="m-4 rounded-lg border border-danger/40 bg-danger/10 px-4 py-6 text-center"
      role="alert"
      data-testid="error-boundary-fallback"
    >
      <p className="font-display text-sm tracking-[0.2em] text-danger">Algo falhou</p>
      <p className="mt-2 text-sm text-[var(--text-muted)]">
        {error.message || 'Erro inesperado na interface.'}
      </p>
      <HudButton className="mt-4" onClick={reset}>
        Tentar de novo
      </HudButton>
    </div>
  )
}

export class ErrorBoundary extends Component<ErrorBoundaryProps, State> {
  state: State = { error: null }

  static getDerivedStateFromError(error: Error): State {
    return { error }
  }

  componentDidCatch(error: Error, info: ErrorInfo): void {
    reportApiError(error, { componentStack: info.componentStack })
    this.props.onError?.(error, info)
  }

  reset = (): void => {
    this.setState({ error: null })
  }

  render(): ReactNode {
    const { error } = this.state
    if (!error) return this.props.children

    const { fallback } = this.props
    if (typeof fallback === 'function') return fallback(error, this.reset)
    if (fallback !== undefined) return fallback
    return <DefaultFallback error={error} reset={this.reset} />
  }
}
