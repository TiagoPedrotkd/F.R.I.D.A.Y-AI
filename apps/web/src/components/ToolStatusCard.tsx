/** Optional card for a single tool step (used in timeline expansions). */
export function ToolStatusCard({
  label,
  status,
}: {
  label: string
  status: string
}) {
  return (
    <div className="glass rounded-lg px-3 py-2 text-sm" data-status={status}>
      <span className="text-[var(--text-primary)]">{label}</span>
      <span className="ml-2 text-xs text-[var(--text-muted)]">{status}</span>
    </div>
  )
}
