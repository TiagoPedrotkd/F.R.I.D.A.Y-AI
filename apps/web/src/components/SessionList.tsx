import { useEffect, useState } from 'react'
import * as api from '../api/client'
import { useAppStore } from '../state/store'

type SessionRow = {
  id: string
  updated_at?: number
  message_count?: number
  preview?: string
}

export function SessionList() {
  const restoreSession = useAppStore((s) => s.restoreSession)
  const sessionId = useAppStore((s) => s.sessionId)
  const [rows, setRows] = useState<SessionRow[]>([])

  useEffect(() => {
    void api
      .listSessions()
      .then((r) => setRows(r.sessions || []))
      .catch(() => setRows([]))
  }, [sessionId])

  if (!rows.length) {
    return <p className="text-xs text-[var(--text-muted)]">Sem sessões guardadas.</p>
  }

  return (
    <ul className="max-h-40 space-y-1 overflow-y-auto text-xs">
      {rows.map((s) => (
        <li key={s.id}>
          <button
            type="button"
            className={`w-full border px-2 py-1.5 text-left ${
              s.id === sessionId
                ? 'border-cyan/50 bg-cyan/10 text-cyan'
                : 'border-cyan/15 text-[var(--text-muted)] hover:border-cyan/40'
            }`}
            onClick={() => void restoreSession(s.id)}
            title={s.id}
          >
            <span className="block truncate font-display tracking-wide">
              {(s.preview || s.id).slice(0, 48)}
            </span>
            <span className="opacity-70">
              {s.message_count ?? 0} msgs
              {s.updated_at
                ? ` · ${new Date(s.updated_at * 1000).toLocaleString()}`
                : ''}
            </span>
          </button>
        </li>
      ))}
    </ul>
  )
}
