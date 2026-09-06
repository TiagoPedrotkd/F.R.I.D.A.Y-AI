import type { HTMLAttributes, ReactNode } from 'react'

export type HoloPanelProps = {
  label?: string
  children?: ReactNode
  className?: string
} & Omit<HTMLAttributes<HTMLElement>, 'children'>

/** Lightweight holographic panel chrome (label + frame). No store/API. */
export function HoloPanel({ label, children, className = '', ...rest }: HoloPanelProps) {
  return (
    <section className={`holo holo-frame p-4 ${className}`.trim()} {...rest}>
      {label ? <p className="holo-label mb-2">{label}</p> : null}
      {typeof children === 'string' ? (
        <p className="text-sm text-[var(--text-primary)]">{children}</p>
      ) : (
        children
      )}
    </section>
  )
}
