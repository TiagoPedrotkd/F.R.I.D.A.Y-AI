import { useCallback, useEffect, useState } from 'react'
import * as api from '../api/client'
import type { FinanceLedgerTx, FinancePosition, FinanceRecurring, FinanceSummary } from '../api/client'

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="border-b border-cyan/10 py-2">
      <p className="text-[10px] uppercase tracking-wide text-[var(--text-muted)]">{label}</p>
      <p className="font-mono text-sm text-cyan">{value}</p>
    </div>
  )
}

function fmtMoney(v: number | null | undefined, currency = 'EUR'): string {
  if (v == null || Number.isNaN(v)) return '—'
  return `${v.toFixed(2)} ${currency}`
}

export function FinancasPanel({ onClose }: { onClose: () => void }) {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [summary, setSummary] = useState<FinanceSummary | null>(null)
  const [recurring, setRecurring] = useState<FinanceRecurring[]>([])
  const [txs, setTxs] = useState<FinanceLedgerTx[]>([])
  const [broker, setBroker] = useState<'ibkr' | 'bitstack'>('ibkr')
  const [positions, setPositions] = useState<FinancePosition[]>([])

  const [salary, setSalary] = useState('')
  const [recName, setRecName] = useState('')
  const [recAmount, setRecAmount] = useState('')
  const [recCadence, setRecCadence] = useState('monthly')
  const [txAmount, setTxAmount] = useState('')
  const [txNote, setTxNote] = useState('')
  const [txCategory, setTxCategory] = useState('geral')
  const [posSymbol, setPosSymbol] = useState('')
  const [posQty, setPosQty] = useState('')
  const [posCost, setPosCost] = useState('')

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const [sum, rec, tx, inv] = await Promise.all([
        api.fetchFinanceSummary(),
        api.fetchFinanceRecurring(),
        api.fetchFinanceLedgerTx(),
        api.fetchFinanceInvestments(),
      ])
      setSummary(sum)
      setRecurring(rec.items || [])
      setTxs(tx.transactions || [])
      if (sum.salary_monthly != null) setSalary(String(sum.salary_monthly))
      const block = inv.data?.[broker]
      setPositions(block?.positions || [])
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Falha a ler finanças')
    } finally {
      setLoading(false)
    }
  }, [broker])

  useEffect(() => {
    void load()
  }, [load])

  const currency = summary?.currency || 'EUR'

  return (
    <div className="fixed inset-0 z-40 flex justify-end bg-black/60" role="presentation">
      <div
        role="dialog"
        aria-modal="true"
        aria-label="Finanças"
        className="hud-panel h-full w-full max-w-md overflow-y-auto border-l border-cyan/30 p-5"
        style={{ clipPath: 'none', borderRadius: 0 }}
      >
        <div className="mb-5 flex items-center justify-between">
          <div>
            <p className="hud-label">Pessoal</p>
            <h2 className="font-display text-lg font-semibold tracking-wide text-cyan">Finanças</h2>
          </div>
          <button type="button" className="hud-btn" onClick={onClose}>
            Fechar
          </button>
        </div>

        {error ? <p className="mb-3 text-xs text-amber">{error}</p> : null}
        <button type="button" className="hud-btn mb-4 text-xs" disabled={loading} onClick={() => void load()}>
          Actualizar
        </button>

        <section className="mb-5">
          <p className="hud-label mb-1">Resumo do mês</p>
          <Metric label="Salário" value={fmtMoney(summary?.salary_monthly, currency)} />
          <Metric label="Despesas" value={fmtMoney(summary?.expenses, currency)} />
          <Metric label="Recorrentes (imputado)" value={fmtMoney(summary?.recurring_imputed, currency)} />
          <Metric label="Resto previsto" value={fmtMoney(summary?.remaining, currency)} />
        </section>

        <section className="mb-5">
          <p className="hud-label mb-1">Salário mensal</p>
          <div className="flex gap-2">
            <input
              className="flex-1 border border-cyan/30 bg-[var(--color-night-950)] px-2 py-1 font-mono text-cyan"
              value={salary}
              onChange={(e) => setSalary(e.target.value)}
              placeholder="ex. 1800"
            />
            <button
              type="button"
              className="hud-btn hud-btn-primary text-xs"
              disabled={loading || !salary}
              onClick={() => {
                void api
                  .putFinanceProfile({ salary_monthly: Number(salary) })
                  .then(() => load())
                  .catch((e) => setError(e instanceof Error ? e.message : 'Falha'))
              }}
            >
              Guardar
            </button>
          </div>
        </section>

        <section className="mb-5">
          <p className="hud-label mb-1">Recorrentes</p>
          <ul className="mb-2 space-y-1 text-sm">
            {recurring.length === 0 ? (
              <li className="text-xs text-[var(--text-muted)]">Sem recorrentes.</li>
            ) : (
              recurring.map((r) => (
                <li key={r.id} className="flex items-center justify-between border-b border-cyan/10 py-1.5">
                  <span className="text-[var(--text-muted)]">
                    {r.name} · {r.cadence}
                  </span>
                  <span className="flex items-center gap-2">
                    <span className="font-mono text-cyan">{fmtMoney(r.amount, currency)}</span>
                    <button
                      type="button"
                      className="text-[10px] text-amber"
                      onClick={() => {
                        void api.deleteFinanceRecurring(r.id).then(() => load())
                      }}
                    >
                      ×
                    </button>
                  </span>
                </li>
              ))
            )}
          </ul>
          <div className="grid grid-cols-2 gap-2">
            <input
              className="border border-cyan/30 bg-[var(--color-night-950)] px-2 py-1 text-xs text-cyan"
              placeholder="Nome"
              value={recName}
              onChange={(e) => setRecName(e.target.value)}
            />
            <input
              className="border border-cyan/30 bg-[var(--color-night-950)] px-2 py-1 text-xs text-cyan"
              placeholder="Valor"
              value={recAmount}
              onChange={(e) => setRecAmount(e.target.value)}
            />
            <select
              className="border border-cyan/30 bg-[var(--color-night-950)] px-2 py-1 text-xs text-cyan"
              value={recCadence}
              onChange={(e) => setRecCadence(e.target.value)}
            >
              <option value="monthly">Mensal</option>
              <option value="quarterly">Trimestral</option>
              <option value="semiannual">Semestral</option>
              <option value="annual">Anual</option>
            </select>
            <button
              type="button"
              className="hud-btn text-xs"
              disabled={!recName || !recAmount}
              onClick={() => {
                void api
                  .createFinanceRecurring({
                    name: recName,
                    amount: Number(recAmount),
                    cadence: recCadence,
                  })
                  .then(() => {
                    setRecName('')
                    setRecAmount('')
                    return load()
                  })
                  .catch((e) => setError(e instanceof Error ? e.message : 'Falha'))
              }}
            >
              Adicionar
            </button>
          </div>
        </section>

        <section className="mb-5">
          <p className="hud-label mb-1">Lançamentos</p>
          <ul className="mb-2 max-h-40 space-y-1 overflow-y-auto text-sm">
            {txs.length === 0 ? (
              <li className="text-xs text-[var(--text-muted)]">Sem lançamentos este mês.</li>
            ) : (
              txs.map((t) => (
                <li key={t.id} className="flex justify-between gap-2 border-b border-cyan/10 py-1.5">
                  <span className="min-w-0 truncate text-[var(--text-muted)]">
                    {t.date} · {t.category} · {t.note || '—'}
                  </span>
                  <span className="shrink-0 font-mono text-cyan">{fmtMoney(t.amount, currency)}</span>
                </li>
              ))
            )}
          </ul>
          <div className="grid grid-cols-2 gap-2">
            <input
              className="border border-cyan/30 bg-[var(--color-night-950)] px-2 py-1 text-xs text-cyan"
              placeholder="Valor (− gasto)"
              value={txAmount}
              onChange={(e) => setTxAmount(e.target.value)}
            />
            <input
              className="border border-cyan/30 bg-[var(--color-night-950)] px-2 py-1 text-xs text-cyan"
              placeholder="Categoria"
              value={txCategory}
              onChange={(e) => setTxCategory(e.target.value)}
            />
            <input
              className="col-span-2 border border-cyan/30 bg-[var(--color-night-950)] px-2 py-1 text-xs text-cyan"
              placeholder="Nota"
              value={txNote}
              onChange={(e) => setTxNote(e.target.value)}
            />
            <button
              type="button"
              className="hud-btn text-xs"
              disabled={!txAmount}
              onClick={() => {
                void api
                  .createFinanceLedgerTx({
                    amount: Number(txAmount),
                    category: txCategory,
                    note: txNote,
                  })
                  .then(() => {
                    setTxAmount('')
                    setTxNote('')
                    return load()
                  })
                  .catch((e) => setError(e instanceof Error ? e.message : 'Falha'))
              }}
            >
              Registar
            </button>
            <label className="hud-btn cursor-pointer text-center text-xs">
              Fatura
              <input
                type="file"
                accept=".pdf,.jpg,.jpeg,.png,.webp"
                className="hidden"
                onChange={(e) => {
                  const f = e.target.files?.[0]
                  if (!f) return
                  void api
                    .uploadFinanceInvoice(f, {
                      note: txNote || f.name,
                      amount: txAmount ? Math.abs(Number(txAmount)) : undefined,
                    })
                    .then(() => load())
                    .catch((err) => setError(err instanceof Error ? err.message : 'Upload falhou'))
                }}
              />
            </label>
          </div>
        </section>

        <section>
          <p className="hud-label mb-1">Investimentos</p>
          <div className="mb-2 flex gap-2">
            <button
              type="button"
              className={`hud-btn text-xs ${broker === 'ibkr' ? 'hud-btn-primary' : ''}`}
              onClick={() => setBroker('ibkr')}
            >
              IBKR
            </button>
            <button
              type="button"
              className={`hud-btn text-xs ${broker === 'bitstack' ? 'hud-btn-primary' : ''}`}
              onClick={() => setBroker('bitstack')}
            >
              Bitstack
            </button>
          </div>
          <ul className="mb-2 space-y-1 text-sm">
            {positions.length === 0 ? (
              <li className="text-xs text-[var(--text-muted)]">Sem posições.</li>
            ) : (
              positions.map((p) => (
                <li key={p.symbol} className="flex justify-between border-b border-cyan/10 py-1.5">
                  <span className="text-[var(--text-muted)]">{p.symbol}</span>
                  <span className="font-mono text-cyan">
                    {p.qty}
                    {p.avg_cost != null ? ` @ ${p.avg_cost}` : ''}
                  </span>
                </li>
              ))
            )}
          </ul>
          <div className="grid grid-cols-3 gap-2">
            <input
              className="border border-cyan/30 bg-[var(--color-night-950)] px-2 py-1 text-xs text-cyan"
              placeholder="Símbolo"
              value={posSymbol}
              onChange={(e) => setPosSymbol(e.target.value)}
            />
            <input
              className="border border-cyan/30 bg-[var(--color-night-950)] px-2 py-1 text-xs text-cyan"
              placeholder="Qty"
              value={posQty}
              onChange={(e) => setPosQty(e.target.value)}
            />
            <input
              className="border border-cyan/30 bg-[var(--color-night-950)] px-2 py-1 text-xs text-cyan"
              placeholder="Custo méd."
              value={posCost}
              onChange={(e) => setPosCost(e.target.value)}
            />
          </div>
          <div className="mt-2 flex gap-2">
            <button
              type="button"
              className="hud-btn text-xs"
              disabled={!posSymbol || !posQty}
              onClick={() => {
                void api
                  .upsertFinancePosition({
                    broker,
                    symbol: posSymbol,
                    qty: Number(posQty),
                    avg_cost: posCost ? Number(posCost) : null,
                  })
                  .then(() => {
                    setPosSymbol('')
                    setPosQty('')
                    setPosCost('')
                    return load()
                  })
                  .catch((e) => setError(e instanceof Error ? e.message : 'Falha'))
              }}
            >
              Guardar posição
            </button>
            {broker === 'ibkr' ? (
              <label className="hud-btn cursor-pointer text-xs">
                Import CSV
                <input
                  type="file"
                  accept=".csv,text/csv"
                  className="hidden"
                  onChange={(e) => {
                    const f = e.target.files?.[0]
                    if (!f) return
                    void f.text().then((text) =>
                      api
                        .importIbkrCsv(text)
                        .then(() => load())
                        .catch((err) => setError(err instanceof Error ? err.message : 'CSV falhou')),
                    )
                  }}
                />
              </label>
            ) : null}
          </div>
        </section>
      </div>
    </div>
  )
}
