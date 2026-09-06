export function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="border-b border-cyan/10 py-2">
      <p className="text-[10px] uppercase tracking-wide text-[var(--text-muted)]">{label}</p>
      <p className="font-mono text-sm text-cyan">{value}</p>
    </div>
  )
}
