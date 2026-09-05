"""Personal finance skills — Fase 5b local ledger."""

from __future__ import annotations

from typing import Any

from friday.config import Settings, get_settings
from friday.integrations import get_enabled_integrations
from friday.integrations.finance_ledger import (
    FinanceLedgerError,
    add_recurring,
    add_transaction,
    investments_summary,
    list_recurring,
    list_transactions,
    month_summary,
    set_profile,
)
from friday.skills.base import SkillResult
from friday.skills.gated import confirmation_required_result, is_confirmed


def _pref_ok(settings: Settings) -> bool:
    enabled = get_enabled_integrations(settings)
    return bool(enabled.get("open_banking", True))


class GetFinanceSummarySkill:
    name = "get_finance_summary"
    description = (
        "Resumo financeiro do mes (salario, despesas, recorrentes, saldo previsto). "
        "Usa para 'resumo financas', 'quanto posso gastar', 'orcamento'."
    )
    parameters: dict[str, Any] = {
        "type": "object",
        "properties": {
            "year": {"type": "integer"},
            "month": {"type": "integer", "minimum": 1, "maximum": 12},
        },
        "required": [],
    }

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()

    async def execute(self, arguments: dict[str, Any]) -> SkillResult:
        if not _pref_ok(self._settings):
            return SkillResult(
                success=False, content="", error="Integracao open_banking/financas desactivada."
            )
        data = month_summary(
            self._settings,
            year=arguments.get("year"),
            month=arguments.get("month"),
        )
        msg = (
            f"Financas {data['year']}-{data['month']:02d}: "
            f"salario {data.get('salary_monthly')} {data.get('currency')}, "
            f"despesas {data.get('expenses')}, recorrentes imputadas {data.get('recurring_imputed')}, "
            f"resto {data.get('remaining')}."
        )
        return SkillResult(
            success=True, content=msg, metadata={"kind": "finance", "data": data}
        )


class ListFinanceTransactionsSkill:
    name = "list_finance_transactions"
    description = "Lista lancamentos do mes (gastos e rendimentos manuais)."
    parameters: dict[str, Any] = {
        "type": "object",
        "properties": {
            "year": {"type": "integer"},
            "month": {"type": "integer"},
            "limit": {"type": "integer"},
        },
        "required": [],
    }

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()

    async def execute(self, arguments: dict[str, Any]) -> SkillResult:
        rows = list_transactions(
            self._settings,
            year=arguments.get("year"),
            month=arguments.get("month"),
            limit=int(arguments.get("limit") or 20),
        )
        if not rows:
            return SkillResult(
                success=True,
                content="Sem lancamentos neste mes. Usa o painel Financas para registar.",
                metadata={"kind": "finance", "transactions": []},
            )
        lines = ["Lancamentos:"]
        for t in rows:
            lines.append(
                f"- {t.get('date')}: {t.get('amount')} [{t.get('category')}] {t.get('note') or ''}"
            )
        return SkillResult(
            success=True,
            content="\n".join(lines),
            metadata={"kind": "finance", "transactions": rows},
        )


class ListRecurringExpensesSkill:
    name = "list_recurring_expenses"
    description = "Lista despesas recorrentes (mensal/trimestral/semestral/anual)."
    parameters: dict[str, Any] = {"type": "object", "properties": {}, "required": []}

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()

    async def execute(self, arguments: dict[str, Any]) -> SkillResult:
        items = list_recurring(self._settings)
        if not items:
            return SkillResult(
                success=True,
                content="Sem despesas recorrentes registadas.",
                metadata={"kind": "finance", "items": []},
            )
        lines = ["Recorrentes:"]
        for r in items:
            lines.append(
                f"- {r.get('name')}: {r.get('amount')} / {r.get('cadence')} "
                f"[{r.get('category')}] active={r.get('active', True)}"
            )
        return SkillResult(
            success=True, content="\n".join(lines), metadata={"kind": "finance", "items": items}
        )


class GetInvestmentSummarySkill:
    name = "get_investment_summary"
    description = "Resumo de investimentos IBKR e Bitstack (posicoes locais)."
    parameters: dict[str, Any] = {"type": "object", "properties": {}, "required": []}

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()

    async def execute(self, arguments: dict[str, Any]) -> SkillResult:
        data = investments_summary(self._settings)
        lines = ["Investimentos:"]
        for broker, block in (data.get("brokers") or {}).items():
            lines.append(
                f"- {broker}: {block.get('positions_count')} posicoes, "
                f"custo aprox. {block.get('cost_basis_approx')}"
            )
        return SkillResult(
            success=True, content="\n".join(lines), metadata={"kind": "finance", "data": data}
        )


class AddFinanceTransactionSkill:
    name = "add_finance_transaction"
    description = (
        "Regista um lancamento (gasto negativo, rendimento positivo). "
        "Requer confirmacao. Args: amount, category, note, date."
    )
    parameters: dict[str, Any] = {
        "type": "object",
        "properties": {
            "amount": {"type": "number"},
            "category": {"type": "string"},
            "note": {"type": "string"},
            "date": {"type": "string"},
            "confirmed": {"type": "boolean"},
        },
        "required": ["amount"],
    }

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()

    async def execute(self, arguments: dict[str, Any]) -> SkillResult:
        amount = float(arguments["amount"])
        category = str(arguments.get("category") or "geral")
        note = str(arguments.get("note") or "")
        if not is_confirmed(arguments):
            return confirmation_required_result(
                action="add_finance_transaction",
                target=category,
                summary=f"registar lancamento {amount} ({category})",
                consequences="Fica guardado no ledger local.",
                payload={
                    "amount": amount,
                    "category": category,
                    "note": note,
                    "date": arguments.get("date"),
                },
            )
        try:
            row = add_transaction(
                self._settings,
                amount=amount,
                category=category,
                note=note,
                tx_date=arguments.get("date"),
            )
        except FinanceLedgerError as exc:
            return SkillResult(success=False, content="", error=str(exc))
        return SkillResult(
            success=True,
            content=f"Lancamento registado: {row.get('amount')} em {row.get('date')}.",
            metadata={"kind": "finance", "transaction": row},
        )


class SetSalarySkill:
    name = "set_salary"
    description = "Define o salario mensal. Requer confirmacao. Args: salary_monthly."
    parameters: dict[str, Any] = {
        "type": "object",
        "properties": {
            "salary_monthly": {"type": "number"},
            "confirmed": {"type": "boolean"},
        },
        "required": ["salary_monthly"],
    }

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()

    async def execute(self, arguments: dict[str, Any]) -> SkillResult:
        salary = float(arguments["salary_monthly"])
        if not is_confirmed(arguments):
            return confirmation_required_result(
                action="set_salary",
                target="profile",
                summary=f"definir salario mensal {salary}",
                consequences="Actualiza o perfil financeiro local.",
                payload={"salary_monthly": salary},
            )
        profile = set_profile(self._settings, salary_monthly=salary)
        return SkillResult(
            success=True,
            content=f"Salario mensal: {profile.get('salary_monthly')} {profile.get('currency')}.",
            metadata={"kind": "finance", "profile": profile},
        )


class UpsertRecurringExpenseSkill:
    name = "upsert_recurring_expense"
    description = (
        "Adiciona despesa recorrente. Requer confirmacao. "
        "Args: name, amount, cadence (monthly|quarterly|semiannual|annual), category."
    )
    parameters: dict[str, Any] = {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "amount": {"type": "number"},
            "cadence": {"type": "string"},
            "category": {"type": "string"},
            "confirmed": {"type": "boolean"},
        },
        "required": ["name", "amount"],
    }

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()

    async def execute(self, arguments: dict[str, Any]) -> SkillResult:
        name = str(arguments.get("name") or "")
        amount = float(arguments["amount"])
        cadence = str(arguments.get("cadence") or "monthly")
        category = str(arguments.get("category") or "geral")
        if not is_confirmed(arguments):
            return confirmation_required_result(
                action="upsert_recurring_expense",
                target=name,
                summary=f"adicionar recorrente {name} {amount}/{cadence}",
                consequences="Entra no orçamento mensal imputado.",
                payload={
                    "name": name,
                    "amount": amount,
                    "cadence": cadence,
                    "category": category,
                },
            )
        try:
            item = add_recurring(
                self._settings,
                name=name,
                amount=amount,
                cadence=cadence,
                category=category,
            )
        except FinanceLedgerError as exc:
            return SkillResult(success=False, content="", error=str(exc))
        return SkillResult(
            success=True,
            content=f"Recorrente: {item.get('name')} {item.get('amount')}/{item.get('cadence')}.",
            metadata={"kind": "finance", "item": item},
        )
