# ADR 0006 — Ledger pessoal em vez de Open Banking

## Context

GoCardless/Enable Banking AIS ficaram bloqueados ou demasiado frágeis para o objectivo (finanças pessoais do utilizador).

## Decision

**Remover Open Banking** da produto. Implementar **ledger local** (salário, recurring, txs, invoices, IBKR/Bitstack) em `friday/integrations/finance_ledger.py` + UI Finanças.

## Consequences

- Sem dependência de AIS/PSD2 signups.
- Dados em `data/integrations/finance/`.
- Skills de finanças mundiais (notícias) continuam separados do ledger pessoal.
