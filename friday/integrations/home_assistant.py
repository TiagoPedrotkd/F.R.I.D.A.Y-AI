"""Home Assistant REST client (Fase 3.0 — read-only)."""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from friday.config import Settings, get_settings


class HomeAssistantError(RuntimeError):
    pass


def _headers(token: str) -> dict[str, str]:
    h = {"Content-Type": "application/json"}
    if token:
        h["Authorization"] = f"Bearer {token}"
    return h


def ha_request(
    path: str,
    *,
    settings: Settings | None = None,
    method: str = "GET",
    body: dict[str, Any] | None = None,
    timeout: float = 8.0,
) -> Any:
    settings = settings or get_settings()
    if not settings.ha_enabled:
        raise HomeAssistantError("Home Assistant desactivado (HA_ENABLED=false).")
    base = (settings.ha_url or "").rstrip("/")
    if not base:
        raise HomeAssistantError("HA_URL vazio.")
    url = f"{base}{path}"
    data = None
    if body is not None:
        data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers=_headers(settings.ha_token or ""),
        method=method,
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310
            raw = resp.read().decode("utf-8")
            if not raw:
                return {"ok": True, "status": resp.status}
            return json.loads(raw)
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="ignore")[:300]
        raise HomeAssistantError(f"HA HTTP {exc.code}: {detail}") from exc
    except Exception as exc:
        raise HomeAssistantError(f"HA unreachable: {exc}") from exc


def get_status(settings: Settings | None = None) -> dict[str, Any]:
    data = ha_request("/api/", settings=settings)
    return {"ok": True, "api": data, "url": (settings or get_settings()).ha_url}


def list_states(
    settings: Settings | None = None,
    *,
    domain: str | None = None,
    limit: int = 40,
) -> dict[str, Any]:
    states = ha_request("/api/states", settings=settings)
    if not isinstance(states, list):
        return {"ok": False, "error": "Resposta inesperada de /api/states", "entities": []}
    domain = (domain or "").strip().casefold()
    rows: list[dict[str, Any]] = []
    for st in states:
        eid = str(st.get("entity_id") or "")
        if domain and not eid.casefold().startswith(f"{domain}."):
            continue
        rows.append(
            {
                "entity_id": eid,
                "state": st.get("state"),
                "friendly_name": (st.get("attributes") or {}).get("friendly_name"),
            }
        )
        if len(rows) >= max(1, limit):
            break
    return {"ok": True, "count": len(rows), "entities": rows, "domain": domain or None}


def get_state(entity_id: str, settings: Settings | None = None) -> dict[str, Any]:
    eid = urllib.parse.quote((entity_id or "").strip(), safe="._")
    if not eid:
        return {"ok": False, "error": "entity_id obrigatorio"}
    st = ha_request(f"/api/states/{eid}", settings=settings)
    if not isinstance(st, dict):
        return {"ok": False, "error": "Resposta inesperada"}
    return {
        "ok": True,
        "entity_id": st.get("entity_id"),
        "state": st.get("state"),
        "attributes": st.get("attributes") or {},
    }
