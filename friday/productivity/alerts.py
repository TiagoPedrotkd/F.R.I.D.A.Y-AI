"""Proactive productivity alerts (conflicts, imminent meetings, overdue email)."""

from __future__ import annotations

import time
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from friday.config import Settings, get_settings
from friday.productivity.context import build_productivity_context, _parse_event_start

_rate: dict[str, float] = {}
_RATE_TTL = 300.0  # 5 min per alert key


def _allow(key: str) -> bool:
    now = time.monotonic()
    last = _rate.get(key, 0.0)
    if now - last < _RATE_TTL:
        return False
    _rate[key] = now
    return True


def compute_alerts(
    settings: Settings | None = None,
    *,
    ctx: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    settings = settings or get_settings()
    ctx = ctx or build_productivity_context(settings)
    alerts: list[dict[str, Any]] = []
    patterns = ctx.get("user_patterns") or {}
    tz_name = str(patterns.get("timezone") or "Europe/Lisbon")
    try:
        tz = ZoneInfo(tz_name)
    except Exception:
        tz = ZoneInfo("Europe/Lisbon")
    now = datetime.now(tz)

    meetings = list(ctx.get("upcoming_meetings") or [])
    # Imminent <15min
    for m in meetings:
        start = _parse_event_start(str(m.get("start_iso") or m.get("start") or ""), tz)
        if not start:
            continue
        delta = (start - now).total_seconds()
        if 0 < delta <= 15 * 60:
            key = f"imminent:{m.get('uid') or m.get('title')}"
            if _allow(key):
                mins = int(delta // 60)
                alerts.append(
                    {
                        "severity": "critical",
                        "kind": "imminent_meeting",
                        "message": f"Reuniao '{m.get('title')}' em {mins} min.",
                        "cta": "Abrir agenda?",
                    }
                )

    # Calendar overlaps (pairwise among next few)
    parsed: list[tuple[Any, datetime, datetime]] = []
    for m in meetings:
        s = _parse_event_start(str(m.get("start_iso") or ""), tz)
        e = _parse_event_start(str(m.get("end_iso") or ""), tz)
        if s and e:
            parsed.append((m, s, e))
    for i in range(len(parsed)):
        for j in range(i + 1, len(parsed)):
            a, sa, ea = parsed[i]
            b, sb, eb = parsed[j]
            if sa < eb and sb < ea:
                key = f"conflict:{a.get('uid')}:{b.get('uid')}"
                if _allow(key):
                    alerts.append(
                        {
                            "severity": "critical",
                            "kind": "calendar_conflict",
                            "message": (
                                f"Conflito: '{a.get('title')}' ({a.get('start')}) "
                                f"e '{b.get('title')}' ({b.get('start')})."
                            ),
                            "cta": "Quer reagendar?",
                        }
                    )

    # Dense day → pause suggestion
    if len(meetings) >= 3:
        key = "pause:dense"
        if _allow(key):
            alerts.append(
                {
                    "severity": "important",
                    "kind": "pause_suggested",
                    "message": f"Tem {len(meetings)} compromissos proximos.",
                    "cta": "Quer uma pausa entre reunioes?",
                }
            )

    # Overdue emails
    for em in ctx.get("pending_emails") or []:
        days = float(em.get("days_waiting") or 0)
        if days >= 2 or em.get("priority") == "high":
            key = f"email:{em.get('id') or em.get('subject')}"
            if _allow(key):
                alerts.append(
                    {
                        "severity": "critical" if days >= 2 else "important",
                        "kind": "email_overdue",
                        "message": (
                            f"Email de {em.get('from')} — '{em.get('subject')}' "
                            f"ha ~{days} dia(s)."
                        ),
                        "cta": "Quer que prepare um rascunho de resposta?",
                    }
                )

    # Local reminders due
    try:
        from friday.productivity.reminders import due_reminders

        for rem in due_reminders(settings, tz_name=tz_name):
            key = f"reminder:{rem.get('id')}"
            if _allow(key):
                alerts.append(
                    {
                        "severity": "important",
                        "kind": "scheduled_reminder",
                        "message": str(rem.get("message") or rem.get("title") or "Lembrete"),
                        "cta": "Quer que prepare a reuniao (emails)?",
                    }
                )
    except Exception:
        pass

    return alerts[:5]
