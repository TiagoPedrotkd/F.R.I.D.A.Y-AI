/** Single source for API base URL (Tauri-ready). */

import { isTauriRuntime } from './links'

export function getAgentApiBase(): string {
  const env = import.meta.env.VITE_AGENT_API_BASE as string | undefined
  if (env && env.trim()) return env.replace(/\/$/, '')
  // Desktop WebView is not same-origin with agent-api
  if (isTauriRuntime()) return 'http://127.0.0.1:8090'
  // Empty = same origin (Vite proxy in browser dev)
  return ''
}

export function apiUrl(path: string): string {
  const base = getAgentApiBase()
  const p = path.startsWith('/') ? path : `/${path}`
  return `${base}${p}`
}
