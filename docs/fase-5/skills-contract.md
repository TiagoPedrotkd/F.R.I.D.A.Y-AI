# Skills / REST — Fase 5b

## Skills

| Skill | Notas |
|-------|-------|
| `get_finance_summary` | Resumo do mês |
| `list_finance_transactions` | Lançamentos |
| `list_recurring_expenses` | Recorrentes |
| `get_investment_summary` | IBKR / Bitstack |
| `add_finance_transaction` | Gated |
| `set_salary` | Gated |
| `upsert_recurring_expense` | Gated |

## REST

| Método | Rota |
|--------|------|
| GET | `/v1/finance/status` |
| GET | `/v1/finance/summary` |
| GET/PUT | `/v1/finance/profile` |
| GET/POST | `/v1/finance/recurring` |
| PATCH/DELETE | `/v1/finance/recurring/{id}` |
| GET/POST | `/v1/finance/transactions` |
| DELETE | `/v1/finance/transactions/{id}` |
| GET/POST | `/v1/finance/invoices` |
| GET | `/v1/finance/investments` |
| POST | `/v1/finance/investments/positions` |
| POST | `/v1/finance/investments/movements` |
| POST | `/v1/finance/investments/ibkr-import` |
