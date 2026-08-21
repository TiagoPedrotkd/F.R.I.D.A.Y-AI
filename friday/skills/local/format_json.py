"""Validate and pretty-print JSON."""

from __future__ import annotations

import json
from typing import Any

from friday.skills.base import SkillResult


class FormatJsonSkill:
    name = "format_json"
    description = (
        "Valida e formata JSON (pretty-print). "
        "Usa quando pedirem formatar, organizar ou validar JSON."
    )
    parameters: dict[str, Any] = {
        "type": "object",
        "properties": {
            "json_text": {
                "type": "string",
                "description": "String JSON a formatar",
            }
        },
        "required": ["json_text"],
    }

    async def execute(self, arguments: dict[str, Any]) -> SkillResult:
        raw = arguments.get("json_text") or arguments.get("text") or ""
        raw = str(raw).strip()
        if not raw:
            return SkillResult(
                success=False,
                content="",
                error="Preciso do JSON. Cola o texto a formatar.",
            )
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            return SkillResult(
                success=False,
                content="",
                error=f"JSON invalido: {exc.msg} (linha {exc.lineno}).",
            )
        pretty = json.dumps(data, indent=2, ensure_ascii=False)
        return SkillResult(
            success=True,
            content=f"JSON formatado:\n{pretty}",
            metadata={"valid": True},
        )
