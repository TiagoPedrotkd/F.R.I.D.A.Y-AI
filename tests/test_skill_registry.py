"""Tests for skill registry."""

import pytest

from friday.pipeline.errors import UnknownSkillError
from friday.skills.mock.joke_skill import JokeSkill
from friday.skills.mock.time_skill import TimeSkill
from friday.skills.registry import SkillRegistry, default_registry


def test_register_and_export_tools():
    registry = SkillRegistry()
    registry.register(TimeSkill())
    registry.register(JokeSkill())
    tools = registry.to_openai_tools()
    names = {t["function"]["name"] for t in tools}
    assert names == {"get_current_time", "tell_joke"}
    assert all(t["type"] == "function" for t in tools)


def test_default_registry_has_mock_skills():
    registry = default_registry()
    assert set(registry.names()) == {"get_current_time", "tell_joke"}


@pytest.mark.asyncio
async def test_time_skill_execute():
    skill = TimeSkill()
    result = await skill.execute({"timezone": "Europe/Lisbon"})
    assert result.success
    assert "Sao" in result.content or "sao" in result.content.lower()


@pytest.mark.asyncio
async def test_joke_skill_execute():
    skill = JokeSkill()
    result = await skill.execute({})
    assert result.success
    assert len(result.content) > 10


@pytest.mark.asyncio
async def test_unknown_skill_returns_error_result():
    registry = SkillRegistry()
    result = await registry.execute("missing_skill", {})
    assert not result.success
    assert "Unknown skill" in (result.error or "")


def test_get_raises_unknown_skill():
    registry = SkillRegistry()
    with pytest.raises(UnknownSkillError):
        registry.get("nope")
