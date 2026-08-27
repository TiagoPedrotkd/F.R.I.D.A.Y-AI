import { DEMO_FIXTURES } from '../demo/fixtures'

export function DemoBanner() {
  return (
    <div
      className="border-b border-amber/40 bg-amber/90 px-4 py-2 text-center font-display text-xs font-semibold tracking-[0.15em] text-night-950"
      role="status"
      data-testid="demo-banner"
    >
      {DEMO_FIXTURES.banner}
    </div>
  )
}
