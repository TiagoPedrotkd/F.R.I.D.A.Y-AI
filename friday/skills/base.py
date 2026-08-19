"""Skill protocol and result types."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable


@dataclass
class SkillResult:
    success: bool
    content: str
    error: str | None = None
    metadata: dict[str, Any] | None = field(default=None)


@runtime_checkable
class Skill(Protocol):
    name: str
    description: str
    parameters: dict[str, Any]

    async def execute(self, arguments: dict[str, Any]) -> SkillResult: ...
