"""Calendar provider — Google Calendar primary, CalDAV fallback (Fase 4)."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any
from uuid import uuid4
from zoneinfo import ZoneInfo

from friday.config import Settings, get_settings
from friday.integrations.google_oauth import (
    GoogleOAuthError,
    google_connected,
    google_request,
)
from friday.productivity.caldav_client import (
    CalDavError,
    cancel_event as caldav_cancel,
    create_event as caldav_create,
    find_free_slots as caldav_free,
    find_overlaps as caldav_overlaps,
    list_events as caldav_list,
    modify_event as caldav_modify,
)


class CalendarProviderError(RuntimeError):
    pass


def use_google(settings: Settings | None = None) -> bool:
    settings = settings or get_settings()
    return bool(settings.google_enabled and google_connected(settings))


def _caldav_kwargs(settings: Settings) -> dict[str, str]:
    return {
        "url": settings.caldav_url,
        "username": settings.caldav_user,
        "password": settings.caldav_password,
    }


def calendar_available(settings: Settings | None = None) -> bool:
    settings = settings or get_settings()
    if use_google(settings):
        return True
    return bool(settings.caldav_enabled and settings.caldav_url)


def list_events(
    settings: Settings | None = None,
    *,
    days: int = 7,
    timezone_name: str = "Europe/Lisbon",
) -> list[dict[str, Any]]:
    settings = settings or get_settings()
    if use_google(settings):
        return _google_list(settings, days=days, timezone_name=timezone_name)
    if not settings.caldav_enabled or not settings.caldav_url:
        raise CalendarProviderError("Calendario nao configurado (Google ou CalDAV).")
    try:
        return caldav_list(**_caldav_kwargs(settings), days=days, timezone_name=timezone_name)
    except CalDavError as exc:
        raise CalendarProviderError(str(exc)) from exc


def create_event(
    settings: Settings | None = None,
    *,
    title: str,
    start: str,
    end: str | None = None,
    description: str = "",
    timezone_name: str = "Europe/Lisbon",
) -> dict[str, Any]:
    settings = settings or get_settings()
    if use_google(settings):
        return _google_create(
            settings,
            title=title,
            start=start,
            end=end,
            description=description,
            timezone_name=timezone_name,
        )
    try:
        return caldav_create(
            **_caldav_kwargs(settings),
            title=title,
            start=start,
            end=end,
            description=description,
            timezone_name=timezone_name,
        )
    except CalDavError as exc:
        raise CalendarProviderError(str(exc)) from exc


def cancel_event(
    settings: Settings | None = None,
    *,
    uid: str,
    timezone_name: str = "Europe/Lisbon",
) -> dict[str, Any]:
    settings = settings or get_settings()
    if use_google(settings):
        return _google_cancel(settings, uid=uid)
    try:
        return caldav_cancel(
            **_caldav_kwargs(settings), uid=uid, timezone_name=timezone_name
        )
    except CalDavError as exc:
        raise CalendarProviderError(str(exc)) from exc


def modify_event(
    settings: Settings | None = None,
    *,
    uid: str,
    title: str | None = None,
    start: str | None = None,
    end: str | None = None,
    description: str | None = None,
    timezone_name: str = "Europe/Lisbon",
) -> dict[str, Any]:
    settings = settings or get_settings()
    if use_google(settings):
        return _google_modify(
            settings,
            uid=uid,
            title=title,
            start=start,
            end=end,
            description=description,
            timezone_name=timezone_name,
        )
    try:
        return caldav_modify(
            **_caldav_kwargs(settings),
            uid=uid,
            title=title,
            start=start,
            end=end,
            description=description,
            timezone_name=timezone_name,
        )
    except CalDavError as exc:
        raise CalendarProviderError(str(exc)) from exc


def find_overlaps(
    settings: Settings | None = None,
    *,
    start: str,
    end: str | None = None,
    timezone_name: str = "Europe/Lisbon",
    exclude_uid: str = "",
) -> list[dict[str, Any]]:
    settings = settings or get_settings()
    if use_google(settings):
        # Reuse list + overlap logic via caldav helper path: list then filter
        from friday.productivity.caldav_client import _parse_dt

        dt_start = _parse_dt(start, tz_name=timezone_name)
        dt_end = (
            _parse_dt(end, tz_name=timezone_name)
            if end
            else dt_start + timedelta(hours=1)
        )
        existing = list_events(settings, days=14, timezone_name=timezone_name)
        hits: list[dict[str, Any]] = []
        for ev in existing:
            if exclude_uid and ev.get("uid") == exclude_uid:
                continue
            try:
                es = _parse_dt(str(ev.get("start") or ""), tz_name=timezone_name)
                ee = _parse_dt(str(ev.get("end") or ""), tz_name=timezone_name)
            except Exception:
                continue
            if dt_start < ee and es < dt_end:
                hits.append(ev)
        return hits
    try:
        return caldav_overlaps(
            **_caldav_kwargs(settings),
            start=start,
            end=end,
            timezone_name=timezone_name,
            exclude_uid=exclude_uid,
        )
    except CalDavError as exc:
        raise CalendarProviderError(str(exc)) from exc


def find_free_slots(
    settings: Settings | None = None,
    *,
    days: int = 5,
    duration_min: int = 30,
    working_hours: str = "9:00-18:00",
    preferred_hour: int = 14,
    timezone_name: str = "Europe/Lisbon",
    limit: int = 5,
) -> list[dict[str, Any]]:
    settings = settings or get_settings()
    if use_google(settings):
        # Same algorithm as CalDAV but with Google list_events
        return _free_slots_from_events(
            list_events(settings, days=days, timezone_name=timezone_name),
            days=days,
            duration_min=duration_min,
            working_hours=working_hours,
            preferred_hour=preferred_hour,
            timezone_name=timezone_name,
            limit=limit,
        )
    try:
        return caldav_free(
            **_caldav_kwargs(settings),
            days=days,
            duration_min=duration_min,
            working_hours=working_hours,
            preferred_hour=preferred_hour,
            timezone_name=timezone_name,
            limit=limit,
        )
    except CalDavError as exc:
        raise CalendarProviderError(str(exc)) from exc


def _free_slots_from_events(
    events: list[dict[str, Any]],
    *,
    days: int,
    duration_min: int,
    working_hours: str,
    preferred_hour: int,
    timezone_name: str,
    limit: int,
) -> list[dict[str, Any]]:
    from friday.productivity.caldav_client import _parse_dt

    tz = ZoneInfo(timezone_name)
    now = datetime.now(tz)
    try:
        start_s, end_s = working_hours.split("-", 1)
        sh, sm = [int(x) for x in start_s.strip().split(":")[:2]]
        eh, em = [int(x) for x in end_s.strip().split(":")[:2]]
    except Exception:
        sh, sm, eh, em = 9, 0, 18, 0
    busy: list[tuple[datetime, datetime]] = []
    for ev in events:
        try:
            busy.append(
                (
                    _parse_dt(str(ev.get("start") or ""), tz_name=timezone_name),
                    _parse_dt(str(ev.get("end") or ""), tz_name=timezone_name),
                )
            )
        except Exception:
            continue
    busy.sort(key=lambda x: x[0])
    duration = timedelta(minutes=max(15, duration_min))
    slots: list[dict[str, Any]] = []
    day = now.date()
    for _ in range(max(1, days)):
        day_start = datetime(day.year, day.month, day.day, sh, sm, tzinfo=tz)
        day_end = datetime(day.year, day.month, day.day, eh, em, tzinfo=tz)
        cursor = max(now + timedelta(minutes=5), day_start)
        preferred = datetime(day.year, day.month, day.day, preferred_hour, 0, tzinfo=tz)
        candidates = []
        if day_start <= preferred < day_end:
            candidates.append(preferred)
        t = cursor
        while t + duration <= day_end:
            candidates.append(t)
            t += timedelta(minutes=30)
        for cand in candidates:
            if cand < cursor:
                continue
            end_c = cand + duration
            if end_c > day_end:
                continue
            overlap = any(cand < be and bs < end_c for bs, be in busy)
            if not overlap:
                slots.append(
                    {
                        "start": cand.isoformat(),
                        "end": end_c.isoformat(),
                        "duration_min": int(duration.total_seconds() // 60),
                    }
                )
                if len(slots) >= limit:
                    return slots
        day = day + timedelta(days=1)
    return slots


def _parse_rfc3339(value: str, timezone_name: str) -> str:
    """Normalize local ISO to RFC3339 for Google."""
    from friday.productivity.caldav_client import _parse_dt

    dt = _parse_dt(value, tz_name=timezone_name)
    return dt.isoformat()


def _google_list(
    settings: Settings, *, days: int, timezone_name: str
) -> list[dict[str, Any]]:
    tz = ZoneInfo(timezone_name)
    now = datetime.now(tz)
    end = now + timedelta(days=max(1, days))
    params = {
        "timeMin": now.astimezone(ZoneInfo("UTC")).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "timeMax": end.astimezone(ZoneInfo("UTC")).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "singleEvents": "true",
        "orderBy": "startTime",
        "maxResults": "50",
    }
    from urllib.parse import urlencode

    url = f"https://www.googleapis.com/calendar/v3/calendars/primary/events?{urlencode(params)}"
    try:
        data = google_request(url, settings=settings)
    except GoogleOAuthError as exc:
        raise CalendarProviderError(str(exc)) from exc
    events: list[dict[str, Any]] = []
    for item in data.get("items") or []:
        start = item.get("start") or {}
        end_o = item.get("end") or {}
        events.append(
            {
                "uid": item.get("id") or "",
                "summary": item.get("summary") or "(sem titulo)",
                "start": start.get("dateTime") or start.get("date") or "",
                "end": end_o.get("dateTime") or end_o.get("date") or "",
                "href": item.get("htmlLink") or "",
            }
        )
    return events


def _google_create(
    settings: Settings,
    *,
    title: str,
    start: str,
    end: str | None,
    description: str,
    timezone_name: str,
) -> dict[str, Any]:
    from friday.productivity.caldav_client import _parse_dt

    dt_start = _parse_dt(start, tz_name=timezone_name)
    dt_end = _parse_dt(end, tz_name=timezone_name) if end else dt_start + timedelta(hours=1)
    body: dict[str, Any] = {
        "summary": title,
        "description": description or "",
        "start": {"dateTime": dt_start.isoformat(), "timeZone": timezone_name},
        "end": {"dateTime": dt_end.isoformat(), "timeZone": timezone_name},
    }
    try:
        data = google_request(
            "https://www.googleapis.com/calendar/v3/calendars/primary/events",
            settings=settings,
            method="POST",
            body=body,
        )
    except GoogleOAuthError as exc:
        raise CalendarProviderError(str(exc)) from exc
    return {
        "uid": data.get("id") or str(uuid4()),
        "summary": data.get("summary") or title,
        "start": (data.get("start") or {}).get("dateTime") or dt_start.isoformat(),
        "end": (data.get("end") or {}).get("dateTime") or dt_end.isoformat(),
    }


def _google_cancel(settings: Settings, *, uid: str) -> dict[str, Any]:
    if not uid:
        raise CalendarProviderError("uid em falta")
    from urllib.parse import quote

    try:
        google_request(
            f"https://www.googleapis.com/calendar/v3/calendars/primary/events/{quote(uid)}",
            settings=settings,
            method="DELETE",
        )
    except GoogleOAuthError as exc:
        raise CalendarProviderError(str(exc)) from exc
    return {"uid": uid, "summary": "", "deleted": True}


def _google_modify(
    settings: Settings,
    *,
    uid: str,
    title: str | None,
    start: str | None,
    end: str | None,
    description: str | None,
    timezone_name: str,
) -> dict[str, Any]:
    if not uid:
        raise CalendarProviderError("uid em falta")
    from urllib.parse import quote

    from friday.productivity.caldav_client import _parse_dt

    try:
        existing = google_request(
            f"https://www.googleapis.com/calendar/v3/calendars/primary/events/{quote(uid)}",
            settings=settings,
        )
    except GoogleOAuthError as exc:
        raise CalendarProviderError(str(exc)) from exc
    if title:
        existing["summary"] = title
    if description is not None:
        existing["description"] = description
    if start:
        dt_start = _parse_dt(start, tz_name=timezone_name)
        existing["start"] = {"dateTime": dt_start.isoformat(), "timeZone": timezone_name}
    if end:
        dt_end = _parse_dt(end, tz_name=timezone_name)
        existing["end"] = {"dateTime": dt_end.isoformat(), "timeZone": timezone_name}
    try:
        data = google_request(
            f"https://www.googleapis.com/calendar/v3/calendars/primary/events/{quote(uid)}",
            settings=settings,
            method="PUT",
            body=existing,
        )
    except GoogleOAuthError as exc:
        raise CalendarProviderError(str(exc)) from exc
    return {
        "uid": data.get("id") or uid,
        "summary": data.get("summary") or title or "",
        "start": (data.get("start") or {}).get("dateTime") or "",
        "end": (data.get("end") or {}).get("dateTime") or "",
    }
