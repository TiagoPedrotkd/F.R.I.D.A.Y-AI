import { useAppStore } from '../state/store'

export function ErrorNotice() {
  const error = useAppStore((s) => s.error)
  if (!error) return null
  return (
    <div
      className="mx-4 mt-3 rounded-lg border border-danger/40 bg-danger/10 px-3 py-2 text-sm text-danger md:mx-6"
      role="alert"
    >
      {error}
    </div>
  )
}
