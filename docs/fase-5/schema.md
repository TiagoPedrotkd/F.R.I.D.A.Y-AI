# Schema — Finanças pessoais

Raiz: `data/integrations/finance/`

## `profile.json`

```json
{
  "salary_monthly": 1800,
  "currency": "EUR",
  "updated_at": "…"
}
```

## `recurring.json`

```json
{
  "items": [
    {
      "id": "abc",
      "name": "Renda",
      "amount": 650,
      "cadence": "monthly",
      "category": "casa",
      "active": true
    }
  ]
}
```

Cadences: `monthly` | `quarterly` | `semiannual` | `annual`  
Imputação no mês: amount / 1|3|6|12.

## `transactions/YYYY-MM.json`

Lançamentos com `amount` positivo (rendimento) ou negativo (gasto), `category`, `note`, `invoice_id?`, `source`.

## `invoices/{id}.meta.json` + ficheiro

PDF/JPG/PNG/WebP até 15MB; sem OCR.

## `investments.json`

```json
{
  "ibkr": { "positions": [], "movements": [] },
  "bitstack": { "positions": [], "movements": [] }
}
```
