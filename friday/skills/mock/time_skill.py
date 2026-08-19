"""Returns the current local time."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from friday.skills.base import SkillResult


class TimeSkill:
    name = "get_current_time"
    description = (
        "Get the current date and time. Use when the user asks what time it is "
        "or the current date."
    )
    parameters: dict[str, Any] = {
        "type": "object",
        "properties": {
            "timezone": {
                "type": "string",
                "description": "IANA timezone, e.g. Europe/Lisbon",
                "default": "Europe/Lisbon",
            }
        },
        "required": [],
    }

    async def execute(self, arguments: dict[str, Any]) -> SkillResult:
        tz_name = arguments.get("timezone", "Europe/Lisbon")
        try:
            tz = ZoneInfo(tz_name)
        except Exception:
            return SkillResult(
                success=False,
                content="",
                error=f"Invalid timezone: {tz_name}",
            )
        now = datetime.now(tz)
        formatted = now.strftime("%H:%M de %d/%m/%Y")
        return SkillResult(
            success=True,
            content=f"Sao {formatted} ({tz_name}).",
            metadata={"iso": now.isoformat()},
        )
