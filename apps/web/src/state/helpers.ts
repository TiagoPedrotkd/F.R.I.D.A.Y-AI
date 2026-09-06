import type { Prefs } from '@/demo/fixtures'

export function uid(): string {
  return Math.random().toString(36).slice(2, 10)
}

export function applyPrefsDom(prefs: Prefs): void {
  document.documentElement.classList.toggle('high-contrast', prefs.highContrast)
  document.documentElement.classList.toggle('reduce-motion', prefs.reducedMotion)
  document.documentElement.dataset.theme = prefs.theme || 'dark'
  document.documentElement.style.colorScheme = prefs.theme === 'light' ? 'light' : 'dark'
}
