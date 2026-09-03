"""Per-turn productivity context for FRIDAY (calendar, email, patterns)."""

from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from friday.config import Settings, get_settings
from friday.productivity.patterns import get_user_patterns

logger = logging.getLogger(__name__)

_cache: dict[str, Any] = {"at": 0.0, "payload": None}
_CACHE_TTL = 45.0
_last_actions: list[dict[str, Any]] = []


def record_action(action: str, result: str = "") -> None:
    _last_actions.insert(
        0,
        {
            "action": action,
            "result": (result or "")[:120],
            "when": datetime.now().isoformat(timespec="seconds"),
        },
    )
    del _last_actions[20:]


def _parse_event_start(raw: str, tz: ZoneInfo) -> datetime | None:
    if not raw:
        return None
    try:
        s = str(raw).replace("Z", "+00:00")
        # date-only
        if len(s) == 10:
            return datetime.fromisoformat(s).replace(tzinfo=tz)
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            return dt.replace(tzinfo=tz)
        return dt.astimezone(tz)
    except Exception:
        return None


def _meeting_payload(ev: dict[str, Any], now: datetime, tz: ZoneInfo) -> dict[str, Any]:
    start = _parse_event_start(str(ev.get("start") or ""), tz)
    end = _parse_event_start(str(ev.get("end") or ""), tz)
    duration = None
    if start and end:
        duration = max(1, int((end - start).total_seconds() // 60))
    time_until = ""
    if start:
        delta = (start - now).total_seconds()
        if delta <= 0:
            time_until = "now"
        elif delta < 3600:
            time_until = f"{int(delta // 60)}min"
        else:
            time_until = f"{delta / 3600:.1f}h"
    return {
        "uid": ev.get("uid") or "",
        "title": ev.get("summary") or "(sem titulo)",
        "start": start.strftime("%H:%M") if start else str(ev.get("start") or ""),
        "start_iso": start.isoformat() if start else str(ev.get("start") or ""),
        "end_iso": end.isoformat() if end else str(ev.get("end") or ""),
        "duration_min": duration,
        "time_until": time_until,
    }


def _email_priority(subject: str, days_waiting: float) -> str:
    sub = (subject or "").casefold()
    if days_waiting >= 2 or any(k in sub for k in ("urgent", "urgente", "asap", "importante")):
        return "high"
    if days_waiting >= 1:
        return "medium"
    return "low"


def build_productivity_context(
    settings: Settings | None = None,
    *,
    force: bool = False,
    last_actions: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Aggregate CONTEXT JSON (cached ~45s). Failures degrade to empty lists."""
    global _cache
    settings = settings or get_settings()
    now_mono = time.monotonic()
    if (
        not force
        and _cache["payload"] is not None
        and (now_mono - float(_cache["at"])) < _CACHE_TTL
    ):
        payload = dict(_cache["payload"])
        payload["last_actions"] = list(last_actions if last_actions is not None else _last_actions)[:8]
        return payload

    patterns = get_user_patterns(settings)
    tz_name = str(patterns.get("timezone") or "Europe/Lisbon")
    try:
        tz = ZoneInfo(tz_name)
    except Exception:
        tz = ZoneInfo("Europe/Lisbon")
        tz_name = "Europe/Lisbon"
    now = datetime.now(tz)
    wh = str(patterns.get("working_hours") or "9:00-18:00")
    is_working = True
    try:
        start_s, end_s = wh.split("-", 1)
        sh, sm = [int(x) for x in start_s.strip().split(":")[:2]]
        eh, em = [int(x) for x in end_s.strip().split(":")[:2]]
        minutes = now.hour * 60 + now.minute
        is_working = (sh * 60 + sm) <= minutes < (eh * 60 + em)
    except Exception:
        is_working = 9 <= now.hour < 18

    upcoming: list[dict[str, Any]] = []
    if settings.caldav_enabled and settings.caldav_url:
        try:
            from friday.productivity.caldav_client import list_events

            raw = list_events(
                url=settings.caldav_url,
                username=settings.caldav_user,
                password=settings.caldav_password,
                days=2,
                timezone_name=tz_name,
            )
            for ev in raw[:12]:
                upcoming.append(_meeting_payload(ev, now, tz))
        except Exception as exc:
            logger.debug("context calendar skipped: %s", exc)

    pending_emails: list[dict[str, Any]] = []
    if settings.email_enabled and settings.imap_host:
        try:
            from friday.productivity.email_client import EmailSettings, list_emails
            from friday.skills.local.email_skills import _email_cfg

            items = list_emails(_email_cfg(settings), limit=8)
            for m in items:
                days = 0.0
                try:
                    if m.get("date"):
                        received = datetime.fromisoformat(str(m["date"]).replace("Z", "+00:00"))
                        if received.tzinfo is None:
                            received = received.replace(tzinfo=tz)
                        days = max(0.0, (now - received.astimezone(tz)).total_seconds() / 86400)
                except Exception:
                    days = 0.0
                pending_emails.append(
                    {
                        "id": m.get("id"),
                        "from": m.get("from"),
                        "subject": m.get("subject"),
                        "received": m.get("date"),
                        "days_waiting": round(days, 1),
                        "priority": _email_priority(str(m.get("subject") or ""), days),
                        "unread": True,
                    }
                )
        except Exception as exc:
            logger.debug("context email skipped: %s", exc)

    payload = {
        "current_time": now.isoformat(timespec="seconds"),
        "is_working_hours": is_working,
        "upcoming_meetings": upcoming,
        "pending_emails": pending_emails,
        "user_patterns": patterns,
        "last_actions": list(last_actions if last_actions is not None else _last_actions)[:8],
    }
    _cache = {"at": now_mono, "payload": payload}
    return payload


def format_context_block(ctx: dict[str, Any]) -> str:
    return (
        "CONTEXT (JSON — usa para contextualizar; nao inventes fora deste bloco):\n"
        + json.dumps(ctx, ensure_ascii=False, indent=2)
    )


def invalidate_context_cache() -> None:
    _cache["at"] = 0.0
    _cache["payload"] = None
