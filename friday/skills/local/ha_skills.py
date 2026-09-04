"""Home Assistant skills — Fase 3.0 read-only."""

from __future__ import annotations

from typing import Any

from friday.config import Settings, get_settings
from friday.integrations import get_enabled_integrations
from friday.integrations.home_assistant import (
    HomeAssistantError,
    get_state,
    get_status,
    list_states,
)
from friday.skills.base import SkillResult


def _ha_pref_ok(settings: Settings) -> bool:
    enabled = get_enabled_integrations(settings)
    return bool(enabled.get("home_assistant", True))


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
        if not self._settings.ha_enabled:
            return SkillResult(
                success=False,
                content="",
                error="Home Assistant desactivado (HA_ENABLED=false no .env).",
            )
        if not _ha_pref_ok(self._settings):
            return SkillResult(
                success=False,
                content="",
                error="Integracao home_assistant desactivada nas preferencias.",
            )
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
        if not self._settings.ha_enabled or not _ha_pref_ok(self._settings):
            return SkillResult(
                success=False,
                content="",
                error="Home Assistant indisponivel ou desactivado.",
            )
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
        if not self._settings.ha_enabled or not _ha_pref_ok(self._settings):
            return SkillResult(
                success=False,
                content="",
                error="Home Assistant indisponivel ou desactivado.",
            )
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
