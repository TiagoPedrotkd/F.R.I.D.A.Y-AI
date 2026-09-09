"""Fase 2 productivity skills — calendar / email / confirmation gate."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from friday.config import Settings
from friday.safety.confirmation import GATED_SKILLS, ConfirmationGate, PendingAction
from friday.skills.gated import confirmation_required_result, is_confirmed
from friday.skills.local.calendar_skills import (
    CreateCalendarEventSkill,
    ListCalendarEventsSkill,
)
from friday.skills.local.email_skills import SendEmailSkill
from friday.skills.registry import default_registry


def test_gated_skills_set():
    assert "create_calendar_event" in GATED_SKILLS
    assert "send_email" in GATED_SKILLS


def test_registry_includes_fase2_skills():
    names = set(default_registry().names())
    for n in (
        "list_calendar_events",
        "create_calendar_event",
        "list_emails",
        "read_email",
        "send_email",
    ):
        assert n in names


@pytest.mark.asyncio
async def test_create_event_requires_confirmation():
    settings = Settings(
        CALDAV_ENABLED=True,
        CALDAV_URL="http://127.0.0.1:5232/friday/friday/",
        CALDAV_USER="friday",
        CALDAV_PASSWORD="friday",
    )
    skill = CreateCalendarEventSkill(settings=settings)
    result = await skill.execute(
        {"title": "Sync", "start": "2026-09-04T15:00:00", "description": "test"}
    )
    assert result.success
    assert result.metadata
    assert result.metadata["kind"] == "confirmation_required"
    assert result.metadata["pending"]["action"] == "create_calendar_event"
    assert not is_confirmed({})


@pytest.mark.asyncio
async def test_create_event_confirmed_calls_client():
    settings = Settings(
        CALDAV_ENABLED=True,
        CALDAV_URL="http://127.0.0.1:5232/x",
        CALDAV_USER="u",
        CALDAV_PASSWORD="p",
    )
    skill = CreateCalendarEventSkill(settings=settings)
    with patch(
        "friday.skills.local.calendar_skills.create_event",
        return_value={
            "uid": "1",
            "summary": "Sync",
            "start": "2026-09-04T15:00:00+01:00",
            "end": "2026-09-04T16:00:00+01:00",
        },
    ) as mock_create:
        result = await skill.execute(
            {
                "title": "Sync",
                "start": "2026-09-04T15:00:00",
                "confirmed": True,
            }
        )
    assert result.success
    assert "Evento criado" in result.content
    mock_create.assert_called_once()


@pytest.mark.asyncio
async def test_send_email_requires_confirmation():
    skill = SendEmailSkill(
        settings=Settings(EMAIL_ENABLED=True, IMAP_HOST="x", IMAP_USER="u")
    )
    result = await skill.execute(
        {"to": "a@b.c", "subject": "Oi", "body": "corpo"}
    )
    assert result.metadata["kind"] == "confirmation_required"
    assert result.metadata["pending"]["action"] == "send_email"


@pytest.mark.asyncio
async def test_list_calendar_disabled():
    # Explicitly disable Google too — env may have GOOGLE_ENABLED + tokens from live setup.
    skill = ListCalendarEventsSkill(
        settings=Settings(CALDAV_ENABLED=False, GOOGLE_ENABLED=False)
    )
    result = await skill.execute({})
    assert not result.success


def test_confirmation_helper_payload():
    r = confirmation_required_result(
        action="send_email",
        target="a@b.c",
        summary="enviar",
        consequences="x",
        payload={"to": "a@b.c"},
    )
    assert r.metadata["pending"]["payload"]["to"] == "a@b.c"
    gate = ConfirmationGate()
    msg = gate.request(
        PendingAction(
            action="send_email",
            target="a@b.c",
            summary="enviar",
            payload={"to": "a@b.c", "subject": "s", "body": "b"},
        )
    )
    assert "Confirmas" in msg
    status, action = gate.interpret("sim")
    assert status == "confirmed"
    assert action.payload["to"] == "a@b.c"
