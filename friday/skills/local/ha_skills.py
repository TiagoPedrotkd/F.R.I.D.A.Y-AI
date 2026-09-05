"""Home Assistant skills — Fase 3.0 read-only + 3.1 ha_call_service (gated)."""

from __future__ import annotations

from typing import Any

from friday.config import Settings, get_settings
from friday.integrations import get_enabled_integrations
from friday.integrations.home_assistant import (
    ALLOWED_SERVICES,
    HomeAssistantError,
    call_service,
    domain_from_entity_id,
    get_state,
    get_status,
    list_states,
)
from friday.skills.base import SkillResult
from friday.skills.gated import confirmation_required_result, is_confirmed


def _ha_pref_ok(settings: Settings) -> bool:
    enabled = get_enabled_integrations(settings)
    return bool(enabled.get("home_assistant", True))


def _guard(settings: Settings) -> SkillResult | None:
    if not settings.ha_enabled:
        return SkillResult(
            success=False,
            content="",
            error="Home Assistant desactivado (HA_ENABLED=false no .env).",
        )
    if not _ha_pref_ok(settings):
        return SkillResult(
            success=False,
            content="",
            error="Integracao home_assistant desactivada nas preferencias.",
        )
    return None


class HaGetStatusSkill:
    name = "ha_get_status"
    description = (
        "Estado da ligacao ao Home Assistant (API local). "
        "Usa para 'estado da casa', 'home assistant online'."
    )
    parameters: dict[str, Any] = {"type": "object", "properties": {}, "required": []}

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()

    async def execute(self, arguments: dict[str, Any]) -> SkillResult:
        blocked = _guard(self._settings)
        if blocked:
            return blocked
        try:
            data = get_status(self._settings)
        except HomeAssistantError as exc:
            return SkillResult(success=False, content="", error=str(exc))
        msg = (
            f"Home Assistant OK em {data.get('url')}. "
            f"API: {data.get('api')}"
        )
        return SkillResult(success=True, content=msg, metadata={"kind": "ha", "data": data})


class HaListEntitiesSkill:
    name = "ha_list_entities"
    description = (
        "Lista entidades do Home Assistant (filtro domain opcional: light, sensor, switch)."
    )
    parameters: dict[str, Any] = {
        "type": "object",
        "properties": {
            "domain": {"type": "string", "description": "Ex. light, sensor, binary_sensor"},
            "limit": {"type": "integer", "default": 30},
        },
        "required": [],
    }

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()

    async def execute(self, arguments: dict[str, Any]) -> SkillResult:
        blocked = _guard(self._settings)
        if blocked:
            return blocked
        domain = arguments.get("domain")
        limit = int(arguments.get("limit") or 30)
        try:
            data = list_states(self._settings, domain=domain, limit=limit)
        except HomeAssistantError as exc:
            return SkillResult(success=False, content="", error=str(exc))
        lines = [
            f"{e['entity_id']}: {e['state']}"
            + (f" ({e['friendly_name']})" if e.get("friendly_name") else "")
            for e in data.get("entities") or []
        ]
        body = "\n".join(lines) if lines else "Sem entidades (filtro vazio ou HA sem devices)."
        return SkillResult(
            success=True,
            content=f"Entidades HA ({data.get('count', 0)}):\n{body}",
            metadata={"kind": "ha", "data": data},
        )


class HaGetStateSkill:
    name = "ha_get_state"
    description = "Obtem o estado de uma entidade HA (entity_id, ex. light.sala)."
    parameters: dict[str, Any] = {
        "type": "object",
        "properties": {
            "entity_id": {"type": "string", "description": "ex. sensor.temperatura_sala"},
        },
        "required": ["entity_id"],
    }

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()

    async def execute(self, arguments: dict[str, Any]) -> SkillResult:
        blocked = _guard(self._settings)
        if blocked:
            return blocked
        eid = (arguments.get("entity_id") or "").strip()
        if not eid:
            return SkillResult(success=False, content="", error="entity_id obrigatorio.")
        try:
            data = get_state(eid, self._settings)
        except HomeAssistantError as exc:
            return SkillResult(success=False, content="", error=str(exc))
        if not data.get("ok"):
            return SkillResult(success=False, content="", error=data.get("error") or "erro")
        name = (data.get("attributes") or {}).get("friendly_name") or eid
        return SkillResult(
            success=True,
            content=f"{name} ({data.get('entity_id')}): {data.get('state')}",
            metadata={"kind": "ha", "data": data},
        )


class HaCallServiceSkill:
    name = "ha_call_service"
    description = (
        "Liga, desliga ou faz toggle de uma entidade HA (light/switch). "
        "Requer confirmacao. Args: entity_id, service (turn_on|turn_off|toggle)."
    )
    parameters: dict[str, Any] = {
        "type": "object",
        "properties": {
            "entity_id": {
                "type": "string",
                "description": "ex. light.sala ou switch.tomada",
            },
            "service": {
                "type": "string",
                "description": "turn_on | turn_off | toggle",
            },
            "domain": {
                "type": "string",
                "description": "Opcional; inferido de entity_id se omitido",
            },
            "confirmed": {"type": "boolean"},
        },
        "required": ["entity_id", "service"],
    }

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()

    async def execute(self, arguments: dict[str, Any]) -> SkillResult:
        blocked = _guard(self._settings)
        if blocked:
            return blocked
        eid = (arguments.get("entity_id") or "").strip()
        service = (arguments.get("service") or "").strip().casefold()
        domain = (arguments.get("domain") or "").strip().casefold() or domain_from_entity_id(
            eid
        )
        if not eid:
            return SkillResult(success=False, content="", error="entity_id obrigatorio.")
        if service not in ALLOWED_SERVICES:
            return SkillResult(
                success=False,
                content="",
                error=f"service invalido: {service}. Use turn_on, turn_off ou toggle.",
            )
        if not domain:
            return SkillResult(
                success=False,
                content="",
                error="domain em falta (entity_id deve ser domain.name).",
            )
        if domain not in {"light", "switch", "fan", "input_boolean", "media_player"}:
            return SkillResult(
                success=False,
                content="",
                error=f"Dominio nao permitido para accoes UI/chat: {domain}.",
            )

        labels = {
            "turn_on": "ligar",
            "turn_off": "desligar",
            "toggle": "alternar",
        }
        summary = f"{labels.get(service, service)} {eid}"
        payload = {
            "entity_id": eid,
            "service": service,
            "domain": domain,
        }
        if not is_confirmed(arguments):
            return confirmation_required_result(
                action="ha_call_service",
                target=eid,
                summary=summary,
                consequences="Altera o estado do dispositivo no Home Assistant.",
                payload=payload,
                preview={"entity_id": eid, "service": service, "domain": domain},
            )

        try:
            data = call_service(domain, service, eid, settings=self._settings)
        except HomeAssistantError as exc:
            return SkillResult(success=False, content="", error=str(exc))
        return SkillResult(
            success=True,
            content=f"Feito: {summary}.",
            metadata={"kind": "ha", "data": data},
        )
