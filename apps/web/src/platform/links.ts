/** Open URLs — browser today; Tauri shell plugin when inside desktop. */

declare global {
  interface Window {
    __TAURI_INTERNALS__?: unknown
  }
}

export function isTauriRuntime(): boolean {
  return typeof window !== 'undefined' && Boolean(window.__TAURI_INTERNALS__)
}

export async function openExternal(url: string): Promise<void> {
  if (isTauriRuntime()) {
    try {
      const { open } = await import('@tauri-apps/plugin-shell')
      await open(url)
      return
    } catch {
      /* fall through */
    }
  }
  const a = document.createElement('a')
  a.href = url
  a.target = '_blank'
  a.rel = 'noopener noreferrer'
  a.style.display = 'none'
  document.body.appendChild(a)
  a.click()
  a.remove()
}

export function openMonitorPath(path: string, apiBase: string): void {
  const base = apiBase || (typeof window !== 'undefined' ? window.location.origin : '')
  const url = path.startsWith('http')
    ? path
    : `${base}${path.startsWith('/') ? path : `/${path}`}`
  void openExternal(url)
}
