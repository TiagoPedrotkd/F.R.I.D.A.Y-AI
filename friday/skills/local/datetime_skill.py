"""Current date/time skill."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from friday.skills.base import SkillResult

_WEEKDAYS_PT = (
    "segunda-feira",
    "terca-feira",
    "quarta-feira",
    "quinta-feira",
    "sexta-feira",
    "sabado",
    "domingo",
)

_TZ_ALIASES = {
    "portugal": "Europe/Lisbon",
    "lisboa": "Europe/Lisbon",
    "lisbon": "Europe/Lisbon",
    "seul": "Asia/Seoul",
    "seoul": "Asia/Seoul",
    "coreia": "Asia/Seoul",
    "london": "Europe/London",
    "londres": "Europe/London",
    "new york": "America/New_York",
    "ny": "America/New_York",
    "utc": "UTC",
}


def resolve_timezone(name: str | None) -> str:
    if not name:
        return "Europe/Lisbon"
    key = name.strip().casefold()
    return _TZ_ALIASES.get(key, name.strip())


class DateTimeSkill:
    name = "get_current_datetime"
    description = (
        "OBRIGATORIO para hora, data ou dia da semana. "
        "Nunca digas que nao tens acesso a tempo real. "
        "Aceita timezone IANA ou aliases (Portugal, Seul)."
    )
    parameters: dict[str, Any] = {
        "type": "object",
        "properties": {
            "timezone": {
                "type": "string",
                "description": "IANA timezone or alias, e.g. Europe/Lisbon, Portugal, Seul",
                "default": "Europe/Lisbon",
            }
        },
        "required": [],
    }

    async def execute(self, arguments: dict[str, Any]) -> SkillResult:
        tz_name = resolve_timezone(arguments.get("timezone"))
        try:
            now = datetime.now(ZoneInfo(tz_name))
            label = tz_name
        except Exception:
            now = datetime.now().astimezone()
            label = now.tzname() or "local"

        weekday = _WEEKDAYS_PT[now.weekday()]
        formatted = now.strftime("%H:%M de %d/%m/%Y")
        return SkillResult(
            success=True,
            content=f"Sao {formatted}, {weekday} ({label}).",
            metadata={"iso": now.isoformat(), "weekday": weekday},
        )


class LegacyTimeSkill(DateTimeSkill):
    """Alias for older tool name."""

    name = "get_current_time"
