/**
 * Typed design tokens for FRIDAY HUD.
 * Runtime source of truth: `tokens.css` CSS variables.
 * Hex values below are the **dark** reference palette for docs/Storybook.
 */

export type ThemeMode = 'dark' | 'light'

export type ThemeFlags = {
  mode: ThemeMode
  highContrast: boolean
  reducedMotion: boolean
}

/** CSS custom property names used by tokens.css / Tailwind. */
export type CssVarName =
  | '--color-night-950'
  | '--color-night-900'
  | '--color-night-800'
  | '--color-night-700'
  | '--color-cyan'
  | '--color-cyan-dim'
  | '--color-cyan-soft'
  | '--color-electric'
  | '--color-amber'
  | '--color-danger'
  | '--glass-bg'
  | '--glass-border'
  | '--text-primary'
  | '--text-muted'
  | '--motion'
  | '--hud-line'
  | '--bloom'
  | '--page-bg'

export const colors = {
  night: {
    950: { css: '--color-night-950' as const, dark: '#000208' },
    900: { css: '--color-night-900' as const, dark: '#040a14' },
    800: { css: '--color-night-800' as const, dark: '#0a1222' },
    700: { css: '--color-night-700' as const, dark: '#122033' },
  },
  cyan: { css: '--color-cyan' as const, dark: '#5cefff' },
  cyanDim: { css: '--color-cyan-dim' as const, dark: '#1a8fa8' },
  cyanSoft: { css: '--color-cyan-soft' as const, dark: 'rgba(92, 239, 255, 0.1)' },
  electric: { css: '--color-electric' as const, dark: '#4aa3ff' },
  amber: { css: '--color-amber' as const, dark: '#ffb020' },
  danger: { css: '--color-danger' as const, dark: '#ff4d6a' },
  textPrimary: { css: '--text-primary' as const, dark: '#e8fbff' },
  textMuted: { css: '--text-muted' as const, dark: '#6eb8c9' },
  glassBg: { css: '--glass-bg' as const, dark: 'rgba(4, 12, 28, 0.28)' },
  glassBorder: { css: '--glass-border' as const, dark: 'rgba(92, 239, 255, 0.35)' },
  pageBg: { css: '--page-bg' as const, dark: '#000208' },
} as const

/** Tailwind spacing scale commonly used in HUD layouts (rem). */
export const spacing = {
  1: '0.25rem',
  2: '0.5rem',
  3: '0.75rem',
  4: '1rem',
  5: '1.25rem',
  6: '1.5rem',
  8: '2rem',
} as const

export const typography = {
  fontFamily: {
    display: 'Rajdhani, Outfit, system-ui, sans-serif',
    body: '"Source Sans 3", system-ui, sans-serif',
  },
  tracking: {
    holoLabel: '0.35em',
    display: '0.35em',
    button: '0.14em',
  },
} as const

export const motion = {
  css: '--motion' as const,
  defaultMs: 320,
  reducedMs: 0,
  note: 'Set --motion to 0ms via prefers-reduced-motion or .reduce-motion',
} as const

export const shadows = {
  bloom: { css: '--bloom' as const, dark: '0 0 24px rgba(92, 239, 255, 0.45)' },
  glass: '0 8px 32px rgba(0, 0, 0, 0.45)',
  glow: '0 0 28px rgba(61, 227, 255, 0.35)',
} as const

export const themes = {
  modes: ['dark', 'light'] as const satisfies readonly ThemeMode[],
  flags: ['highContrast', 'reducedMotion'] as const,
} as const

/** Hud button class variants (CSS in tokens.css). */
export const hudButtonVariants = {
  default: 'hud-btn',
  primary: 'hud-btn hud-btn-primary',
  danger: 'hud-btn hud-btn-danger',
} as const

export type HudButtonVariant = keyof typeof hudButtonVariants

export function cssVar(name: CssVarName): string {
  return `var(${name})`
}

export type ApplyThemeOptions = Partial<ThemeFlags>

/** Apply theme attributes on `<html>` (matches store applyPrefsDom). */
export function applyTheme(opts: ApplyThemeOptions = {}): void {
  const root = document.documentElement
  const mode = opts.mode ?? 'dark'
  if (mode === 'light') {
    root.dataset.theme = 'light'
  } else {
    delete root.dataset.theme
  }
  root.classList.toggle('high-contrast', Boolean(opts.highContrast))
  root.classList.toggle('reduce-motion', Boolean(opts.reducedMotion))
  root.style.colorScheme = mode === 'light' ? 'light' : 'dark'
}

export const system = {
  colors,
  spacing,
  typography,
  motion,
  shadows,
  themes,
  hudButtonVariants,
  cssVar,
  applyTheme,
} as const

export default system
