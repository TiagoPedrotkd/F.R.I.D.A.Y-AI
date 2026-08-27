import { stateLabel, type FridayState } from '../state/machine'
import { useAppStore } from '../state/store'

const STATE_TINT: Record<FridayState, string> = {
  offline: '#64748b',
  connecting: '#4aa3ff',
  idle: '#5cefff',
  listening: '#9af6ff',
  transcribing: '#4aa3ff',
  thinking: '#4aa3ff',
  tool_calling: '#ffb020',
  awaiting_confirmation: '#ffb020',
  speaking: '#5cefff',
  error: '#ff4d6a',
}

export function FridayCore() {
  const state = useAppStore((s) => s.state)
  const lang = useAppStore((s) => s.prefs.language)
  const reduced = useAppStore((s) => s.prefs.reducedMotion)
  const tint = STATE_TINT[state] ?? STATE_TINT.idle

  return (
    <div className="relative mx-auto w-[min(78vw,420px)]" aria-live="polite">
      <div
        className={`relative aspect-square w-full ${reduced ? '' : 'hud-breathe'}`}
        role="img"
        aria-label={stateLabel(state, lang)}
      >
        <svg viewBox="0 0 400 400" className="h-full w-full" aria-hidden>
          <defs>
            <radialGradient id="reactorCore" cx="50%" cy="50%" r="50%">
              <stop offset="0%" stopColor="#ffffff" stopOpacity="0.95" />
              <stop offset="18%" stopColor={tint} stopOpacity="0.85" />
              <stop offset="45%" stopColor={tint} stopOpacity="0.2" />
              <stop offset="100%" stopColor="transparent" stopOpacity="0" />
            </radialGradient>
            <filter id="softGlow">
              <feGaussianBlur stdDeviation="3.5" result="b" />
              <feMerge>
                <feMergeNode in="b" />
                <feMergeNode in="SourceGraphic" />
              </feMerge>
            </filter>
          </defs>

          <circle cx="200" cy="200" r="190" fill="url(#reactorCore)" opacity="0.55" />

          {/* Outer tick compass */}
          <g opacity="0.55">
            {Array.from({ length: 72 }, (_, i) => {
              const a = (i / 72) * Math.PI * 2 - Math.PI / 2
              const long = i % 6 === 0
              const x1 = 200 + Math.cos(a) * 178
              const y1 = 200 + Math.sin(a) * 178
              const x2 = 200 + Math.cos(a) * (long ? 162 : 170)
              const y2 = 200 + Math.sin(a) * (long ? 162 : 170)
              return (
                <line
                  key={i}
                  x1={x1}
                  y1={y1}
                  x2={x2}
                  y2={y2}
                  stroke={tint}
                  strokeWidth={long ? 1.8 : 0.7}
                />
              )
            })}
          </g>

          <g className={reduced ? '' : 'hud-spin-rev'} style={{ transformOrigin: '200px 200px' }}>
            <circle
              cx="200"
              cy="200"
              r="155"
              fill="none"
              stroke={tint}
              strokeWidth="1.4"
              strokeDasharray="28 16 6 16"
              opacity="0.65"
            />
            <circle cx="200" cy="200" r="148" fill="none" stroke={tint} strokeWidth="0.5" opacity="0.3" />
          </g>

          <g className={reduced ? '' : 'hud-spin'} style={{ transformOrigin: '200px 200px' }}>
            <circle
              cx="200"
              cy="200"
              r="128"
              fill="none"
              stroke={tint}
              strokeWidth="2.4"
              strokeDasharray="56 22"
              opacity="0.9"
            />
            <circle
              cx="200"
              cy="200"
              r="112"
              fill="none"
              stroke={tint}
              strokeWidth="10"
              strokeDasharray="5 11"
              opacity="0.18"
            />
          </g>

          <g className={reduced ? '' : 'hud-spin-fast'} style={{ transformOrigin: '200px 200px' }}>
            <circle
              cx="200"
              cy="200"
              r="95"
              fill="none"
              stroke={tint}
              strokeWidth="5"
              strokeDasharray="80 180"
              strokeLinecap="round"
              opacity="0.95"
              filter="url(#softGlow)"
            />
          </g>

          {/* Arc reactor triangle cluster */}
          <circle cx="200" cy="200" r="58" fill="rgba(0,8,20,0.75)" stroke={tint} strokeWidth="1.5" />
          <circle cx="200" cy="200" r="38" fill="url(#reactorCore)" opacity="0.9" filter="url(#softGlow)" />
          <path
            d="M200 178 L224 218 L176 218 Z"
            fill="none"
            stroke="#e8fbff"
            strokeWidth="2.2"
            opacity="0.95"
            filter="url(#softGlow)"
          />
          <path d="M200 186 L216 212 L184 212 Z" fill={tint} opacity="0.45" />
        </svg>

        <div className="pointer-events-none absolute inset-x-0 bottom-[18%] text-center">
          <p
            className="font-display text-sm font-semibold tracking-[0.45em] text-cyan md:text-base"
            style={{ textShadow: '0 0 16px rgba(92,239,255,0.8)' }}
          >
            F.R.I.D.A.Y.
          </p>
          <p className="mt-1 font-display text-[11px] uppercase tracking-[0.35em] text-[var(--text-muted)]">
            {stateLabel(state, lang)}
          </p>
        </div>
      </div>
    </div>
  )
}
