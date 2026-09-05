"""Health sync + local cache — Google Fitness / Fitbit / ficheiro (Fase 4)."""

from __future__ import annotations

import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from friday.config import Settings, get_settings
from friday.integrations import integrations_root
from friday.integrations.google_oauth import GoogleOAuthError, google_connected, google_request


class HealthSyncError(RuntimeError):
    pass


def _health_root(settings: Settings | None = None) -> Path:
    return integrations_root(settings) / "health"


def _daily_path(day: date, settings: Settings | None = None) -> Path:
    return _health_root(settings) / "daily" / f"{day.isoformat()}.json"


def _summary_path(settings: Settings | None = None) -> Path:
    return _health_root(settings) / "summary.json"


def empty_day(day: date | None = None, *, source: str = "none") -> dict[str, Any]:
    d = day or date.today()
    return {
        "date": d.isoformat(),
        "steps": None,
        "sleep_hours": None,
        "resting_hr": None,
        "hrv": None,
        "active_minutes": None,
        "source": source,
        "synced_at": None,
    }


def write_day(payload: dict[str, Any], settings: Settings | None = None) -> dict[str, Any]:
    settings = settings or get_settings()
    day_s = str(payload.get("date") or date.today().isoformat())
    day = date.fromisoformat(day_s)
    path = _daily_path(day, settings)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    # Keep summary as "today" mirror when applicable
    if day == date.today():
        _summary_path(settings).write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload


def read_day(day: str | date, settings: Settings | None = None) -> dict[str, Any]:
    settings = settings or get_settings()
    if isinstance(day, str):
        d = date.fromisoformat(day.strip())
    else:
        d = day
    path = _daily_path(d, settings)
    if path.is_file():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return {"ok": True, "data": data, "path": str(path)}
        except (OSError, json.JSONDecodeError) as exc:
            return {"ok": False, "error": str(exc)}
    # Fallback summary for today
    if d == date.today():
        sp = _summary_path(settings)
        if sp.is_file():
            try:
                return {
                    "ok": True,
                    "data": json.loads(sp.read_text(encoding="utf-8")),
                    "path": str(sp),
                }
            except (OSError, json.JSONDecodeError) as exc:
                return {"ok": False, "error": str(exc)}
    return {"ok": False, "error": f"Sem dados para {d.isoformat()}", "data": empty_day(d)}


def list_days(settings: Settings | None = None, *, limit: int = 14) -> dict[str, Any]:
    settings = settings or get_settings()
    root = _health_root(settings) / "daily"
    rows: list[dict[str, Any]] = []
    if root.is_dir():
        files = sorted(root.glob("*.json"), reverse=True)
        for path in files[: max(1, limit)]:
            try:
                rows.append(json.loads(path.read_text(encoding="utf-8")))
            except (OSError, json.JSONDecodeError):
                continue
    if not rows:
        today = read_day(date.today(), settings)
        if today.get("ok") and today.get("data"):
            rows = [today["data"]]
    return {"ok": True, "count": len(rows), "days": rows}


def health_status(settings: Settings | None = None) -> dict[str, Any]:
    settings = settings or get_settings()
    summary = read_day(date.today(), settings)
    return {
        "ok": True,
        "google_connected": google_connected(settings),
        "cache_ok": bool(summary.get("ok")),
        "summary": summary.get("data") if summary.get("ok") else None,
        "error": summary.get("error") if not summary.get("ok") else None,
    }


def _ms_bucket(day: date) -> tuple[int, int]:
    start = datetime(day.year, day.month, day.day, tzinfo=timezone.utc)
    end = start + timedelta(days=1)
    return int(start.timestamp() * 1000), int(end.timestamp() * 1000)


def _fitness_aggregate(
    data_type: str,
    day: date,
    settings: Settings,
) -> float | None:
    start_ms, end_ms = _ms_bucket(day)
    body = {
        "aggregateBy": [{"dataTypeName": data_type}],
        "bucketByTime": {"durationMillis": 86400000},
        "startTimeMillis": start_ms,
        "endTimeMillis": end_ms,
    }
    data = google_request(
        "https://www.googleapis.com/fitness/v1/users/me/dataset:aggregate",
        settings=settings,
        method="POST",
        body=body,
    )
    buckets = data.get("bucket") or []
    total = 0.0
    found = False
    for bucket in buckets:
        for dataset in bucket.get("dataset") or []:
            for point in dataset.get("point") or []:
                for val in point.get("value") or []:
                    if "intVal" in val:
                        total += float(val["intVal"])
                        found = True
                    elif "fpVal" in val:
                        total += float(val["fpVal"])
                        found = True
    return total if found else None


def sync_from_google_fitness(
    settings: Settings | None = None,
    *,
    days: int = 7,
) -> dict[str, Any]:
    settings = settings or get_settings()
    if not settings.google_enabled or not google_connected(settings):
        raise HealthSyncError("Google nao ligado — conecta em Definições.")
    synced: list[dict[str, Any]] = []
    errors: list[str] = []
    today = date.today()
    for i in range(max(1, days)):
        day = today - timedelta(days=i)
        row = empty_day(day, source="google_fitness")
        try:
            steps = _fitness_aggregate(
                "com.google.step_count.delta", day, settings
            )
            if steps is not None:
                row["steps"] = int(steps)
            active = _fitness_aggregate(
                "com.google.active_minutes", day, settings
            )
            if active is not None:
                row["active_minutes"] = int(active)
            # Sleep / HR often need specific scopes or may be empty
            try:
                sleep_ms = _fitness_aggregate("com.google.sleep.segment", day, settings)
                if sleep_ms is not None and sleep_ms > 0:
                    # segment aggregates are not always hours; leave None if absurd
                    if sleep_ms < 24:
                        row["sleep_hours"] = round(float(sleep_ms), 2)
            except GoogleOAuthError:
                pass
            try:
                hr = _fitness_aggregate("com.google.heart_rate.bpm", day, settings)
                if hr is not None and 30 < hr < 220:
                    row["resting_hr"] = round(float(hr), 1)
            except GoogleOAuthError:
                pass
            row["synced_at"] = datetime.now(timezone.utc).isoformat()
            write_day(row, settings)
            synced.append(row)
        except GoogleOAuthError as exc:
            errors.append(f"{day.isoformat()}: {exc}")
            break
    if not synced and errors:
        raise HealthSyncError(errors[0])
    return {
        "ok": True,
        "synced": len(synced),
        "days": synced,
        "errors": errors,
        "source": "google_fitness",
    }


def sync_health(settings: Settings | None = None, *, days: int = 7) -> dict[str, Any]:
    """Best-effort sync: Google Fitness first; else leave cache untouched with clear error."""
    settings = settings or get_settings()
    try:
        return sync_from_google_fitness(settings, days=days)
    except HealthSyncError:
        raise
    except GoogleOAuthError as exc:
        raise HealthSyncError(str(exc)) from exc
