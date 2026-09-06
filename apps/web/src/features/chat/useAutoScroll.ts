import { useEffect, useRef, type DependencyList, type RefObject } from 'react'

/** Scrolls an end sentinel into view when `deps` change. */
export function useAutoScroll(deps: DependencyList): RefObject<HTMLDivElement> {
  const endRef = useRef<HTMLDivElement>(null!)
  useEffect(() => {
    const el = endRef.current
    if (el && typeof el.scrollIntoView === 'function') {
      el.scrollIntoView({ behavior: 'smooth' })
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps -- caller owns the dependency list
  }, deps)
  return endRef
}
