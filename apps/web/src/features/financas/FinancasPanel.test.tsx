import { render, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { financeSummaryOk } from '@/test/fixtures'
import { FinancasPanel } from './FinancasPanel'

vi.mock('@/api/client', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/api/client')>()
  return {
    ...actual,
    fetchFinanceSummary: vi.fn(),
    fetchFinanceRecurring: vi.fn(),
    fetchFinanceLedgerTx: vi.fn(),
    fetchFinanceInvestments: vi.fn(),
  }
})

import * as api from '@/api/client'

describe('FinancasPanel', () => {
  afterEach(() => {
    vi.mocked(api.fetchFinanceSummary).mockReset()
    vi.mocked(api.fetchFinanceRecurring).mockReset()
    vi.mocked(api.fetchFinanceLedgerTx).mockReset()
    vi.mocked(api.fetchFinanceInvestments).mockReset()
  })

  it('loads summary and shows remaining metric', async () => {
    vi.mocked(api.fetchFinanceSummary).mockResolvedValue(financeSummaryOk)
    vi.mocked(api.fetchFinanceRecurring).mockResolvedValue({ ok: true, items: [] })
    vi.mocked(api.fetchFinanceLedgerTx).mockResolvedValue({
      ok: true,
      transactions: financeSummaryOk.transactions,
    })
    vi.mocked(api.fetchFinanceInvestments).mockResolvedValue({
      ok: true,
      data: {
        ibkr: { positions: [], movements: [] },
        bitstack: { positions: [], movements: [] },
      },
      summary: undefined,
    })

    render(<FinancasPanel onClose={() => undefined} />)

    expect(screen.getByRole('dialog', { name: 'Finanças' })).toBeInTheDocument()
    await waitFor(() => {
      expect(screen.getByText(/1000\.00 EUR/)).toBeInTheDocument()
    })
    expect(api.fetchFinanceSummary).toHaveBeenCalled()
  })
})
