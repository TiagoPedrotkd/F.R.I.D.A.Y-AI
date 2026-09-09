# Checklist — Fase 5b

Script: `.\scripts\fase5_acceptance.ps1`  
Live smoke: [`live-smoke-last.json`](live-smoke-last.json) · `.\scripts\acceptance\fases2-5_live_gates.ps1`

## Código / docs

- [x] Remoção Open Banking
- [x] Ledger local + REST
- [x] Faturas + investimentos
- [x] Painel Finanças (`apps/web/src/features/financas/`)
- [x] Skills + acceptance

## Manual

- [x] Definir salário no painel (`salary_monthly` no summary)
- [x] Adicionar 1 recorrente + 1 gasto + 1 fatura (recurring=6, tx=9, invoices=2)
- [x] Posição Bitstack ou import CSV IBKR (Bitstack BTC qty=0.001 no ledger local)
- [x] Chat/skill: `get_finance_summary` (“resumo finanças”) — skill live OK (LLM opcional para routing via chat)
