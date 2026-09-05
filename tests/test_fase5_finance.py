"""Fase 5b — personal finance ledger (local)."""

from __future__ import annotations

from pathlib import Path

from friday.config import Settings
from friday.integrations.finance_ledger import (
    add_recurring,
    add_transaction,
    import_ibkr_csv,
    month_summary,
    save_invoice,
    set_profile,
    upsert_position,
)
from friday.llm.intent_router import match_skill_with_args
from friday.skills.registry import default_registry


def _settings(tmp_path: Path) -> Settings:
    prefs = tmp_path / "prefs"
    prefs.mkdir(exist_ok=True)
    return Settings(PREFS_DIR=str(prefs))


def test_fase5_docs_exist():
    root = Path("docs/fase-5")
    for name in ("README.md", "schema.md", "skills-contract.md", "checklist-conclusao.md"):
        assert (root / name).is_file(), name
    assert not (root / "enablebanking.md").is_file()
    assert not Path("friday/integrations/enable_banking.py").is_file()


def test_profile_and_summary(tmp_path: Path):
    s = _settings(tmp_path)
    set_profile(s, salary_monthly=2000)
    add_recurring(s, name="Renda", amount=600, cadence="monthly")
    add_recurring(s, name="Seguro", amount=120, cadence="annual")
    add_transaction(s, amount=-40, category="comida", note="almoco")
    add_transaction(s, amount=50, category="extra", note="bonus")
    summary = month_summary(s)
    assert summary["salary_monthly"] == 2000
    assert summary["expenses"] == 40
    assert summary["income_extra"] == 50
    # 600 monthly + 120/12 = 10
    assert summary["recurring_imputed"] == 610
    assert summary["remaining"] == 2000 + 50 - 40 - 610


def test_invoice_roundtrip(tmp_path: Path):
    s = _settings(tmp_path)
    meta = save_invoice(
        filename="fatura.pdf",
        content=b"%PDF-1.4 fake",
        settings=s,
        note="test",
        amount=12.5,
    )
    assert meta["id"]
    path = tmp_path / "integrations" / "finance" / "invoices" / meta["stored_as"]
    assert path.is_file()


def test_ibkr_csv_import(tmp_path: Path):
    s = _settings(tmp_path)
    csv_text = "Date,Symbol,Quantity,Amount,CurrencyPrimary\n2026-01-02,AAPL,10,-1500,USD\n"
    out = import_ibkr_csv(csv_text, s)
    assert out["imported"] == 1
    assert "AAPL" in out["symbols"]


def test_investments_position(tmp_path: Path):
    s = _settings(tmp_path)
    upsert_position(s, broker="bitstack", symbol="BTC", qty=0.01, avg_cost=50000)
    summary = month_summary(s)
    assert summary["investments"]["brokers"]["bitstack"]["positions_count"] == 1


def test_finance_skills_registered():
    names = set(default_registry(Settings()).names())
    for n in (
        "get_finance_summary",
        "list_finance_transactions",
        "list_recurring_expenses",
        "get_investment_summary",
        "add_finance_transaction",
        "set_salary",
        "upsert_recurring_expense",
    ):
        assert n in names


def test_finance_intent_routing():
    assert match_skill_with_args("resumo financas")[0] == "get_finance_summary"
    assert match_skill_with_args("despesas recorrentes")[0] == "list_recurring_expenses"
    assert match_skill_with_args("investimentos ibkr")[0] == "get_investment_summary"
    assert match_skill_with_args("gastos do mes")[0] == "list_finance_transactions"


def test_finance_status_endpoint(tmp_path: Path):
    import sys
    from unittest.mock import MagicMock, patch

    from fastapi.testclient import TestClient

    API_DIR = Path(__file__).resolve().parents[1] / "services" / "agent-api"
    sys.path.insert(0, str(API_DIR))
    import main as agent_main

    client = TestClient(agent_main.app)
    settings = MagicMock()
    settings.prefs_dir = tmp_path / "prefs"
    (tmp_path / "prefs").mkdir(exist_ok=True)

    with patch("main.get_settings", return_value=settings), patch(
        "friday.config.get_settings", return_value=settings
    ), patch(
        "friday.integrations.finance_ledger.get_settings", return_value=settings
    ):
        # status uses integrations_root(settings) via prefs_dir
        r = client.get("/v1/finance/status")
    assert r.status_code == 200
    body = r.json()
    assert body["provider"] == "local_ledger"
    assert body["enabled"] is True
