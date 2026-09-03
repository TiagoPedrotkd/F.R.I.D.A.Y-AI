"""CalDAV calendar client (Radicale / any CalDAV server)."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import uuid4
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)


class CalDavError(RuntimeError):
    pass


def _parse_dt(value: str, *, tz_name: str = "Europe/Lisbon") -> datetime:
    raw = (value or "").strip()
    if not raw:
        raise CalDavError("Data/hora em falta")
    tz = ZoneInfo(tz_name)
    if raw.endswith("Z"):
        return datetime.fromisoformat(raw.replace("Z", "+00:00")).astimezone(tz)
    dt = datetime.fromisoformat(raw)
    if dt.tzinfo is None:
        return dt.replace(tzinfo=tz)
    return dt.astimezone(tz)


def _get_calendar(url: str, username: str, password: str):
    import caldav

    client = caldav.DAVClient(url=url, username=username, password=password)
    principal = client.principal()
    calendars = principal.calendars()
    if not calendars:
        return client.calendar(url=url)
    return calendars[0]


def list_events(
    *,
    url: str,
    username: str,
    password: str,
    days: int = 7,
    timezone_name: str = "Europe/Lisbon",
) -> list[dict[str, Any]]:
    try:
        import caldav  # noqa: F401
    except ImportError as exc:
        raise CalDavError(
            "Pacote caldav nao instalado. Corre: pip install -e \".[productivity]\""
        ) from exc

    calendar = _get_calendar(url, username, password)
    start = datetime.now(ZoneInfo(timezone_name))
    end = start + timedelta(days=max(1, days))
    try:
        results = calendar.search(start=start, end=end, event=True, expand=True)
    except Exception as exc:
        raise CalDavError(f"Falha ao listar eventos CalDAV: {exc}") from exc
    events: list[dict[str, Any]] = []
    for item in results:
        try:
            ical = item.icalendar_component
            summary = str(ical.get("summary") or "(sem titulo)")
            dtstart = ical.get("dtstart")
            dtend = ical.get("dtend")
            href = ""
            try:
                href = str(getattr(item, "url", "") or "")
            except Exception:
                href = ""
            events.append(
                {
                    "uid": str(ical.get("uid") or ""),
                    "summary": summary,
                    "start": str(dtstart.dt) if dtstart else "",
                    "end": str(dtend.dt) if dtend else "",
                    "href": href,
                }
            )
        except Exception as exc:
            logger.debug("Skip calendar item: %s", exc)
    events.sort(key=lambda e: e.get("start") or "")
    return events


def find_overlaps(
    *,
    url: str,
    username: str,
    password: str,
    start: str,
    end: str | None = None,
    timezone_name: str = "Europe/Lisbon",
    exclude_uid: str = "",
) -> list[dict[str, Any]]:
    dt_start = _parse_dt(start, tz_name=timezone_name)
    dt_end = _parse_dt(end, tz_name=timezone_name) if end else dt_start + timedelta(hours=1)
    existing = list_events(
        url=url,
        username=username,
        password=password,
        days=max(1, (dt_end.date() - datetime.now(ZoneInfo(timezone_name)).date()).days + 2),
        timezone_name=timezone_name,
    )
    hits: list[dict[str, Any]] = []
    for ev in existing:
        if exclude_uid and ev.get("uid") == exclude_uid:
            continue
        try:
            es = _parse_dt(str(ev.get("start") or ""), tz_name=timezone_name)
            ee = _parse_dt(str(ev.get("end") or ""), tz_name=timezone_name)
        except CalDavError:
            continue
        if dt_start < ee and es < dt_end:
            hits.append(ev)
    return hits


def create_event(
    *,
    url: str,
    username: str,
    password: str,
    title: str,
    start: str,
    end: str | None = None,
    description: str = "",
    timezone_name: str = "Europe/Lisbon",
) -> dict[str, Any]:
    try:
        from icalendar import Calendar, Event
    except ImportError as exc:
        raise CalDavError(
            "Pacotes caldav/icalendar nao instalados. "
            'Corre: pip install -e ".[productivity]"'
        ) from exc

    dt_start = _parse_dt(start, tz_name=timezone_name)
    if end:
        dt_end = _parse_dt(end, tz_name=timezone_name)
    else:
        dt_end = dt_start + timedelta(hours=1)

    uid = f"{uuid4()}@friday.local"
    cal = Calendar()
    cal.add("prodid", "-//F.R.I.D.A.Y//EN")
    cal.add("version", "2.0")
    ev = Event()
    ev.add("uid", uid)
    ev.add("summary", title)
    ev.add("dtstart", dt_start)
    ev.add("dtend", dt_end)
    ev.add("dtstamp", datetime.now(timezone.utc))
    if description:
        ev.add("description", description)
    cal.add_component(ev)

    calendar = _get_calendar(url, username, password)
    calendar.save_event(cal.to_ical().decode("utf-8"))
    return {
        "uid": uid,
        "summary": title,
        "start": dt_start.isoformat(),
        "end": dt_end.isoformat(),
    }


def _find_event_object(calendar, uid: str, timezone_name: str):
    start = datetime.now(ZoneInfo(timezone_name)) - timedelta(days=1)
    end = start + timedelta(days=60)
    results = calendar.search(start=start, end=end, event=True, expand=True)
    for item in results:
        try:
            ical = item.icalendar_component
            if str(ical.get("uid") or "") == uid:
                return item
        except Exception:
            continue
    return None


def cancel_event(
    *,
    url: str,
    username: str,
    password: str,
    uid: str,
    timezone_name: str = "Europe/Lisbon",
) -> dict[str, Any]:
    if not uid:
        raise CalDavError("uid em falta")
    calendar = _get_calendar(url, username, password)
    item = _find_event_object(calendar, uid, timezone_name)
    if item is None:
        raise CalDavError(f"Evento {uid} nao encontrado")
    summary = ""
    try:
        summary = str(item.icalendar_component.get("summary") or "")
    except Exception:
        pass
    item.delete()
    return {"uid": uid, "summary": summary, "deleted": True}


def modify_event(
    *,
    url: str,
    username: str,
    password: str,
    uid: str,
    title: str | None = None,
    start: str | None = None,
    end: str | None = None,
    description: str | None = None,
    timezone_name: str = "Europe/Lisbon",
) -> dict[str, Any]:
    if not uid:
        raise CalDavError("uid em falta")
    calendar = _get_calendar(url, username, password)
    item = _find_event_object(calendar, uid, timezone_name)
    if item is None:
        raise CalDavError(f"Evento {uid} nao encontrado")
    ical = item.icalendar_component
    if title:
        ical["summary"] = title
    if start:
        ical["dtstart"] = _parse_dt(start, tz_name=timezone_name)
    if end:
        ical["dtend"] = _parse_dt(end, tz_name=timezone_name)
    elif start and ical.get("dtend") is None:
        ical["dtend"] = _parse_dt(start, tz_name=timezone_name) + timedelta(hours=1)
    if description is not None:
        ical["description"] = description
    item.save()
    return {
        "uid": uid,
        "summary": str(ical.get("summary") or title or ""),
        "start": str(ical.get("dtstart").dt) if ical.get("dtstart") else "",
        "end": str(ical.get("dtend").dt) if ical.get("dtend") else "",
    }


def find_free_slots(
    *,
    url: str,
    username: str,
    password: str,
    days: int = 5,
    duration_min: int = 30,
    working_hours: str = "9:00-18:00",
    preferred_hour: int = 14,
    timezone_name: str = "Europe/Lisbon",
    limit: int = 5,
) -> list[dict[str, Any]]:
    tz = ZoneInfo(timezone_name)
    now = datetime.now(tz)
    try:
        start_s, end_s = working_hours.split("-", 1)
        sh, sm = [int(x) for x in start_s.strip().split(":")[:2]]
        eh, em = [int(x) for x in end_s.strip().split(":")[:2]]
    except Exception:
        sh, sm, eh, em = 9, 0, 18, 0
    events = list_events(
        url=url,
        username=username,
        password=password,
        days=days,
        timezone_name=timezone_name,
    )
    busy: list[tuple[datetime, datetime]] = []
    for ev in events:
        try:
            busy.append(
                (
                    _parse_dt(str(ev.get("start") or ""), tz_name=timezone_name),
                    _parse_dt(str(ev.get("end") or ""), tz_name=timezone_name),
                )
            )
        except CalDavError:
            continue
    busy.sort(key=lambda x: x[0])
    duration = timedelta(minutes=max(15, duration_min))
    slots: list[dict[str, Any]] = []
    day = now.date()
    for _ in range(max(1, days)):
        day_start = datetime(day.year, day.month, day.day, sh, sm, tzinfo=tz)
        day_end = datetime(day.year, day.month, day.day, eh, em, tzinfo=tz)
        cursor = max(now + timedelta(minutes=5), day_start)
        # Prefer preferred_hour first
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
