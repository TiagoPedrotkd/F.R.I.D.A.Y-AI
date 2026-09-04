"""Fase 3.0 — Home Assistant client + skills (mocked HTTP)."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from friday.config import Settings
from friday.integrations.home_assistant import (
    HomeAssistantError,
    get_state,
    get_status,
    list_states,
)
from friday.llm.intent_router import match_skill, match_skill_with_args
from friday.skills.local.ha_skills import HaGetStatusSkill, HaListEntitiesSkill
from friday.skills.registry import default_registry


def _ha_settings(**kwargs) -> Settings:
    base = {
        "ha_enabled": True,
        "ha_url": "http://127.0.0.1:8123",
        "ha_token": "test-token",
    }
    base.update(kwargs)
    return Settings(**base)


def test_intent_ha_status():
    assert match_skill("Qual o estado da casa?") == "ha_get_status"
    assert match_skill("Home Assistant online?") == "ha_get_status"


def test_intent_ha_list_lights():
    hit = match_skill_with_args("lista as luzes da casa")
    assert hit is not None
    assert hit[0] == "ha_list_entities"
    assert hit[1].get("domain") == "light"


def test_ha_skills_registered_when_enabled():
    reg = default_registry(Settings(ha_enabled=True))
    assert "ha_get_status" in reg.names()
    assert "get_home_status" in reg.names()
    assert "ha_list_entities" in reg.names()
    assert "ha_get_state" in reg.names()


def test_ha_skills_not_registered_when_disabled():
    reg = default_registry(Settings(ha_enabled=False))
    assert "ha_get_status" not in reg.names()


def test_get_status_mock():
    settings = _ha_settings()
    fake = MagicMock()
    fake.read.return_value = b'{"message":"API running."}'
    fake.__enter__ = MagicMock(return_value=fake)
    fake.__exit__ = MagicMock(return_value=False)
    fake.status = 200
    with patch("urllib.request.urlopen", return_value=fake):
        out = get_status(settings)
    assert out["ok"] is True


def test_list_states_domain_filter():
    settings = _ha_settings()
    payload = [
        {
            "entity_id": "light.sala",
            "state": "on",
            "attributes": {"friendly_name": "Sala"},
        },
        {"entity_id": "sensor.temp", "state": "21", "attributes": {}},
    ]
    fake = MagicMock()
    fake.read.return_value = json.dumps(payload).encode()
    fake.__enter__ = MagicMock(return_value=fake)
    fake.__exit__ = MagicMock(return_value=False)
    with patch("urllib.request.urlopen", return_value=fake):
        out = list_states(settings, domain="light", limit=10)
    assert out["ok"]
    assert out["count"] == 1
    assert out["entities"][0]["entity_id"] == "light.sala"


def test_get_state_mock():
    settings = _ha_settings()
    payload = {
        "entity_id": "sensor.temp",
        "state": "22.5",
        "attributes": {"friendly_name": "Temp"},
    }
    fake = MagicMock()
    fake.read.return_value = json.dumps(payload).encode()
    fake.__enter__ = MagicMock(return_value=fake)
    fake.__exit__ = MagicMock(return_value=False)
    with patch("urllib.request.urlopen", return_value=fake):
        out = get_state("sensor.temp", settings)
    assert out["ok"]
    assert out["state"] == "22.5"


@pytest.mark.asyncio
async def test_ha_get_status_skill_disabled():
    skill = HaGetStatusSkill(Settings(ha_enabled=False))
    result = await skill.execute({})
    assert result.success is False


@pytest.mark.asyncio
async def test_ha_list_skill_ok():
    settings = _ha_settings()
    skill = HaListEntitiesSkill(settings)
    payload = [{"entity_id": "light.a", "state": "off", "attributes": {}}]
    fake = MagicMock()
    fake.read.return_value = json.dumps(payload).encode()
    fake.__enter__ = MagicMock(return_value=fake)
    fake.__exit__ = MagicMock(return_value=False)
    with patch("urllib.request.urlopen", return_value=fake):
        result = await skill.execute({"domain": "light"})
    assert result.success
    assert "light.a" in result.content


def test_ha_disabled_raises():
    with pytest.raises(HomeAssistantError):
        get_status(Settings(ha_enabled=False))


def test_compose_has_profiles():
    text = Path("docker-compose.yml").read_text(encoding="utf-8")
    assert "profiles:" in text
    assert "homeassistant" in text
    assert "mosquitto" in text
    assert "frigate" in text


def test_fase3_docs_exist():
    root = Path("docs/fase-3")
    for name in (
        "README.md",
        "home-assistant.md",
        "mqtt.md",
        "frigate.md",
        "skills-contract.md",
        "checklist-conclusao.md",
    ):
        assert (root / name).is_file(), name
