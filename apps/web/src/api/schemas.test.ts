import { describe, expect, it } from 'vitest'
import { ChatResponseSchema, FinanceSummarySchema, StatusResponseSchema } from './schemas'

describe('api schemas', () => {
  it('accepts minimal status payload', () => {
    const r = StatusResponseSchema.safeParse({
      status: 'ok',
      backend: true,
      demo: false,
      llm: { ok: true, model: 'test' },
    })
    expect(r.success).toBe(true)
  })

  it('rejects status without backend', () => {
    const r = StatusResponseSchema.safeParse({
      status: 'ok',
      demo: false,
      llm: { ok: true },
    })
    expect(r.success).toBe(false)
  })

  it('fills chat defaults for metadata/activity/ui', () => {
    const r = ChatResponseSchema.safeParse({ reply: 'Olá' })
    expect(r.success).toBe(true)
    if (r.success) {
      expect(r.data.metadata).toEqual({})
      expect(r.data.activity).toEqual([])
      expect(r.data.ui).toEqual({})
    }
  })

  it('rejects chat without reply', () => {
    expect(ChatResponseSchema.safeParse({ metadata: {} }).success).toBe(false)
  })

  it('accepts finance summary fixture', () => {
    const r = FinanceSummarySchema.safeParse({
      ok: true,
      year: 2026,
      month: 9,
      currency: 'EUR',
      income_extra: 0,
      expenses: 100,
      recurring_imputed: 50,
      remaining: 850,
      transactions_count: 1,
      transactions: [{ id: 't1', amount: -100 }],
    })
    expect(r.success).toBe(true)
  })

  it('rejects finance summary missing remaining', () => {
    const r = FinanceSummarySchema.safeParse({
      ok: true,
      year: 2026,
      month: 9,
      currency: 'EUR',
      income_extra: 0,
      expenses: 0,
      recurring_imputed: 0,
      transactions_count: 0,
    })
    expect(r.success).toBe(false)
  })
})
