import type { SourceItem } from '../api/client'
import { openExternal } from '../platform/links'

export function SourceCard({ source, demo }: { source: SourceItem; demo?: boolean }) {
  return (
    <article className="border border-cyan/20 bg-night-950/50 p-3 text-sm">
      {demo && (
        <span className="mb-1 block font-display text-[10px] font-semibold uppercase tracking-wider text-amber">
          Demo
        </span>
      )}
      <h3 className="font-medium leading-snug text-[var(--text-primary)]">{source.title}</h3>
      {(source.source || source.date) && (
        <p className="mt-0.5 text-xs text-[var(--text-muted)]">
          {[source.source, source.date].filter(Boolean).join(' · ')}
        </p>
      )}
      {source.snippet && (
        <p className="mt-1 line-clamp-2 text-xs text-[var(--text-muted)]">{source.snippet}</p>
      )}
      {source.url && (
        <button
          type="button"
          className="mt-2 font-display text-[10px] tracking-widest text-cyan hover:underline"
          onClick={() => void openExternal(source.url)}
        >
          Abrir fonte →
        </button>
      )}
    </article>
  )
}
