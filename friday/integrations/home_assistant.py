"""Home Assistant REST client (Fase 3.0 read + 3.1 call_service)."""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from friday.config import Settings, get_settings

ENERGY_DEVICE_CLASSES = frozenset({"power", "energy", "gas", "monetary"})
ENERGY_UNITS = frozenset(
    {
        "w",
        "kw",
        "kwh",
        "wh",
        "mwh",
        "mw",
        "m³",
        "m3",
        "ft³",
        "ft3",
        "€",
        "eur",
        "$",
        "usd",
    }
)
ALLOWED_SERVICES = frozenset({"turn_on", "turn_off", "toggle"})


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
    if not (settings.ha_token or "").strip():
        raise HomeAssistantError(
            "HA_TOKEN vazio. Cria um Long-Lived Access Token no HA "
            "(Perfil → Security) e mete-o no .env; reinicia o agent-api."
        )
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


def _entity_row(st: dict[str, Any]) -> dict[str, Any]:
    attrs = st.get("attributes") or {}
    if not isinstance(attrs, dict):
        attrs = {}
    row: dict[str, Any] = {
        "entity_id": str(st.get("entity_id") or ""),
        "state": st.get("state"),
        "friendly_name": attrs.get("friendly_name"),
    }
    if attrs.get("device_class") is not None:
        row["device_class"] = attrs.get("device_class")
    if attrs.get("unit_of_measurement") is not None:
        row["unit_of_measurement"] = attrs.get("unit_of_measurement")
    if attrs.get("brightness") is not None:
        row["brightness"] = attrs.get("brightness")
    if attrs.get("supported_color_modes") is not None:
        row["supported_color_modes"] = attrs.get("supported_color_modes")
    return row


def get_status(settings: Settings | None = None) -> dict[str, Any]:
    settings = settings or get_settings()
    data = ha_request("/api/", settings=settings)
    return {
        "ok": True,
        "api": data,
        "url": settings.ha_url,
    }


def list_states(
    settings: Settings | None = None,
    *,
    domain: str | None = None,
    limit: int = 200,
) -> dict[str, Any]:
    states = ha_request("/api/states", settings=settings)
    if not isinstance(states, list):
        return {"ok": False, "error": "Resposta inesperada de /api/states", "entities": []}
    domain = (domain or "").strip().casefold()
    rows: list[dict[str, Any]] = []
    for st in states:
        if not isinstance(st, dict):
            continue
        eid = str(st.get("entity_id") or "")
        if domain and not eid.casefold().startswith(f"{domain}."):
            continue
        rows.append(_entity_row(st))
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


def _is_energy_sensor(st: dict[str, Any]) -> bool:
    eid = str(st.get("entity_id") or "")
    if not eid.casefold().startswith("sensor."):
        return False
    attrs = st.get("attributes") or {}
    if not isinstance(attrs, dict):
        return False
    dc = str(attrs.get("device_class") or "").casefold()
    if dc in ENERGY_DEVICE_CLASSES:
        return True
    unit = str(attrs.get("unit_of_measurement") or "").strip().casefold()
    return unit in ENERGY_UNITS


def list_energy_sensors(
    settings: Settings | None = None,
    *,
    limit: int = 80,
) -> dict[str, Any]:
    states = ha_request("/api/states", settings=settings)
    if not isinstance(states, list):
        return {"ok": False, "error": "Resposta inesperada de /api/states", "entities": []}
    rows: list[dict[str, Any]] = []
    for st in states:
        if not isinstance(st, dict) or not _is_energy_sensor(st):
            continue
        rows.append(_entity_row(st))
        if len(rows) >= max(1, limit):
            break
    return {"ok": True, "count": len(rows), "entities": rows}


def call_service(
    domain: str,
    service: str,
    entity_id: str,
    *,
    settings: Settings | None = None,
    data: dict[str, Any] | None = None,
) -> dict[str, Any]:
    domain = (domain or "").strip().casefold()
    service = (service or "").strip().casefold()
    eid = (entity_id or "").strip()
    if not domain or not eid:
        raise HomeAssistantError("domain e entity_id obrigatorios.")
    if service not in ALLOWED_SERVICES:
        raise HomeAssistantError(
            f"Servico nao permitido: {service}. Use: {', '.join(sorted(ALLOWED_SERVICES))}."
        )
    body: dict[str, Any] = {"entity_id": eid}
    if data:
        for key, val in data.items():
            if key == "entity_id":
                continue
            body[key] = val
    path = f"/api/services/{urllib.parse.quote(domain)}/{urllib.parse.quote(service)}"
    result = ha_request(path, settings=settings, method="POST", body=body)
    return {
        "ok": True,
        "domain": domain,
        "service": service,
        "entity_id": eid,
        "result": result,
    }


def domain_from_entity_id(entity_id: str) -> str:
    eid = (entity_id or "").strip()
    if "." not in eid:
        return ""
    return eid.split(".", 1)[0].casefold()
