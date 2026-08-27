/** Open URLs — web today, Tauri shell tomorrow. */

export async function openExternal(url: string): Promise<void> {
  // Prefer <a> click: more reliable than window.open(..., 'noopener') which
  // some browsers treat as windowFeatures and silently fail / block.
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
  const base = apiBase || window.location.origin
  const url = path.startsWith('http')
    ? path
    : `${base}${path.startsWith('/') ? path : `/${path}`}`
  void openExternal(url)
}
