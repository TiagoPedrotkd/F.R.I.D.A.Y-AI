# Fase 5 — Finanças pessoais (ledger local)

**Estado:** gestor local de orçamento (sem Open Banking).  
Salário, despesas recorrentes, lançamentos, faturas anexadas, investimentos IBKR/Bitstack.

## Documentos

| Doc | Conteúdo |
|------|----------|
| [schema.md](schema.md) | Ficheiros em `data/integrations/finance/` |
| [skills-contract.md](skills-contract.md) | Skills + REST |
| [checklist-conclusao.md](checklist-conclusao.md) | Gates |

## Uso

1. Abrir painel **Finanças** na UI
2. Definir salário mensal
3. Adicionar recorrentes (mensal / trimestral / semestral / anual)
4. Registar gastos (valor negativo) e anexar faturas (PDF/imagem)
5. Investimentos: posições manuais; IBKR também via import CSV

## Chat

- “resumo finanças”, “quanto gastei”, “investimentos”, “despesas recorrentes”
- Mutações (`set_salary`, `add_finance_transaction`, …) pedem confirmação

## Fora de âmbito

- Open Banking / Enable Banking / PIS
- OCR de faturas
- API live IBKR Flex / Bitstack
