const PREFIX = 'friday.prefs.'

export function getItem(key: string): string | null {
  try {
    return localStorage.getItem(PREFIX + key)
  } catch {
    return null
  }
}

export function setItem(key: string, value: string): void {
  try {
    localStorage.setItem(PREFIX + key, value)
  } catch {
    /* ignore quota */
  }
}

export function getJson<T>(key: string, fallback: T): T {
  const raw = getItem(key)
  if (!raw) return fallback
  try {
    return JSON.parse(raw) as T
  } catch {
    return fallback
  }
}

export function setJson(key: string, value: unknown): void {
  setItem(key, JSON.stringify(value))
}
