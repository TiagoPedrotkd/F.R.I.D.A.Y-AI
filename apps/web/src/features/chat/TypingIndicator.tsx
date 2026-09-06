export function TypingIndicator({ label }: { label: string }) {
  return (
    <div
      className="mr-auto flex max-w-[90%] items-center gap-3 border border-cyan/25 bg-cyan/5 px-3.5 py-2.5"
      style={{
        clipPath:
          'polygon(0 0, calc(100% - 8px) 0, 100% 8px, 100% 100%, 8px 100%, 0 calc(100% - 8px))',
      }}
      aria-label={label}
    >
      <span className="hud-typing" aria-hidden>
        <span />
        <span />
        <span />
      </span>
      <span className="font-display text-[11px] uppercase tracking-[0.28em] text-cyan/80">
        {label}
      </span>
    </div>
  )
}
