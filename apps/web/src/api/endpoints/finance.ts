import { FinanceSummarySchema, type FinanceSummary } from '../schemas'
import { defineParamEndpoint } from './types'

export type { FinanceSummary }

export type FinanceSummaryParams = {
  year?: number
  month?: number
}

export const fetchFinanceSummary = defineParamEndpoint<FinanceSummaryParams, FinanceSummary>({
  method: 'GET',
  path: ({ year, month }) => {
    const qs = new URLSearchParams()
    if (year != null) qs.set('year', String(year))
    if (month != null) qs.set('month', String(month))
    const q = qs.toString()
    return `/v1/finance/summary${q ? `?${q}` : ''}`
  },
  schema: FinanceSummarySchema,
  timeoutMs: 10_000,
  retries: 3,
  cache: { ttlMs: 5_000 },
})
