"""Calendar skills (Google Calendar or CalDAV via provider)."""

from __future__ import annotations

from typing import Any

from friday.config import Settings, get_settings
from friday.productivity.calendar_provider import (
    CalendarProviderError,
    calendar_available,
    cancel_event,
    create_event,
    find_free_slots,
    find_overlaps,
    list_events,
    modify_event,
)
from friday.productivity.context import invalidate_context_cache, record_action
from friday.productivity.patterns import get_user_patterns
from friday.skills.base import SkillResult
from friday.skills.gated import confirmation_required_result, is_confirmed


def _not_configured() -> SkillResult:
    return SkillResult(
        success=False,
        content="",
        error="Calendario nao configurado (Google OAuth ou CalDAV).",
    )


class ListCalendarEventsSkill:
    name = "list_calendar_events"
    description = (
        "Lista eventos proximos do calendario CalDAV local (hoje / proximos dias). "
        "Usa para 'que tenho na agenda', reunioes, compromissos."
    )
    parameters: dict[str, Any] = {
        "type": "object",
        "properties": {
            "days": {
                "type": "integer",
                "description": "Janela em dias a partir de agora (default 7)",
                "minimum": 1,
                "maximum": 60,
            }
        },
        "required": [],
    }

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()

    async def execute(self, arguments: dict[str, Any]) -> SkillResult:
        s = self._settings
        if not calendar_available(s):
            return SkillResult(
                success=False, content="", error="Calendario nao configurado (Google ou CalDAV)."
            )
        days = int(arguments.get("days") or 7)
        try:
            events = list_events(s, days=days)
        except CalendarProviderError as exc:
            return SkillResult(success=False, content="", error=str(exc))
        record_action("list_events", f"{len(events)} events")
        if not events:
            return SkillResult(
                success=True,
                content=f"Nao ha eventos nos proximos {days} dias.",
                metadata={"kind": "calendar", "events": []},
            )
        lines = [f"Agenda (proximos {days} dias):"]
        for ev in events[:20]:
            lines.append(
                f"- [{ev.get('uid','')}] {ev.get('start', '?')}: {ev.get('summary', '?')}"
            )
        return SkillResult(
            success=True,
            content="\n".join(lines),
            metadata={"kind": "calendar", "events": events[:20]},
        )


class CreateCalendarEventSkill:
    name = "create_calendar_event"
    description = (
        "Cria um evento no calendario CalDAV. "
        "REQUER confirmacao do utilizador antes de gravar."
    )
    parameters: dict[str, Any] = {
        "type": "object",
        "properties": {
            "title": {"type": "string"},
            "start": {"type": "string", "description": "ISO-8601"},
            "end": {"type": "string"},
            "description": {"type": "string"},
            "confirmed": {"type": "boolean"},
        },
        "required": ["title", "start"],
    }

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()

    async def execute(self, arguments: dict[str, Any]) -> SkillResult:
        s = self._settings
        title = str(arguments.get("title") or "").strip()
        start = str(arguments.get("start") or "").strip()
        end = str(arguments.get("end") or "").strip() or None
        description = str(arguments.get("description") or "").strip()
        if not title or not start:
            return SkillResult(
                success=False, content="", error="Preciso de title e start (ISO-8601)."
            )
        payload = {
            "title": title,
            "start": start,
            "end": end,
            "description": description,
        }
        preview = {"title": title, "start": start, "end": end or "(+1h)"}
        consequences = "O evento sera gravado no calendario."
        if calendar_available(s) and not is_confirmed(arguments):
            try:
                overlaps = find_overlaps(s, start=start, end=end)
                if overlaps:
                    names = ", ".join(
                        str(o.get("summary") or o.get("uid")) for o in overlaps[:3]
                    )
                    consequences += f" AVISO: conflita com {names}."
                    preview["overlaps"] = [
                        {"summary": o.get("summary"), "start": o.get("start")}
                        for o in overlaps[:3]
                    ]
            except Exception:
                pass
        if not is_confirmed(arguments):
            return confirmation_required_result(
                action=self.name,
                target=title,
                summary=f"criar o evento '{title}' em {start}",
                consequences=consequences,
                payload=payload,
                preview=preview,
            )
        if not calendar_available(s):
            return SkillResult(success=False, content="", error="Calendario nao configurado (Google ou CalDAV).")
        try:
            created = create_event(
                s,
                title=title,
                start=start,
                end=end,
                description=description,
            )
        except CalendarProviderError as exc:
            return SkillResult(success=False, content="", error=str(exc))
        invalidate_context_cache()
        record_action("create_event", title)
        try:
            from friday.productivity.patterns import bump_pattern_counter

            bump_pattern_counter("confirmed_creates")
        except Exception:
            pass
        return SkillResult(
            success=True,
            content=(
                f"Evento criado: {created['summary']} "
                f"({created['start']} → {created['end']})."
            ),
            metadata={"kind": "calendar", "created": created},
        )


class CancelCalendarEventSkill:
    name = "cancel_calendar_event"
    description = (
        "Cancela/apaga um evento CalDAV pelo uid ou titulo. REQUER confirmacao."
    )
    parameters: dict[str, Any] = {
        "type": "object",
        "properties": {
            "uid": {"type": "string"},
            "title_hint": {"type": "string"},
            "confirmed": {"type": "boolean"},
        },
        "required": [],
    }

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()

    def _resolve_uid(self, uid: str, hint: str) -> tuple[str, str] | SkillResult:
        if uid:
            return uid, hint or uid
        if not hint:
            return SkillResult(
                success=False, content="", error="Indica uid ou titulo do evento."
            )
        s = self._settings
        if not calendar_available(s):
            return SkillResult(success=False, content="", error="Calendario nao configurado (Google ou CalDAV).")
        try:
            events = list_events(s, days=30)
        except CalendarProviderError as exc:
            return SkillResult(success=False, content="", error=str(exc))
        needle = hint.casefold()
        hits = [e for e in events if needle in str(e.get("summary") or "").casefold()]
        if not hits:
            return SkillResult(
                success=False, content="", error=f"Nenhum evento com titulo '{hint}'."
            )
        if len(hits) > 1:
            opts = "; ".join(
                f"{e.get('summary')} ({e.get('start')}, uid={e.get('uid')})"
                for e in hits[:5]
            )
            return SkillResult(
                success=False,
                content="",
                error=f"Varios eventos para '{hint}': {opts}. Indica o uid.",
            )
        return str(hits[0].get("uid") or ""), str(hits[0].get("summary") or hint)

    async def execute(self, arguments: dict[str, Any]) -> SkillResult:
        uid = str(arguments.get("uid") or "").strip()
        hint = str(arguments.get("title_hint") or "").strip()
        resolved = self._resolve_uid(uid, hint)
        if isinstance(resolved, SkillResult):
            return resolved
        uid, hint = resolved
        payload = {"uid": uid, "title_hint": hint}
        if not is_confirmed(arguments):
            return confirmation_required_result(
                action=self.name,
                target=hint,
                summary=f"cancelar o evento '{hint}'",
                consequences="O evento sera removido do calendario.",
                payload=payload,
                preview={"uid": uid, "title": hint},
            )
        s = self._settings
        if not calendar_available(s):
            return SkillResult(success=False, content="", error="Calendario nao configurado (Google ou CalDAV).")
        try:
            deleted = cancel_event(s, uid=uid)
        except CalendarProviderError as exc:
            return SkillResult(success=False, content="", error=str(exc))
        invalidate_context_cache()
        record_action("cancel_event", hint)
        return SkillResult(
            success=True,
            content=f"Evento cancelado: {deleted.get('summary') or uid}.",
            metadata={"kind": "calendar", "deleted": deleted},
        )


class ModifyCalendarEventSkill:
    name = "modify_calendar_event"
    description = (
        "Altera titulo/horario de um evento CalDAV (reagendar). REQUER confirmacao."
    )
    parameters: dict[str, Any] = {
        "type": "object",
        "properties": {
            "uid": {"type": "string"},
            "title": {"type": "string"},
            "start": {"type": "string"},
            "end": {"type": "string"},
            "description": {"type": "string"},
            "confirmed": {"type": "boolean"},
        },
        "required": ["uid"],
    }

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()

    async def execute(self, arguments: dict[str, Any]) -> SkillResult:
        uid = str(arguments.get("uid") or "").strip()
        if not uid:
            return SkillResult(success=False, content="", error="uid em falta")
        payload = {
            "uid": uid,
            "title": arguments.get("title"),
            "start": arguments.get("start"),
            "end": arguments.get("end"),
            "description": arguments.get("description"),
        }
        preview = {k: v for k, v in payload.items() if v}
        if not is_confirmed(arguments):
            return confirmation_required_result(
                action=self.name,
                target=uid,
                summary=f"alterar o evento {uid}",
                consequences="O calendario sera actualizado.",
                payload=payload,
                preview=preview,
            )
        s = self._settings
        if not calendar_available(s):
            return SkillResult(success=False, content="", error="Calendario nao configurado (Google ou CalDAV).")
        try:
            updated = modify_event(
                s,
                uid=uid,
                title=arguments.get("title"),
                start=arguments.get("start"),
                end=arguments.get("end"),
                description=arguments.get("description"),
            )
        except CalendarProviderError as exc:
            return SkillResult(success=False, content="", error=str(exc))
        invalidate_context_cache()
        record_action("modify_event", uid)
        return SkillResult(
            success=True,
            content=f"Evento actualizado: {updated.get('summary')} ({updated.get('start')}).",
            metadata={"kind": "calendar", "updated": updated},
        )


class FindFreeSlotsSkill:
    name = "find_free_slots"
    description = (
        "Encontra horarios livres no calendario (working hours + preferencias). "
        "Usa para 'quando posso falar', 'slots livres'."
    )
    parameters: dict[str, Any] = {
        "type": "object",
        "properties": {
            "duration_min": {"type": "integer", "minimum": 15, "maximum": 240},
            "days": {"type": "integer", "minimum": 1, "maximum": 14},
            "limit": {"type": "integer", "minimum": 1, "maximum": 10},
        },
        "required": [],
    }

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()

    async def execute(self, arguments: dict[str, Any]) -> SkillResult:
        s = self._settings
        if not calendar_available(s):
            return SkillResult(success=False, content="", error="Calendario nao configurado (Google ou CalDAV).")
        patterns = get_user_patterns(s)
        duration = int(
            arguments.get("duration_min")
            or patterns.get("preferred_meeting_duration")
            or 30
        )
        days = int(arguments.get("days") or 5)
        limit = int(arguments.get("limit") or 5)
        try:
            slots = find_free_slots(
                s,
                days=days,
                duration_min=duration,
                working_hours=str(patterns.get("working_hours") or "9:00-18:00"),
                preferred_hour=int(patterns.get("preferred_meeting_hour") or 14),
                limit=limit,
            )
        except CalendarProviderError as exc:
            return SkillResult(success=False, content="", error=str(exc))
        record_action("find_free_slots", f"{len(slots)} slots")
        if not slots:
            return SkillResult(
                success=True,
                content="Nao encontrei slots livres nessa janela.",
                metadata={"kind": "calendar", "slots": []},
            )
        lines = [f"Slots livres ({duration} min):"]
        for sl in slots:
            lines.append(f"- {sl['start']} → {sl['end']}")
        return SkillResult(
            success=True,
            content="\n".join(lines),
            metadata={"kind": "calendar", "slots": slots},
        )


class SummarizeDaySkill:
    name = "summarize_day"
    description = (
        "Resume o dia: reunioes proximas + emails pendentes (usa CONTEXT). "
        "Usa para 'como esta o meu dia', 'resumo de hoje'."
    )
    parameters: dict[str, Any] = {"type": "object", "properties": {}, "required": []}

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()

    async def execute(self, arguments: dict[str, Any]) -> SkillResult:
        from friday.productivity.context import build_productivity_context

        ctx = build_productivity_context(self._settings, force=True)
        meetings = ctx.get("upcoming_meetings") or []
        emails = ctx.get("pending_emails") or []
        lines = [f"Agora: {ctx.get('current_time')}."]
        if meetings:
            lines.append(f"Proximas reunioes ({len(meetings)}):")
            for m in meetings[:5]:
                lines.append(f"- {m.get('start')}: {m.get('title')} ({m.get('time_until')})")
        else:
            lines.append("Sem reunioes proximas.")
        high = [e for e in emails if e.get("priority") == "high"]
        if emails:
            lines.append(f"Emails recentes: {len(emails)} (prioridade alta: {len(high)}).")
            for e in (high or emails)[:3]:
                lines.append(f"- {e.get('from')}: {e.get('subject')}")
        else:
            lines.append("Sem emails pendentes no contexto.")
        lines.append("Quer que detalhe a agenda ou a inbox?")
        record_action("summarize_day", f"m={len(meetings)} e={len(emails)}")
        return SkillResult(
            success=True,
            content="\n".join(lines),
            metadata={"kind": "summary", "context": ctx},
        )


class StatusCheckSkill:
    name = "status_check"
    description = (
        "Estado rapido: emails high-priority / unread e alertas. "
        "Usa para 'tens emails importantes?', 'status'."
    )
    parameters: dict[str, Any] = {"type": "object", "properties": {}, "required": []}

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()

    async def execute(self, arguments: dict[str, Any]) -> SkillResult:
        from friday.productivity.alerts import compute_alerts
        from friday.productivity.context import build_productivity_context

        ctx = build_productivity_context(self._settings, force=True)
        emails = [e for e in (ctx.get("pending_emails") or []) if e.get("priority") == "high"]
        alerts = compute_alerts(self._settings, ctx=ctx)
        lines: list[str] = []
        if emails:
            lines.append(f"{len(emails)} email(s) de prioridade alta:")
            for e in emails[:5]:
                lines.append(
                    f"- {e.get('from')}: {e.get('subject')} (~{e.get('days_waiting')}d)"
                )
        else:
            lines.append("Sem emails de prioridade alta no contexto.")
        if alerts:
            lines.append("Alertas:")
            for a in alerts[:3]:
                lines.append(f"- {a.get('message')} {a.get('cta') or ''}")
        record_action("status_check", f"high={len(emails)} alerts={len(alerts)}")
        return SkillResult(
            success=True,
            content="\n".join(lines),
            metadata={"kind": "status", "alerts": alerts, "emails": emails},
        )
