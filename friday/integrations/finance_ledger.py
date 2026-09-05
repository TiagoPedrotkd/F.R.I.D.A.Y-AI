"""Personal finance ledger — Fase 5b (local, no Open Banking)."""

from __future__ import annotations

import csv
import io
import json
import re
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from friday.config import Settings, get_settings
from friday.integrations import integrations_root

CADENCES = ("monthly", "quarterly", "semiannual", "annual")
CADENCE_DIVISOR = {
    "monthly": 1,
    "quarterly": 3,
    "semiannual": 6,
    "annual": 12,
}
BROKERS = ("ibkr", "bitstack")
INVOICE_EXTS = {".pdf", ".jpg", ".jpeg", ".png", ".webp"}


class FinanceLedgerError(RuntimeError):
    pass


def _root(settings: Settings | None = None) -> Path:
    return integrations_root(settings) / "finance"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_json(path: Path) -> Any:
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def save_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def status(settings: Settings | None = None) -> dict[str, Any]:
    settings = settings or get_settings()
    root = _root(settings)
    profile = get_profile(settings)
    recurring = list_recurring(settings)
    inv = get_investments(settings)
    pos_n = sum(len(inv.get(b, {}).get("positions") or []) for b in BROKERS)
    return {
        "enabled": True,
        "configured": True,
        "provider": "local_ledger",
        "currency": profile.get("currency") or "EUR",
        "salary_monthly": profile.get("salary_monthly"),
        "recurring_count": len([r for r in recurring if r.get("active", True)]),
        "investments_positions": pos_n,
        "path": str(root),
    }


# --- profile ---


def default_profile() -> dict[str, Any]:
    return {
        "salary_monthly": None,
        "currency": "EUR",
        "updated_at": None,
    }


def get_profile(settings: Settings | None = None) -> dict[str, Any]:
    path = _root(settings) / "profile.json"
    data = load_json(path)
    if not isinstance(data, dict):
        return default_profile()
    out = default_profile()
    out.update({k: data.get(k) for k in out})
    return out


def set_profile(
    settings: Settings | None = None,
    *,
    salary_monthly: float | None = None,
    currency: str | None = None,
) -> dict[str, Any]:
    profile = get_profile(settings)
    if salary_monthly is not None:
        profile["salary_monthly"] = float(salary_monthly)
    if currency is not None and currency.strip():
        profile["currency"] = currency.strip().upper()[:3]
    profile["updated_at"] = _now_iso()
    save_json(_root(settings) / "profile.json", profile)
    return profile


# --- recurring ---


def list_recurring(settings: Settings | None = None) -> list[dict[str, Any]]:
    data = load_json(_root(settings) / "recurring.json")
    if isinstance(data, dict):
        items = data.get("items") or []
    elif isinstance(data, list):
        items = data
    else:
        items = []
    return [i for i in items if isinstance(i, dict)]


def _save_recurring(items: list[dict[str, Any]], settings: Settings | None) -> None:
    save_json(_root(settings) / "recurring.json", {"items": items, "updated_at": _now_iso()})


def add_recurring(
    settings: Settings | None = None,
    *,
    name: str,
    amount: float,
    cadence: str = "monthly",
    category: str = "geral",
    next_due: str | None = None,
    active: bool = True,
) -> dict[str, Any]:
    cad = (cadence or "monthly").strip().lower()
    if cad not in CADENCES:
        raise FinanceLedgerError(f"cadence invalida: {cadence}")
    item = {
        "id": uuid4().hex[:12],
        "name": (name or "").strip() or "Despesa",
        "amount": abs(float(amount)),
        "cadence": cad,
        "category": (category or "geral").strip() or "geral",
        "next_due": next_due,
        "active": bool(active),
        "created_at": _now_iso(),
    }
    items = list_recurring(settings)
    items.append(item)
    _save_recurring(items, settings)
    return item


def update_recurring(
    item_id: str,
    settings: Settings | None = None,
    **fields: Any,
) -> dict[str, Any]:
    items = list_recurring(settings)
    for i, item in enumerate(items):
        if item.get("id") != item_id:
            continue
        if "name" in fields and fields["name"] is not None:
            item["name"] = str(fields["name"]).strip()
        if "amount" in fields and fields["amount"] is not None:
            item["amount"] = abs(float(fields["amount"]))
        if "cadence" in fields and fields["cadence"] is not None:
            cad = str(fields["cadence"]).strip().lower()
            if cad not in CADENCES:
                raise FinanceLedgerError(f"cadence invalida: {cad}")
            item["cadence"] = cad
        if "category" in fields and fields["category"] is not None:
            item["category"] = str(fields["category"]).strip()
        if "next_due" in fields:
            item["next_due"] = fields["next_due"]
        if "active" in fields and fields["active"] is not None:
            item["active"] = bool(fields["active"])
        item["updated_at"] = _now_iso()
        items[i] = item
        _save_recurring(items, settings)
        return item
    raise FinanceLedgerError(f"recurring nao encontrado: {item_id}")


def delete_recurring(item_id: str, settings: Settings | None = None) -> dict[str, Any]:
    items = list_recurring(settings)
    kept = [i for i in items if i.get("id") != item_id]
    if len(kept) == len(items):
        raise FinanceLedgerError(f"recurring nao encontrado: {item_id}")
    _save_recurring(kept, settings)
    return {"ok": True, "id": item_id}


def monthly_imputed_recurring(settings: Settings | None = None) -> dict[str, Any]:
    items = [r for r in list_recurring(settings) if r.get("active", True)]
    total = 0.0
    breakdown: list[dict[str, Any]] = []
    for r in items:
        cad = r.get("cadence") or "monthly"
        div = CADENCE_DIVISOR.get(cad, 1)
        monthly = float(r.get("amount") or 0) / div
        total += monthly
        breakdown.append(
            {
                "id": r.get("id"),
                "name": r.get("name"),
                "cadence": cad,
                "amount": r.get("amount"),
                "monthly_imputed": round(monthly, 2),
                "category": r.get("category"),
            }
        )
    return {"total": round(total, 2), "items": breakdown}


# --- transactions ---


def _tx_path(settings: Settings | None, year: int, month: int) -> Path:
    return _root(settings) / "transactions" / f"{year:04d}-{month:02d}.json"


def list_transactions(
    settings: Settings | None = None,
    *,
    year: int | None = None,
    month: int | None = None,
    limit: int = 100,
) -> list[dict[str, Any]]:
    today = date.today()
    y = year or today.year
    m = month or today.month
    data = load_json(_tx_path(settings, y, m))
    items = []
    if isinstance(data, dict):
        items = data.get("transactions") or []
    elif isinstance(data, list):
        items = data
    rows = [t for t in items if isinstance(t, dict)]
    rows.sort(key=lambda t: str(t.get("date") or ""), reverse=True)
    return rows[: max(1, min(limit, 500))]


def add_transaction(
    settings: Settings | None = None,
    *,
    amount: float,
    category: str = "geral",
    note: str = "",
    tx_date: str | None = None,
    tags: list[str] | None = None,
    invoice_id: str | None = None,
    source: str = "manual",
) -> dict[str, Any]:
    d = tx_date or date.today().isoformat()
    try:
        parsed = date.fromisoformat(d[:10])
    except ValueError as exc:
        raise FinanceLedgerError(f"data invalida: {tx_date}") from exc
    row = {
        "id": uuid4().hex[:12],
        "date": parsed.isoformat(),
        "amount": float(amount),
        "category": (category or "geral").strip() or "geral",
        "note": (note or "").strip()[:500],
        "tags": tags or [],
        "invoice_id": invoice_id,
        "source": source or "manual",
        "created_at": _now_iso(),
    }
    path = _tx_path(settings, parsed.year, parsed.month)
    existing = load_json(path)
    txs: list[dict[str, Any]] = []
    if isinstance(existing, dict):
        txs = list(existing.get("transactions") or [])
    elif isinstance(existing, list):
        txs = list(existing)
    txs.append(row)
    save_json(
        path,
        {
            "year": parsed.year,
            "month": parsed.month,
            "transactions": txs,
            "updated_at": _now_iso(),
        },
    )
    return row


def delete_transaction(
    tx_id: str,
    settings: Settings | None = None,
    *,
    year: int | None = None,
    month: int | None = None,
) -> dict[str, Any]:
    today = date.today()
    y = year or today.year
    m = month or today.month
    # Search current month first, then scan all months if needed
    paths = [_tx_path(settings, y, m)]
    tx_dir = _root(settings) / "transactions"
    if tx_dir.is_dir():
        for p in sorted(tx_dir.glob("*.json")):
            if p not in paths:
                paths.append(p)
    for path in paths:
        data = load_json(path)
        if not isinstance(data, dict):
            continue
        txs = list(data.get("transactions") or [])
        kept = [t for t in txs if t.get("id") != tx_id]
        if len(kept) == len(txs):
            continue
        data["transactions"] = kept
        data["updated_at"] = _now_iso()
        save_json(path, data)
        return {"ok": True, "id": tx_id}
    raise FinanceLedgerError(f"transacao nao encontrada: {tx_id}")


# --- invoices ---


def _invoices_dir(settings: Settings | None) -> Path:
    d = _root(settings) / "invoices"
    d.mkdir(parents=True, exist_ok=True)
    return d


def list_invoices(settings: Settings | None = None) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in sorted(_invoices_dir(settings).glob("*.meta.json")):
        meta = load_json(path)
        if isinstance(meta, dict):
            rows.append(meta)
    rows.sort(key=lambda m: str(m.get("created_at") or ""), reverse=True)
    return rows


def save_invoice(
    *,
    filename: str,
    content: bytes,
    settings: Settings | None = None,
    transaction_id: str | None = None,
    note: str = "",
    amount: float | None = None,
) -> dict[str, Any]:
    if not content:
        raise FinanceLedgerError("ficheiro vazio")
    if len(content) > 15 * 1024 * 1024:
        raise FinanceLedgerError("fatura demasiado grande (max 15MB)")
    ext = Path(filename or "file.bin").suffix.lower() or ".bin"
    if ext not in INVOICE_EXTS:
        raise FinanceLedgerError(f"tipo nao suportado: {ext} (pdf/jpg/png/webp)")
    inv_id = uuid4().hex[:12]
    dest = _invoices_dir(settings) / f"{inv_id}{ext}"
    dest.write_bytes(content)
    meta = {
        "id": inv_id,
        "filename": Path(filename).name,
        "stored_as": dest.name,
        "content_type_hint": ext,
        "size": len(content),
        "transaction_id": transaction_id,
        "note": (note or "").strip()[:300],
        "amount": amount,
        "created_at": _now_iso(),
    }
    save_json(_invoices_dir(settings) / f"{inv_id}.meta.json", meta)
    return meta


# --- investments ---


def default_investments() -> dict[str, Any]:
    return {
        "ibkr": {"positions": [], "movements": []},
        "bitstack": {"positions": [], "movements": []},
        "updated_at": None,
    }


def get_investments(settings: Settings | None = None) -> dict[str, Any]:
    data = load_json(_root(settings) / "investments.json")
    out = default_investments()
    if isinstance(data, dict):
        for b in BROKERS:
            block = data.get(b)
            if isinstance(block, dict):
                out[b] = {
                    "positions": list(block.get("positions") or []),
                    "movements": list(block.get("movements") or []),
                }
        out["updated_at"] = data.get("updated_at")
    return out


def _save_investments(data: dict[str, Any], settings: Settings | None) -> None:
    data["updated_at"] = _now_iso()
    save_json(_root(settings) / "investments.json", data)


def upsert_position(
    settings: Settings | None = None,
    *,
    broker: str,
    symbol: str,
    qty: float,
    avg_cost: float | None = None,
    currency: str = "EUR",
) -> dict[str, Any]:
    b = (broker or "").strip().lower()
    if b not in BROKERS:
        raise FinanceLedgerError(f"broker invalido: {broker}")
    sym = (symbol or "").strip().upper()
    if not sym:
        raise FinanceLedgerError("symbol em falta")
    data = get_investments(settings)
    positions = list(data[b]["positions"])
    found = False
    for p in positions:
        if str(p.get("symbol") or "").upper() == sym:
            p["qty"] = float(qty)
            if avg_cost is not None:
                p["avg_cost"] = float(avg_cost)
            p["currency"] = (currency or "EUR").upper()[:3]
            p["updated_at"] = _now_iso()
            found = True
            break
    if not found:
        positions.append(
            {
                "id": uuid4().hex[:10],
                "symbol": sym,
                "qty": float(qty),
                "avg_cost": float(avg_cost) if avg_cost is not None else None,
                "currency": (currency or "EUR").upper()[:3],
                "updated_at": _now_iso(),
            }
        )
    data[b]["positions"] = positions
    _save_investments(data, settings)
    return {"ok": True, "broker": b, "positions": positions}


def add_investment_movement(
    settings: Settings | None = None,
    *,
    broker: str,
    kind: str,
    symbol: str | None = None,
    qty: float | None = None,
    amount: float | None = None,
    currency: str = "EUR",
    mv_date: str | None = None,
    note: str = "",
) -> dict[str, Any]:
    b = (broker or "").strip().lower()
    if b not in BROKERS:
        raise FinanceLedgerError(f"broker invalido: {broker}")
    k = (kind or "").strip().lower()
    if k not in ("buy", "sell", "deposit", "withdraw", "transfer"):
        raise FinanceLedgerError(f"kind invalido: {kind}")
    row = {
        "id": uuid4().hex[:10],
        "kind": k,
        "symbol": (symbol or "").strip().upper() or None,
        "qty": float(qty) if qty is not None else None,
        "amount": float(amount) if amount is not None else None,
        "currency": (currency or "EUR").upper()[:3],
        "date": (mv_date or date.today().isoformat())[:10],
        "note": (note or "").strip()[:300],
        "created_at": _now_iso(),
    }
    data = get_investments(settings)
    data[b]["movements"] = [row] + list(data[b]["movements"])
    _save_investments(data, settings)
    return row


def _norm_header(h: str) -> str:
    return re.sub(r"[^a-z0-9]", "", (h or "").casefold())


def import_ibkr_csv(text: str, settings: Settings | None = None) -> dict[str, Any]:
    """Tolerant import of IBKR activity-like CSV (Date/Symbol/Quantity/Amount)."""
    if not (text or "").strip():
        raise FinanceLedgerError("CSV vazio")
    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        raise FinanceLedgerError("CSV sem cabecalhos")
    cmap = {_norm_header(h): h for h in reader.fieldnames}

    def col(*names: str) -> str | None:
        for n in names:
            if _norm_header(n) in cmap:
                return cmap[_norm_header(n)]
        return None

    c_date = col("Date", "TradeDate", "SettleDate")
    c_sym = col("Symbol", "UnderlyingSymbol")
    c_qty = col("Quantity", "Qty")
    c_amt = col("Amount", "Proceeds", "NetCash", "TradeMoney")
    c_cur = col("CurrencyPrimary", "Currency", "Curr")

    imported = 0
    positions_touched: dict[str, float] = {}
    for row in reader:
        if not isinstance(row, dict):
            continue
        sym = (row.get(c_sym) or "").strip().upper() if c_sym else ""
        if not sym or sym in ("TOTAL", "NAN"):
            continue
        qty_raw = (row.get(c_qty) or "").replace(",", "") if c_qty else ""
        amt_raw = (row.get(c_amt) or "").replace(",", "") if c_amt else ""
        try:
            qty = float(qty_raw) if qty_raw else None
        except ValueError:
            qty = None
        try:
            amount = float(amt_raw) if amt_raw else None
        except ValueError:
            amount = None
        if qty is None and amount is None:
            continue
        kind = "buy"
        if qty is not None and qty < 0:
            kind = "sell"
        elif amount is not None and amount > 0 and (qty is None or qty == 0):
            kind = "deposit"
        d = (row.get(c_date) or date.today().isoformat())[:10] if c_date else date.today().isoformat()
        # Normalize MM/DD/YYYY roughly
        if "/" in d and len(d.split("/")[0]) <= 2:
            parts = d.split("/")
            if len(parts) == 3:
                try:
                    d = date(int(parts[2]), int(parts[0]), int(parts[1])).isoformat()
                except ValueError:
                    pass
        cur = (row.get(c_cur) or "USD") if c_cur else "USD"
        add_investment_movement(
            settings,
            broker="ibkr",
            kind=kind,
            symbol=sym,
            qty=abs(qty) if qty is not None else None,
            amount=amount,
            currency=str(cur)[:3],
            mv_date=d,
            note="ibkr_csv",
        )
        if qty is not None:
            positions_touched[sym] = positions_touched.get(sym, 0.0) + float(qty)
        imported += 1

    for sym, qdelta in positions_touched.items():
        data = get_investments(settings)
        existing = next(
            (
                p
                for p in data["ibkr"]["positions"]
                if str(p.get("symbol") or "").upper() == sym
            ),
            None,
        )
        new_qty = float(existing.get("qty") or 0) + qdelta if existing else qdelta
        upsert_position(
            settings,
            broker="ibkr",
            symbol=sym,
            qty=new_qty,
            avg_cost=existing.get("avg_cost") if existing else None,
            currency=(existing or {}).get("currency") or "USD",
        )

    return {"ok": True, "imported": imported, "symbols": list(positions_touched.keys())}


def investments_summary(settings: Settings | None = None) -> dict[str, Any]:
    data = get_investments(settings)
    brokers: dict[str, Any] = {}
    for b in BROKERS:
        positions = data[b]["positions"]
        cost = 0.0
        for p in positions:
            q = float(p.get("qty") or 0)
            ac = p.get("avg_cost")
            if ac is not None:
                cost += q * float(ac)
        brokers[b] = {
            "positions_count": len(positions),
            "movements_count": len(data[b]["movements"]),
            "cost_basis_approx": round(cost, 2),
            "positions": positions[:50],
        }
    return {"ok": True, "brokers": brokers, "updated_at": data.get("updated_at")}


# --- month summary ---


def month_summary(
    settings: Settings | None = None,
    *,
    year: int | None = None,
    month: int | None = None,
) -> dict[str, Any]:
    today = date.today()
    y = year or today.year
    m = month or today.month
    profile = get_profile(settings)
    txs = list_transactions(settings, year=y, month=m, limit=500)
    income = sum(float(t["amount"]) for t in txs if float(t.get("amount") or 0) > 0)
    expenses = sum(
        abs(float(t["amount"])) for t in txs if float(t.get("amount") or 0) < 0
    )
    salary = profile.get("salary_monthly")
    salary_f = float(salary) if salary is not None else 0.0
    imputed = monthly_imputed_recurring(settings)
    inv = investments_summary(settings)
    remaining = salary_f + income - expenses - imputed["total"]
    return {
        "ok": True,
        "year": y,
        "month": m,
        "currency": profile.get("currency") or "EUR",
        "salary_monthly": salary,
        "income_extra": round(income, 2),
        "expenses": round(expenses, 2),
        "recurring_imputed": imputed["total"],
        "recurring_breakdown": imputed["items"],
        "remaining": round(remaining, 2),
        "transactions_count": len(txs),
        "transactions": txs[:40],
        "investments": inv,
    }
