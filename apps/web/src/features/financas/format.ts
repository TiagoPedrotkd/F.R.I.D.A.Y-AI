export function fmtMoney(v: number | null | undefined, currency = 'EUR'): string {
  if (v == null || Number.isNaN(v)) return '—'
  return `${v.toFixed(2)} ${currency}`
}

export type LedgerKind = 'expense' | 'income'

/**
 * Signed ledger amount from UI input.
 * expense: `100` → `-100`; income: `100` → `+100`.
 */
export function toLedgerAmount(raw: number, kind: LedgerKind): number {
  if (!Number.isFinite(raw) || raw === 0) return raw
  const abs = Math.abs(raw)
  return kind === 'income' ? abs : -abs
}

/** @deprecated prefer toLedgerAmount(raw, 'expense') */
export function toExpenseAmount(raw: number): number {
  return toLedgerAmount(raw, 'expense')
}
