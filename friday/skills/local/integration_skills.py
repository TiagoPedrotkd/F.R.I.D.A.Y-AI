"""Integration skills — weather, health file, personal notes."""

from __future__ import annotations

from typing import Any

from friday.config import Settings, get_settings
from friday.integrations import (
    fetch_weather,
    get_enabled_integrations,
    read_health_summary,
    search_personal_notes,
)
from friday.skills.base import SkillResult


class GetWeatherSkill:
    name = "get_weather"
    description = "Tempo actual (Open-Meteo). Usa para 'que tempo esta', clima, temperatura."
    parameters: dict[str, Any] = {
        "type": "object",
        "properties": {
            "latitude": {"type": "number"},
            "longitude": {"type": "number"},
        },
        "required": [],
    }

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()

    async def execute(self, arguments: dict[str, Any]) -> SkillResult:
        enabled = get_enabled_integrations(self._settings)
        if not enabled.get("weather", True):
            return SkillResult(success=False, content="", error="Weather desactivado nas prefs.")
        lat = float(arguments.get("latitude") or 38.72)
        lon = float(arguments.get("longitude") or -9.14)
        try:
            data = fetch_weather(lat, lon)
        except Exception as exc:
            return SkillResult(success=False, content="", error=str(exc))
        content = (
            f"Tempo agora ({data.get('time')}): {data.get('temperature_c')}°C, "
            f"humidade {data.get('humidity')}%, vento {data.get('wind_speed')}."
        )
        return SkillResult(success=True, content=content, metadata={"kind": "weather", **data})


class GetHealthSummarySkill:
    name = "get_health_summary"
    description = (
        "Le resumo de saude local (cache Google Fitness / ficheiro). "
        "Usa para 'como dormi', 'passos de hoje', 'resumo de saude'."
    )
    parameters: dict[str, Any] = {"type": "object", "properties": {}, "required": []}

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()

    async def execute(self, arguments: dict[str, Any]) -> SkillResult:
        enabled = get_enabled_integrations(self._settings)
        if not enabled.get("health_file", True) and not enabled.get("google_health", True):
            return SkillResult(success=False, content="", error="Saude desactivada nas prefs.")
        result = read_health_summary(self._settings)
        if not result.get("ok"):
            return SkillResult(success=False, content="", error=str(result.get("error")))
        data = result.get("data") or {}
        return SkillResult(
            success=True,
            content=f"Resumo de saude: {data}",
            metadata={"kind": "health", **result},
        )


class GetHealthDaySkill:
    name = "get_health_day"
    description = "Le metricas de saude de um dia (YYYY-MM-DD) do cache local."
    parameters: dict[str, Any] = {
        "type": "object",
        "properties": {
            "date": {"type": "string", "description": "YYYY-MM-DD (default: hoje)"},
        },
        "required": [],
    }

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()

    async def execute(self, arguments: dict[str, Any]) -> SkillResult:
        from datetime import date as date_cls

        from friday.integrations.google_health import read_day

        day = str(arguments.get("date") or "").strip() or date_cls.today().isoformat()
        result = read_day(day, self._settings)
        if not result.get("ok"):
            return SkillResult(success=False, content="", error=str(result.get("error")))
        return SkillResult(
            success=True,
            content=f"Saude {day}: {result.get('data')}",
            metadata={"kind": "health", **result},
        )


class SearchPersonalNotesSkill:
    name = "search_personal_notes"
    description = "Pesquisa notas pessoais / export Notion em data/integrations/notion_export/."
    parameters: dict[str, Any] = {
        "type": "object",
        "properties": {"query": {"type": "string"}},
        "required": ["query"],
    }

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()

    async def execute(self, arguments: dict[str, Any]) -> SkillResult:
        enabled = get_enabled_integrations(self._settings)
        if not enabled.get("notion_export", True):
            return SkillResult(success=False, content="", error="Notes desactivado.")
        q = str(arguments.get("query") or "").strip()
        result = search_personal_notes(q, self._settings)
        if not result.get("ok"):
            return SkillResult(success=False, content="", error=str(result.get("error")))
        hits = result.get("hits") or []
        if not hits:
            return SkillResult(success=True, content="Nenhuma nota encontrada.", metadata=result)
        lines = [f"- {h['path']}: {h['excerpt'][:160]}…" for h in hits]
        return SkillResult(
            success=True,
            content="Notas:\n" + "\n".join(lines),
            metadata={"kind": "notes", **result},
        )
