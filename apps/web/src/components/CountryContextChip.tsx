const LABELS: Record<string, string> = {
  WW: 'Mundial',
  PT: 'Portugal',
  ES: 'Espanha',
  FR: 'França',
  DE: 'Alemanha',
  GB: 'Reino Unido',
  US: 'EUA',
  BR: 'Brasil',
  JP: 'Japão',
}

export function CountryContextChip({ country }: { country: string | null }) {
  if (!country) return null
  const label = LABELS[country.toUpperCase()] ?? country
  return (
    <div
      className="inline-flex items-center gap-2 border border-cyan/35 bg-cyan/10 px-3 py-1.5"
      data-testid="country-chip"
      style={{ clipPath: 'polygon(6px 0, 100% 0, 100% calc(100% - 6px), calc(100% - 6px) 100%, 0 100%, 0 6px)' }}
    >
      <span
        className="h-2 w-2 rounded-full bg-cyan"
        style={{ boxShadow: '0 0 8px var(--color-cyan)' }}
        aria-hidden
      />
      <span className="font-display text-[10px] tracking-widest text-[var(--text-muted)]">CTX</span>
      <strong className="font-display text-sm font-medium tracking-wide text-cyan">{label}</strong>
    </div>
  )
}
