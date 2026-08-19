"""Returns a short joke in Portuguese."""

from __future__ import annotations

import random
from typing import Any

from friday.skills.base import SkillResult

_JOKES = [
    "Porque e que o computador foi ao medico? Porque tinha un virus!",
    "O que e um pontinho verde no canto da sala? Um irmão mais novo do Pikachu perdido.",
    "Sabes qual e o cafe favorito dos programadores? Java.",
    "Porque e que os programadores confundem Halloween com Natal? Porque Oct 31 == Dec 25.",
    "O que e um terabyte? Um insecto muito pesado.",
]


class JokeSkill:
    name = "tell_joke"
    description = (
        "Tell a short joke in Portuguese. Use when the user asks for a joke "
        "or something funny."
    )
    parameters: dict[str, Any] = {
        "type": "object",
        "properties": {},
        "required": [],
    }

    async def execute(self, arguments: dict[str, Any]) -> SkillResult:
        joke = random.choice(_JOKES)
        return SkillResult(success=True, content=joke)
