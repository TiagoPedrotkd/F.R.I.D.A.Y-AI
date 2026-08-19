"""Skill registry and OpenAI tool export."""

from __future__ import annotations

from typing import Any

from friday.pipeline.errors import UnknownSkillError
from friday.skills.base import Skill, SkillResult


class SkillRegistry:
    def __init__(self) -> None:
        self._skills: dict[str, Skill] = {}

    def register(self, skill: Skill) -> None:
        if skill.name in self._skills:
            raise ValueError(f"Skill already registered: {skill.name}")
        self._skills[skill.name] = skill

    def get(self, name: str) -> Skill:
        skill = self._skills.get(name)
        if skill is None:
            raise UnknownSkillError(f"Unknown skill: {name}")
        return skill

    def names(self) -> list[str]:
        return list(self._skills.keys())

    def to_openai_tools(self) -> list[dict[str, Any]]:
        tools: list[dict[str, Any]] = []
        for skill in self._skills.values():
            tools.append(
                {
                    "type": "function",
                    "function": {
                        "name": skill.name,
                        "description": skill.description,
                        "parameters": skill.parameters,
                    },
                }
            )
        return tools

    async def execute(self, name: str, arguments: dict[str, Any]) -> SkillResult:
        try:
            skill = self.get(name)
        except UnknownSkillError as exc:
            return SkillResult(success=False, content="", error=str(exc))
        return await skill.execute(arguments)


def default_registry() -> SkillRegistry:
    from friday.skills.mock.joke_skill import JokeSkill
    from friday.skills.mock.time_skill import TimeSkill

    registry = SkillRegistry()
    registry.register(TimeSkill())
    registry.register(JokeSkill())
    return registry
