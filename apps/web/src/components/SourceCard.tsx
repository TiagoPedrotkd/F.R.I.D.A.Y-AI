import type { SourceItem } from '../api/client'
import { openExternal } from '../platform/links'

function kindLabel(kind?: string | null): string {
  switch (kind) {
    case 'document':
      return 'Docs (RAG)'
    case 'memory':
      return 'Memória pessoal'
    case 'web':
    case 'research':
      return 'Web'
    case 'news':
    case 'finance':
    case 'briefing':
      return 'Notícias'
    default:
      return 'Fonte'
  }
}

function kindClass(kind?: string | null): string {
  switch (kind) {
    case 'document':
      return 'border-electric/40 text-electric'
    case 'memory':
      return 'border-amber/45 text-amber'
    case 'web':
    case 'research':
      return 'border-cyan/45 text-cyan'
    default:
      return 'border-cyan/25 text-[var(--text-muted)]'
  }
}

export function SourceCard({ source, demo }: { source: SourceItem; demo?: boolean }) {
  return (
    <article className="border border-cyan/20 bg-[var(--glass-bg)] p-3 text-sm">
      <div className="mb-1 flex flex-wrap items-center gap-2">
        <span
          className={`font-display text-[9px] font-semibold uppercase tracking-[0.18em] border px-1.5 py-0.5 ${kindClass(source.kind)}`}
        >
          {kindLabel(source.kind)}
        </span>
        {demo && (
          <span className="font-display text-[10px] font-semibold uppercase tracking-wider text-amber">
            Demo
          </span>
        )}
      </div>
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
