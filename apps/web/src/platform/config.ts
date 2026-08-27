/** Single source for API base URL (Tauri-ready). */
export function getAgentApiBase(): string {
  const env = import.meta.env.VITE_AGENT_API_BASE as string | undefined
  if (env && env.trim()) return env.replace(/\/$/, '')
  // Empty = same origin (Vite proxy in dev)
  return ''
}

export function apiUrl(path: string): string {
  const base = getAgentApiBase()
  const p = path.startsWith('/') ? path : `/${path}`
  return `${base}${p}`
}
