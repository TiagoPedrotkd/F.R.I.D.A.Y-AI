"""External / local integrations for FRIDAY (Phase 5)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from friday.config import Settings, get_settings


def integrations_root(settings: Settings | None = None) -> Path:
    settings = settings or get_settings()
    # data/ sits next to prefs_dir parent
    return Path(settings.prefs_dir).parent / "integrations"


def get_enabled_integrations(settings: Settings | None = None) -> dict[str, bool]:
    settings = settings or get_settings()
    try:
        from friday.memory.prefs_store import PrefsStore

        prefs = PrefsStore(settings.prefs_dir).get("default")
        raw = prefs.get("integrations_enabled")
        if isinstance(raw, dict):
            return {
                "weather": bool(raw.get("weather", True)),
                "health_file": bool(raw.get("health_file", True)),
                "notion_export": bool(raw.get("notion_export", True)),
                "strava_file": bool(raw.get("strava_file", True)),
                "home_assistant": bool(raw.get("home_assistant", True)),
            }
    except Exception:
        pass
    return {
        "weather": True,
        "health_file": True,
        "notion_export": True,
        "strava_file": True,
        "home_assistant": True,
    }


def fetch_weather(lat: float = 38.72, lon: float = -9.14) -> dict[str, Any]:
    """Open-Meteo — no API key required."""
    import urllib.parse
    import urllib.request

    qs = urllib.parse.urlencode(
        {
            "latitude": lat,
            "longitude": lon,
            "current": "temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m",
            "timezone": "Europe/Lisbon",
        }
    )
    url = f"https://api.open-meteo.com/v1/forecast?{qs}"
    with urllib.request.urlopen(url, timeout=8) as resp:  # noqa: S310
        data = json.loads(resp.read().decode("utf-8"))
    cur = data.get("current") or {}
    return {
        "provider": "open-meteo",
        "latitude": lat,
        "longitude": lon,
        "temperature_c": cur.get("temperature_2m"),
        "humidity": cur.get("relative_humidity_2m"),
        "weather_code": cur.get("weather_code"),
        "wind_speed": cur.get("wind_speed_10m"),
        "time": cur.get("time"),
    }


def read_health_summary(settings: Settings | None = None) -> dict[str, Any]:
    root = integrations_root(settings)
    path = root / "health" / "summary.json"
    if not path.is_file():
        return {
            "ok": False,
            "error": (
                f"Sem dados de saude. Coloca um JSON em {path} "
                "(ex. sleep_hours, hrv, steps) ou exporta do Apple Health/Fitbit."
            ),
        }
    try:
        return {"ok": True, "data": json.loads(path.read_text(encoding="utf-8")), "path": str(path)}
    except (OSError, json.JSONDecodeError) as exc:
        return {"ok": False, "error": str(exc)}


def search_personal_notes(query: str, settings: Settings | None = None, limit: int = 5) -> dict[str, Any]:
    root = integrations_root(settings) / "notion_export"
    if not root.is_dir():
        return {
            "ok": False,
            "error": f"Pasta Notion/notes ausente: {root}. Exporta markdown/JSON para la.",
            "hits": [],
        }
    q = (query or "").casefold()
    hits: list[dict[str, str]] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in {".md", ".txt", ".json"}:
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        if q and q not in text.casefold() and q not in path.name.casefold():
            continue
        hits.append({"path": str(path), "excerpt": text[:400]})
        if len(hits) >= limit:
            break
    return {"ok": True, "hits": hits, "root": str(root)}
