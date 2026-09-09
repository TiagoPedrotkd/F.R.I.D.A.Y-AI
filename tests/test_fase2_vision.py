"""Fase 2 vision — context, contacts, workflows, alerts, new skills."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from friday.config import Settings
from friday.llm.intent_router import match_skill
from friday.productivity.alerts import compute_alerts
from friday.productivity.contacts import resolve_contact, save_contacts
from friday.productivity.context import build_productivity_context, format_context_block
from friday.productivity.workflows import build_meeting_invite_workflow
from friday.safety.confirmation import GATED_SKILLS
from friday.skills.local.calendar_skills import FindFreeSlotsSkill, SummarizeDaySkill
from friday.skills.registry import default_registry


def test_gated_skills_extended():
    assert "cancel_calendar_event" in GATED_SKILLS
    assert "modify_calendar_event" in GATED_SKILLS
    assert "draft_email_reply" in GATED_SKILLS


def test_registry_vision_skills():
    names = set(default_registry().names())
    for n in (
        "find_free_slots",
        "summarize_day",
        "status_check",
        "cancel_calendar_event",
        "modify_calendar_event",
        "draft_email_reply",
        "resolve_contact",
        "start_meeting_workflow",
        "prepare_meeting",
        "schedule_local_reminder",
    ):
        assert n in names


def test_context_block_shape():
    ctx = build_productivity_context(
        Settings(CALDAV_ENABLED=False, EMAIL_ENABLED=False), force=True
    )
    assert "current_time" in ctx
    assert "upcoming_meetings" in ctx
    assert "pending_emails" in ctx
    assert "user_patterns" in ctx
    block = format_context_block(ctx)
    assert "CONTEXT" in block


def test_contact_disambiguation(tmp_path, monkeypatch):
    settings = Settings(PREFS_DIR=str(tmp_path / "prefs"))
    monkeypatch.setattr(
        "friday.productivity.contacts.contacts_path",
        lambda s=None: tmp_path / "contacts.json",
    )
    save_contacts(
        [
            {"name": "Joao Boss", "email": "a@x.com", "aliases": ["Joao"]},
            {"name": "Joao Peer", "email": "b@x.com", "aliases": ["Joao"]},
        ],
        settings,
    )
    r = resolve_contact("Joao", settings)
    assert r["status"] == "ambiguous"
    assert len(r["matches"]) == 2


def test_workflow_three_steps():
    wf = build_meeting_invite_workflow(
        title="Sync", start="2026-09-04T15:00:00", end=None, to="a@b.c"
    )
    assert len(wf.steps) == 3
    p = wf.to_pending()
    assert p and p.action == "create_calendar_event"
    wf.advance()
    p2 = wf.to_pending()
    assert p2 and p2.action == "send_email"
    wf.advance()
    p3 = wf.to_pending()
    assert p3 and p3.action == "schedule_local_reminder"


def test_alerts_from_synthetic_ctx():
    ctx = {
        "current_time": "2026-09-03T14:20:00+01:00",
        "user_patterns": {"timezone": "Europe/Lisbon"},
        "upcoming_meetings": [
            {
                "uid": "1",
                "title": "Standup",
                "start": "14:30",
                "start_iso": "2026-09-03T14:30:00+01:00",
                "end_iso": "2026-09-03T14:45:00+01:00",
                "time_until": "10min",
            }
        ],
        "pending_emails": [
            {
                "id": "9",
                "from": "boss",
                "subject": "Q3",
                "days_waiting": 2.5,
                "priority": "high",
            }
        ],
    }
    with patch("friday.productivity.alerts._allow", return_value=True):
        alerts = compute_alerts(Settings(CALDAV_ENABLED=False, EMAIL_ENABLED=False), ctx=ctx)
    kinds = {a["kind"] for a in alerts}
    assert "imminent_meeting" in kinds or "email_overdue" in kinds


def test_intent_summarize_and_status():
    assert match_skill("Como esta o meu dia?") == "summarize_day"
    assert match_skill("Tens emails importantes?") == "status_check"
    assert match_skill("Quando posso falar?") == "find_free_slots"


def test_intent_cancel_and_create_extract_args():
    from friday.llm.intent_router import match_skill_with_args

    name, args = match_skill_with_args("Cancela a reuniao Sync")
    assert name == "cancel_calendar_event"
    assert args.get("title_hint", "").lower().startswith("sync")

    name2, args2 = match_skill_with_args("Cria reuniao amanha as 15h chamada Sync")
    assert name2 == "create_calendar_event"
    assert args2.get("title")
    assert "T15:00:00" in str(args2.get("start") or "")

    name3, args3 = match_skill_with_args("Prepara a reuniao com Cliente X")
    assert name3 == "prepare_meeting"
    assert "Cliente" in args3.get("query", "")


@pytest.mark.asyncio
async def test_summarize_day_skill():
    skill = SummarizeDaySkill(settings=Settings(CALDAV_ENABLED=False, EMAIL_ENABLED=False))
    result = await skill.execute({})
    assert result.success
    assert "Agora:" in result.content


@pytest.mark.asyncio
async def test_find_free_slots_requires_caldav():
    # Explicitly disable Google too — env may have GOOGLE_ENABLED + tokens from live setup.
    skill = FindFreeSlotsSkill(
        settings=Settings(CALDAV_ENABLED=False, GOOGLE_ENABLED=False)
    )
    result = await skill.execute({})
    assert not result.success
