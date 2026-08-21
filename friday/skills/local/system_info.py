"""Local machine system information."""

from __future__ import annotations

import platform
import sys
from typing import Any

from friday.skills.base import SkillResult


class SystemInfoSkill:
    name = "get_system_info"
    description = (
        "Informacoes deste computador: sistema operativo, arquitectura, "
        "versao Python e hostname."
    )
    parameters: dict[str, Any] = {
        "type": "object",
        "properties": {},
        "required": [],
    }

    async def execute(self, arguments: dict[str, Any]) -> SkillResult:
        info = {
            "system": platform.system(),
            "release": platform.release(),
            "version": platform.version(),
            "machine": platform.machine(),
            "processor": platform.processor() or "n/d",
            "python": sys.version.split()[0],
            "hostname": platform.node(),
        }
        content = (
            f"Sistema: {info['system']} {info['release']} ({info['machine']}). "
            f"Python {info['python']}. Hostname: {info['hostname']}."
        )
        return SkillResult(success=True, content=content, metadata=info)
