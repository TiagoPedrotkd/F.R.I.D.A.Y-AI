import { describe, expect, it } from 'vitest'
import { fmtMoney, toExpenseAmount, toLedgerAmount } from './format'

describe('financas format', () => {
  it('fmtMoney formats EUR', () => {
    expect(fmtMoney(200, 'EUR')).toBe('200.00 EUR')
    expect(fmtMoney(-40.5)).toBe('-40.50 EUR')
  })

  it('toLedgerAmount signs by kind', () => {
    expect(toLedgerAmount(100, 'expense')).toBe(-100)
    expect(toLedgerAmount(100, 'income')).toBe(100)
    expect(toLedgerAmount(-50, 'expense')).toBe(-50)
    expect(toLedgerAmount(-50, 'income')).toBe(50)
  })

  it('toExpenseAmount still maps to expense', () => {
    expect(toExpenseAmount(200)).toBe(-200)
  })
})
