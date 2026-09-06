import { useCallback, useEffect, useState } from 'react'
import * as api from '@/api/client'
import type {
  FinanceLedgerTx,
  FinancePosition,
  FinanceRecurring,
  FinanceSummary,
} from '@/api/client'
import { HudButton } from '@/components/ui'
import { FinancasSummary } from './FinancasSummary'
import { fmtMoney, toLedgerAmount, type LedgerKind } from './format'

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
  const [txKind, setTxKind] = useState<LedgerKind>('expense')
  const [posSymbol, setPosSymbol] = useState('')
  const [posQty, setPosQty] = useState('')
  const [posCost, setPosCost] = useState('')

  const load = useCallback(
    async (signal?: AbortSignal) => {
      setLoading(true)
      setError(null)
      try {
        const [sum, rec, tx, inv] = await Promise.all([
          // skipCache: summary must refresh after writes (ledger list is uncached)
          api.fetchFinanceSummary(undefined, undefined, { signal, skipCache: true }),
          api.fetchFinanceRecurring(),
          api.fetchFinanceLedgerTx(),
          api.fetchFinanceInvestments(),
        ])
        if (signal?.aborted) return
        setSummary(sum)
        setRecurring(rec.items || [])
        setTxs(tx.transactions || [])
        if (sum.salary_monthly != null) setSalary(String(sum.salary_monthly))
        const block = inv.data?.[broker]
        setPositions(block?.positions || [])
      } catch (e) {
        if (signal?.aborted || (e instanceof DOMException && e.name === 'AbortError')) return
        setError(e instanceof Error ? e.message : 'Falha a ler finanças')
      } finally {
        if (!signal?.aborted) setLoading(false)
      }
    },
    [broker],
  )

  useEffect(() => {
    const ac = new AbortController()
    void load(ac.signal)
    return () => ac.abort()
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
          <HudButton onClick={onClose}>Fechar</HudButton>
        </div>

        {error ? <p className="mb-3 text-xs text-amber">{error}</p> : null}
        <HudButton className="mb-4 text-xs" disabled={loading} onClick={() => void load()}>
          Actualizar
        </HudButton>

        <FinancasSummary summary={summary} />

        <section className="mb-5">
          <p className="hud-label mb-1">Salário mensal</p>
          <div className="flex gap-2">
            <input
              className="flex-1 border border-cyan/30 bg-[var(--color-night-950)] px-2 py-1 font-mono text-cyan"
              value={salary}
              onChange={(e) => setSalary(e.target.value)}
              placeholder="ex. 1800"
            />
            <HudButton
              variant="primary"
              className="text-xs"
              disabled={loading || !salary}
              onClick={() => {
                void api
                  .putFinanceProfile({ salary_monthly: Number(salary) })
                  .then(() => load())
                  .catch((e) => setError(e instanceof Error ? e.message : 'Falha'))
              }}
            >
              Guardar
            </HudButton>
          </div>
        </section>

        <section className="mb-5">
          <p className="hud-label mb-1">Recorrentes</p>
          <ul className="mb-2 space-y-1 text-sm">
            {recurring.length === 0 ? (
              <li className="text-xs text-[var(--text-muted)]">Sem recorrentes.</li>
            ) : (
              recurring.map((r) => (
                <li
                  key={r.id}
                  className="flex items-center justify-between border-b border-cyan/10 py-1.5"
                >
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
            <HudButton
              className="text-xs"
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
            </HudButton>
          </div>
        </section>

        <section className="mb-5">
          <p className="hud-label mb-1">Lançamentos</p>
          <ul className="mb-2 max-h-40 space-y-1 overflow-y-auto text-sm">
            {txs.length === 0 ? (
              <li className="text-xs text-[var(--text-muted)]">Sem lançamentos este mês.</li>
            ) : (
              txs.map((t) => (
                <li
                  key={t.id}
                  className="flex justify-between gap-2 border-b border-cyan/10 py-1.5"
                >
                  <span className="min-w-0 truncate text-[var(--text-muted)]">
                    {t.date} · {t.category} · {t.note || '—'}
                  </span>
                  <span className="shrink-0 font-mono text-cyan">
                    {fmtMoney(t.amount, currency)}
                  </span>
                </li>
              ))
            )}
          </ul>
          <div className="grid grid-cols-2 gap-2">
            <select
              className="border border-cyan/30 bg-[var(--color-night-950)] px-2 py-1 text-xs text-cyan"
              value={txKind}
              onChange={(e) => setTxKind(e.target.value as LedgerKind)}
              aria-label="Tipo de lançamento"
            >
              <option value="expense">Gasto</option>
              <option value="income">Rendimento</option>
            </select>
            <input
              className="border border-cyan/30 bg-[var(--color-night-950)] px-2 py-1 text-xs text-cyan"
              placeholder={txKind === 'income' ? 'Valor (recebido)' : 'Valor (gasto)'}
              value={txAmount}
              onChange={(e) => setTxAmount(e.target.value)}
              inputMode="decimal"
            />
            <input
              className="border border-cyan/30 bg-[var(--color-night-950)] px-2 py-1 text-xs text-cyan"
              placeholder="Categoria"
              value={txCategory}
              onChange={(e) => setTxCategory(e.target.value)}
            />
            <input
              className="border border-cyan/30 bg-[var(--color-night-950)] px-2 py-1 text-xs text-cyan"
              placeholder="Nota"
              value={txNote}
              onChange={(e) => setTxNote(e.target.value)}
            />
            <HudButton
              className="text-xs"
              disabled={!txAmount}
              onClick={() => {
                const amount = toLedgerAmount(Number(txAmount), txKind)
                if (!Number.isFinite(amount) || amount === 0) {
                  setError('Indica um valor válido.')
                  return
                }
                void api
                  .createFinanceLedgerTx({
                    amount,
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
            </HudButton>
            <label className="hud-btn cursor-pointer text-center text-xs">
              Fatura
              <input
                type="file"
                accept=".pdf,.jpg,.jpeg,.png,.webp"
                className="hidden"
                onChange={(e) => {
                  const f = e.target.files?.[0]
                  if (!f) return
                  const amount = txAmount ? toLedgerAmount(Number(txAmount), txKind) : undefined
                  void api
                    .uploadFinanceInvoice(f, {
                      note: txNote || f.name,
                      amount,
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
            <HudButton
              variant={broker === 'ibkr' ? 'primary' : 'default'}
              className="text-xs"
              onClick={() => setBroker('ibkr')}
            >
              IBKR
            </HudButton>
            <HudButton
              variant={broker === 'bitstack' ? 'primary' : 'default'}
              className="text-xs"
              onClick={() => setBroker('bitstack')}
            >
              Bitstack
            </HudButton>
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
            <HudButton
              className="text-xs"
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
            </HudButton>
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
                        .catch((err) =>
                          setError(err instanceof Error ? err.message : 'CSV falhou'),
                        ),
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
