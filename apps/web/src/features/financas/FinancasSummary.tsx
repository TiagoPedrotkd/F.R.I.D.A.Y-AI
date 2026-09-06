import type { FinanceSummary } from '@/api/schemas'
import { fmtMoney } from './format'
import { Metric } from './Metric'

export function FinancasSummary({ summary }: { summary: FinanceSummary | null }) {
  const currency = summary?.currency || 'EUR'
  return (
    <section className="mb-5" aria-label="Resumo do mês">
      <p className="hud-label mb-1">Resumo do mês</p>
      <Metric label="Salário" value={fmtMoney(summary?.salary_monthly, currency)} />
      <Metric label="Rendimentos extra" value={fmtMoney(summary?.income_extra, currency)} />
      <Metric label="Despesas" value={fmtMoney(summary?.expenses, currency)} />
      <Metric
        label="Recorrentes (imputado)"
        value={fmtMoney(summary?.recurring_imputed, currency)}
      />
      <Metric label="Resto previsto" value={fmtMoney(summary?.remaining, currency)} />
    </section>
  )
}
