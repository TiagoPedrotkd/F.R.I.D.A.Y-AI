import { useEffect, useState, type ReactNode } from 'react'

/** Circular date gauge — top-left HUD module */
export function HudDateGauge({ locale = 'pt-PT' }: { locale?: string }) {
  const [now, setNow] = useState(() => new Date())
  useEffect(() => {
    const id = setInterval(() => setNow(new Date()), 1000)
    return () => clearInterval(id)
  }, [])

  const day = now.getDate()
  const month = now.toLocaleDateString(locale, { month: 'long' })
  const weekday = now.toLocaleDateString(locale, { weekday: 'long' })
  const time = now.toLocaleTimeString(locale, {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  })
  const sec = now.getSeconds()
  const dash = 2 * Math.PI * 54
  const offset = dash * (1 - sec / 60)

  return (
    <div className="relative mx-auto h-[168px] w-[168px]">
      <svg viewBox="0 0 140 140" className="h-full w-full drop-shadow-[0_0_12px_rgba(61,227,255,0.35)]">
        <circle cx="70" cy="70" r="66" fill="none" stroke="rgba(61,227,255,0.2)" strokeWidth="1" />
        <circle
          cx="70"
          cy="70"
          r="54"
          fill="none"
          stroke="rgba(61,227,255,0.25)"
          strokeWidth="6"
          strokeDasharray="4 8"
        />
        <circle
          cx="70"
          cy="70"
          r="54"
          fill="none"
          stroke="#3de3ff"
          strokeWidth="3"
          strokeLinecap="round"
          strokeDasharray={`${dash}`}
          strokeDashoffset={offset}
          transform="rotate(-90 70 70)"
          style={{ filter: 'drop-shadow(0 0 6px #3de3ff)' }}
        />
        <circle cx="70" cy="70" r="42" fill="rgba(3,8,20,0.75)" stroke="rgba(61,227,255,0.45)" strokeWidth="1" />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center text-center">
        <span className="font-display text-[9px] uppercase tracking-[0.25em] text-cyan/70">{weekday}</span>
        <span className="font-display text-3xl font-bold tabular-nums text-cyan" style={{ textShadow: '0 0 14px #3de3ff' }}>
          {day}
        </span>
        <span className="font-display text-[10px] uppercase tracking-widest text-[var(--text-muted)]">{month}</span>
        <span className="mt-0.5 font-display text-[11px] tabular-nums tracking-wider text-cyan/90">{time}</span>
      </div>
    </div>
  )
}

/** Segmented ring meter for API/LM/CORE */
export function HudRingMeter({
  label,
  value,
  ok = true,
}: {
  label: string
  value: number
  ok?: boolean
}) {
  const r = 28
  const c = 2 * Math.PI * r
  const color = ok ? '#3de3ff' : '#ff4d6a'
  const offset = c * (1 - Math.min(100, Math.max(0, value)) / 100)
  return (
    <div className="flex flex-col items-center gap-1">
      <div className="relative h-[72px] w-[72px]">
        <svg viewBox="0 0 72 72" className="h-full w-full">
          <circle cx="36" cy="36" r={r} fill="none" stroke="rgba(61,227,255,0.15)" strokeWidth="5" />
          <circle
            cx="36"
            cy="36"
            r={r}
            fill="none"
            stroke={color}
            strokeWidth="5"
            strokeLinecap="round"
            strokeDasharray={c}
            strokeDashoffset={offset}
            transform="rotate(-90 36 36)"
            style={{ filter: `drop-shadow(0 0 6px ${color})` }}
          />
        </svg>
        <span className="absolute inset-0 flex items-center justify-center font-display text-xs tabular-nums text-cyan">
          {value}%
        </span>
      </div>
      <span className="font-display text-[9px] tracking-[0.2em] text-[var(--text-muted)]">{label}</span>
    </div>
  )
}

/** Day-of-month timeline across the top */
export function HudDayRail() {
  const today = new Date().getDate()
  const days = Array.from({ length: 31 }, (_, i) => i + 1)
  return (
    <div className="hidden overflow-hidden lg:block">
      <div className="flex items-end gap-0.5 px-1">
        {days.map((d) => (
          <span
            key={d}
            className={`min-w-[1.35rem] text-center font-display text-[9px] tabular-nums tracking-wide ${
              d === today
                ? 'bg-cyan/20 px-0.5 text-cyan shadow-[0_0_10px_rgba(61,227,255,0.4)]'
                : 'text-cyan/35'
            }`}
          >
            {String(d).padStart(2, '0')}
          </span>
        ))}
      </div>
    </div>
  )
}

/** Bottom circular dock buttons */
export function HudDock({
  onMic,
  onSend,
  onSettings,
  onMonitor,
  onPanel,
  micActive,
  hasMonitor,
}: {
  onMic: () => void
  onSend: () => void
  onSettings: () => void
  onMonitor?: () => void
  onPanel: () => void
  micActive: boolean
  hasMonitor: boolean
}) {
  const Item = ({
    label,
    onClick,
    active,
    children,
  }: {
    label: string
    onClick: () => void
    active?: boolean
    children: ReactNode
  }) => (
    <button
      type="button"
      title={label}
      aria-label={label}
      onClick={onClick}
      className={`group flex h-14 w-14 flex-col items-center justify-center rounded-full border transition ${
        active
          ? 'border-danger bg-danger/20 text-danger'
          : 'border-cyan/40 bg-cyan/5 text-cyan hover:border-cyan hover:bg-cyan/15 hover:shadow-[0_0_18px_rgba(61,227,255,0.35)]'
      }`}
    >
      {children}
      <span className="mt-0.5 font-display text-[7px] tracking-wider opacity-70">{label}</span>
    </button>
  )

  return (
    <div className="flex flex-wrap items-center justify-center gap-3 py-1">
      <Item label="MIC" onClick={onMic} active={micActive}>
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6">
          <rect x="9" y="2" width="6" height="11" rx="3" />
          <path d="M5 11a7 7 0 0 0 14 0M12 18v4" />
        </svg>
      </Item>
      <Item label="SEND" onClick={onSend}>
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6">
          <path d="M22 2 11 13M22 2l-7 20-4-9-9-4 20-7z" />
        </svg>
      </Item>
      <Item label="PANEL" onClick={onPanel}>
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6">
          <rect x="3" y="3" width="7" height="7" />
          <rect x="14" y="3" width="7" height="7" />
          <rect x="3" y="14" width="7" height="7" />
          <rect x="14" y="14" width="7" height="7" />
        </svg>
      </Item>
      {hasMonitor && onMonitor && (
        <Item label="MAP" onClick={onMonitor}>
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6">
            <circle cx="12" cy="12" r="9" />
            <path d="M3 12h18M12 3a14 14 0 0 1 0 18M12 3a14 14 0 0 0 0 18" />
          </svg>
        </Item>
      )}
      <Item label="CFG" onClick={onSettings}>
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6">
          <circle cx="12" cy="12" r="3" />
          <path d="M12 1v2M12 21v2M4.2 4.2l1.4 1.4M18.4 18.4l1.4 1.4M1 12h2M21 12h2M4.2 19.8l1.4-1.4M18.4 5.6l1.4-1.4" />
        </svg>
      </Item>
    </div>
  )
}

/** Decorative connector SVG behind content */
export function HudConnectors() {
  return (
    <svg
      className="pointer-events-none absolute inset-0 z-0 hidden h-full w-full opacity-40 lg:block"
      aria-hidden
    >
      <defs>
        <linearGradient id="wire" x1="0" y1="0" x2="1" y2="0">
          <stop offset="0%" stopColor="#3de3ff" stopOpacity="0" />
          <stop offset="50%" stopColor="#3de3ff" stopOpacity="0.7" />
          <stop offset="100%" stopColor="#3de3ff" stopOpacity="0" />
        </linearGradient>
      </defs>
      <path d="M 80 120 L 220 120 L 280 200" fill="none" stroke="url(#wire)" strokeWidth="1" />
      <path d="M calc(100% - 80px) 140 L calc(100% - 240px) 140 L calc(100% - 300px) 220" fill="none" stroke="url(#wire)" strokeWidth="1" />
      <path d="M 50% 80 L 50% 140" fill="none" stroke="rgba(61,227,255,0.35)" strokeWidth="1" strokeDasharray="3 6" />
    </svg>
  )
}
