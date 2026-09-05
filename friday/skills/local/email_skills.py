"""Email skills (IMAP/SMTP)."""

from __future__ import annotations

from typing import Any

from friday.config import Settings, get_settings
from friday.productivity.contacts import resolve_contact
from friday.productivity.context import invalidate_context_cache, record_action
from friday.productivity.email_provider import (
    EmailProviderError,
    email_available,
    list_emails,
    read_email,
    send_email,
)
from friday.skills.base import SkillResult
from friday.skills.gated import confirmation_required_result, is_confirmed


async def _draft_reply_with_llm(settings: Settings, msg: dict[str, Any]) -> str:
    """Best-effort LLM draft; falls back to a short template."""
    fallback = (
        "Obrigado pela mensagem. Vou analisar e retorno em breve.\n\n"
        f"— A proposito de: {msg.get('subject')}"
    )
    try:
        import asyncio

        from friday.llm.client import LlmClient

        client = LlmClient(settings)
        prompt = (
            "Redige um email de resposta profissional em portugues europeu, "
            "conciso (5-8 linhas), sem assunto, sem markdown.\n"
            f"De: {msg.get('from')}\n"
            f"Assunto: {msg.get('subject')}\n"
            f"Corpo original:\n{(msg.get('body') or '')[:2000]}\n"
        )

        def _call() -> str:
            client.ensure_model_ready()
            resp = client.create_completion(
                messages=[
                    {
                        "role": "system",
                        "content": "Escreves rascunhos de email para a F.R.I.D.A.Y. So o corpo.",
                    },
                    {"role": "user", "content": prompt},
                ],
                max_tokens=350,
                temperature=0.4,
            )
            return (resp.choices[0].message.content or "").strip()

        text = await asyncio.to_thread(_call)
        return text or fallback
    except Exception:
        return fallback


class ListEmailsSkill:
    name = "list_emails"
    description = (
        "Lista emails recentes da caixa IMAP (assunto, de, data). "
        "Usa para 'ha emails novos', 'mostra a inbox'."
    )
    parameters: dict[str, Any] = {
        "type": "object",
        "properties": {
            "limit": {
                "type": "integer",
                "description": "Quantos emails (default 10, max 50)",
                "minimum": 1,
                "maximum": 50,
            }
        },
        "required": [],
    }

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()

    async def execute(self, arguments: dict[str, Any]) -> SkillResult:
        s = self._settings
        if not email_available(s):
            return SkillResult(
                success=False,
                content="",
                error="Email desactivado (EMAIL_ENABLED=false).",
            )
        limit = int(arguments.get("limit") or 10)
        try:
            items = list_emails(s, limit=limit)
        except EmailProviderError as exc:
            return SkillResult(success=False, content="", error=str(exc))
        if not items:
            return SkillResult(
                success=True,
                content="Caixa vazia ou sem mensagens recentes.",
                metadata={"kind": "email", "emails": []},
            )
        lines = ["Emails recentes:"]
        for m in items:
            lines.append(
                f"- [{m['id']}] {m.get('date', '')} | {m.get('from', '')} | {m.get('subject', '')}"
            )
        return SkillResult(
            success=True,
            content="\n".join(lines),
            metadata={"kind": "email", "emails": items},
        )


class ReadEmailSkill:
    name = "read_email"
    description = "Le o corpo de um email pelo id IMAP (de list_emails)."
    parameters: dict[str, Any] = {
        "type": "object",
        "properties": {
            "message_id": {"type": "string", "description": "Id IMAP da mensagem"},
        },
        "required": ["message_id"],
    }

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()

    async def execute(self, arguments: dict[str, Any]) -> SkillResult:
        s = self._settings
        if not email_available(s):
            return SkillResult(
                success=False,
                content="",
                error="Email desactivado (EMAIL_ENABLED=false).",
            )
        mid = str(arguments.get("message_id") or "").strip()
        if not mid:
            return SkillResult(success=False, content="", error="message_id em falta")
        try:
            msg = read_email(s, message_id=mid)
        except EmailProviderError as exc:
            return SkillResult(success=False, content="", error=str(exc))
        content = (
            f"De: {msg.get('from')}\n"
            f"Para: {msg.get('to')}\n"
            f"Assunto: {msg.get('subject')}\n"
            f"Data: {msg.get('date')}\n\n"
            f"{msg.get('body', '')}"
        )
        return SkillResult(
            success=True,
            content=content,
            metadata={"kind": "email", "message": msg},
        )


class SendEmailSkill:
    name = "send_email"
    description = (
        "Envia um email via SMTP. REQUER confirmacao do utilizador antes de enviar."
    )
    parameters: dict[str, Any] = {
        "type": "object",
        "properties": {
            "to": {"type": "string", "description": "Destinatario"},
            "subject": {"type": "string"},
            "body": {"type": "string"},
            "confirmed": {
                "type": "boolean",
                "description": "Interno: true apos ConfirmationGate",
            },
        },
        "required": ["to", "subject", "body"],
    }

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()

    async def execute(self, arguments: dict[str, Any]) -> SkillResult:
        to_raw = str(arguments.get("to") or "").strip()
        subject = str(arguments.get("subject") or "").strip()
        body = str(arguments.get("body") or "")
        if not to_raw or not subject:
            return SkillResult(
                success=False,
                content="",
                error="Preciso de to e subject.",
            )
        resolved = resolve_contact(to_raw, self._settings)
        if resolved["status"] == "ambiguous":
            opts = "; ".join(
                f"{m.get('name')} <{m.get('email')}>" for m in resolved["matches"][:5]
            )
            return SkillResult(
                success=True,
                content=f"Qual contacto? {opts}",
                metadata={"kind": "disambiguation", "matches": resolved["matches"]},
            )
        if resolved["status"] == "exact":
            to = str(resolved.get("email") or to_raw)
        else:
            to = to_raw
            if "@" not in to:
                return SkillResult(
                    success=False,
                    content="",
                    error=f"Nao conheco o contacto '{to_raw}'. Indica o email completo.",
                )
        payload = {"to": to, "subject": subject, "body": body}
        preview = {"to": to, "subject": subject, "body": body}
        if not is_confirmed(arguments):
            return confirmation_required_result(
                action=self.name,
                target=to,
                summary=f"enviar um email para {to} com assunto '{subject}'",
                consequences="A mensagem sera enviada de verdade via SMTP.",
                payload=payload,
                preview=preview,
            )
        s = self._settings
        if not email_available(s):
            return SkillResult(
                success=False,
                content="",
                error="Email desactivado (EMAIL_ENABLED=false).",
            )
        try:
            sent = send_email(s, to=to, subject=subject, body=body)
        except EmailProviderError as exc:
            return SkillResult(success=False, content="", error=str(exc))
        invalidate_context_cache()
        record_action("send_email", to)
        try:
            from friday.productivity.patterns import bump_pattern_counter

            bump_pattern_counter("confirmed_sends")
        except Exception:
            pass
        return SkillResult(
            success=True,
            content=f"Email enviado para {sent['to']} (assunto: {sent['subject']}).",
            metadata={"kind": "email", "sent": sent},
        )


class DraftEmailReplySkill:
    name = "draft_email_reply"
    description = (
        "Le um email e prepara resposta; apos confirmacao envia via SMTP. "
        "Usa para 'responde ao email do boss', 'draft reply'."
    )
    parameters: dict[str, Any] = {
        "type": "object",
        "properties": {
            "message_id": {"type": "string"},
            "body": {
                "type": "string",
                "description": "Corpo da resposta (se vazio, gera rascunho curto)",
            },
            "confirmed": {"type": "boolean"},
        },
        "required": ["message_id"],
    }

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()

    async def execute(self, arguments: dict[str, Any]) -> SkillResult:
        s = self._settings
        mid = str(arguments.get("message_id") or "").strip()
        if not mid:
            return SkillResult(success=False, content="", error="message_id em falta")
        if not email_available(s):
            return SkillResult(
                success=False, content="", error="Email desactivado (EMAIL_ENABLED=false)."
            )
        try:
            msg = read_email(s, message_id=mid)
        except EmailProviderError as exc:
            return SkillResult(success=False, content="", error=str(exc))
        to = str(msg.get("from") or "").strip()
        # extract email from "Name <email>"
        import re

        m = re.search(r"[\w.+-]+@[\w.-]+", to)
        to_addr = m.group(0) if m else to
        subj = str(msg.get("subject") or "")
        if not subj.lower().startswith("re:"):
            subj = f"Re: {subj}"
        body = str(arguments.get("body") or "").strip()
        if not body:
            body = await _draft_reply_with_llm(s, msg)
        payload = {"to": to_addr, "subject": subj, "body": body, "message_id": mid}
        preview = {"to": to_addr, "subject": subj, "body": body}
        if not is_confirmed(arguments):
            return confirmation_required_result(
                action="send_email",
                target=to_addr,
                summary=f"enviar resposta a {to_addr}",
                consequences="A resposta sera enviada via SMTP.",
                payload={"to": to_addr, "subject": subj, "body": body},
                preview=preview,
            )
        try:
            sent = send_email(s, to=to_addr, subject=subj, body=body)
        except EmailProviderError as exc:
            return SkillResult(success=False, content="", error=str(exc))
        invalidate_context_cache()
        record_action("draft_email_reply", to_addr)
        return SkillResult(
            success=True,
            content=f"Resposta enviada para {sent['to']}.",
            metadata={"kind": "email", "sent": sent, "draft": payload},
        )


class ResolveContactSkill:
    name = "resolve_contact"
    description = (
        "Resolve um nome para email na agenda local. "
        "Se ambiguo, devolve opcoes para o utilizador escolher."
    )
    parameters: dict[str, Any] = {
        "type": "object",
        "properties": {"query": {"type": "string"}},
        "required": ["query"],
    }

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()

    async def execute(self, arguments: dict[str, Any]) -> SkillResult:
        q = str(arguments.get("query") or "").strip()
        result = resolve_contact(q, self._settings)
        if result["status"] == "exact":
            return SkillResult(
                success=True,
                content=f"{result['matches'][0].get('name')} → {result.get('email')}",
                metadata={"kind": "contact", **result},
            )
        if result["status"] == "ambiguous":
            opts = "; ".join(
                f"{m.get('name')} <{m.get('email')}>" for m in result["matches"]
            )
            return SkillResult(
                success=True,
                content=f"Varios contactos para '{q}': {opts}. Qual?",
                metadata={"kind": "disambiguation", **result},
            )
        return SkillResult(
            success=False,
            content="",
            error=f"Contacto '{q}' nao encontrado. Indica o email.",
        )


class StartMeetingWorkflowSkill:
    name = "start_meeting_workflow"
    description = (
        "Workflow: criar evento + enviar email de agenda (confirmacao por passo). "
        "Usa para 'marca reuniao e envia convite'."
    )
    parameters: dict[str, Any] = {
        "type": "object",
        "properties": {
            "title": {"type": "string"},
            "start": {"type": "string"},
            "end": {"type": "string"},
            "to": {"type": "string", "description": "Email do destinatario do convite"},
            "body": {"type": "string"},
        },
        "required": ["title", "start", "to"],
    }

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()

    async def execute(self, arguments: dict[str, Any]) -> SkillResult:
        from friday.productivity.workflows import build_meeting_invite_workflow

        title = str(arguments.get("title") or "").strip()
        start = str(arguments.get("start") or "").strip()
        to = str(arguments.get("to") or "").strip()
        if not title or not start or not to:
            return SkillResult(
                success=False,
                content="",
                error="Preciso de title, start e to.",
            )
        resolved = resolve_contact(to, self._settings)
        if resolved["status"] == "ambiguous":
            opts = "; ".join(
                f"{m.get('name')} <{m.get('email')}>" for m in resolved["matches"][:5]
            )
            return SkillResult(
                success=True,
                content=f"Qual contacto para o convite? {opts}",
                metadata={"kind": "disambiguation", "matches": resolved["matches"]},
            )
        if resolved["status"] == "exact":
            to = str(resolved.get("email") or to)
        wf = build_meeting_invite_workflow(
            title=title,
            start=start,
            end=str(arguments.get("end") or "") or None,
            to=to,
            body=str(arguments.get("body") or ""),
        )
        step = wf.current()
        assert step is not None
        # Serialize remaining steps (including current) for session workflow queue
        steps_data = [
            {
                "action": s.action,
                "target": s.target,
                "summary": s.summary,
                "consequences": s.consequences,
                "payload": s.payload,
                "preview": s.preview,
            }
            for s in wf.steps
        ]
        result = confirmation_required_result(
            action=step.action,
            target=step.target,
            summary=step.summary,
            consequences=step.consequences,
            payload=step.payload,
            preview=step.preview,
        )
        meta = dict(result.metadata or {})
        meta["workflow"] = {"label": wf.label, "steps": steps_data, "index": 0}
        result.metadata = meta
        return result


class ScheduleLocalReminderSkill:
    name = "schedule_local_reminder"
    description = (
        "Agenda um lembrete local (ficheiro) X horas antes de um evento. "
        "Usado em workflows; REQUER confirmacao."
    )
    parameters: dict[str, Any] = {
        "type": "object",
        "properties": {
            "title": {"type": "string"},
            "event_start": {"type": "string"},
            "hours_before": {"type": "integer", "minimum": 1, "maximum": 168},
            "message": {"type": "string"},
            "confirmed": {"type": "boolean"},
        },
        "required": ["title", "event_start"],
    }

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()

    async def execute(self, arguments: dict[str, Any]) -> SkillResult:
        from datetime import datetime, timedelta
        from zoneinfo import ZoneInfo

        from friday.productivity.reminders import schedule_reminder

        title = str(arguments.get("title") or "").strip()
        event_start = str(arguments.get("event_start") or "").strip()
        hours = int(arguments.get("hours_before") or 24)
        message = str(arguments.get("message") or f"Lembrete: {title}")
        if not title or not event_start:
            return SkillResult(
                success=False, content="", error="Preciso de title e event_start."
            )
        payload = {
            "title": title,
            "event_start": event_start,
            "hours_before": hours,
            "message": message,
        }
        if not is_confirmed(arguments):
            return confirmation_required_result(
                action=self.name,
                target=title,
                summary=f"agendar lembrete {hours}h antes de '{title}'",
                consequences="Fica um alerta local na FRIDAY.",
                payload=payload,
                preview=payload,
            )
        try:
            start = datetime.fromisoformat(event_start.replace("Z", "+00:00"))
            if start.tzinfo is None:
                start = start.replace(tzinfo=ZoneInfo("Europe/Lisbon"))
            fire = start - timedelta(hours=hours)
            item = schedule_reminder(
                title=title,
                fire_at_iso=fire.isoformat(),
                message=message,
                settings=self._settings,
            )
        except Exception as exc:
            return SkillResult(success=False, content="", error=str(exc))
        record_action("schedule_reminder", title)
        return SkillResult(
            success=True,
            content=f"Lembrete agendado para {item['fire_at']}: {title}.",
            metadata={"kind": "reminder", "item": item},
        )


class PrepareMeetingSkill:
    name = "prepare_meeting"
    description = (
        "Prepara uma reuniao: procura emails recentes com a pessoa/assunto e resume. "
        "Usa quando ha meeting iminente ou 'prepara a call com X'."
    )
    parameters: dict[str, Any] = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Nome, email ou palavra-chave (ex. Cliente X)",
            },
            "limit": {"type": "integer", "minimum": 1, "maximum": 20},
        },
        "required": ["query"],
    }

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()

    async def execute(self, arguments: dict[str, Any]) -> SkillResult:
        q = str(arguments.get("query") or "").strip().casefold()
        if not q:
            return SkillResult(success=False, content="", error="query em falta")
        s = self._settings
        lines = [f"Preparacao para '{arguments.get('query')}':"]
        # Calendar matches
        from friday.productivity.calendar_provider import calendar_available, list_events as cal_list

        if calendar_available(s):
            try:
                events = cal_list(s, days=3)
                hits = [
                    e
                    for e in events
                    if q in str(e.get("summary") or "").casefold()
                ]
                if hits:
                    lines.append("Agenda:")
                    for e in hits[:5]:
                        lines.append(f"- {e.get('start')}: {e.get('summary')}")
            except Exception as exc:
                lines.append(f"(Calendario indisponivel: {exc})")
        # Email matches
        if email_available(s):
            try:
                items = list_emails(s, limit=int(arguments.get("limit") or 15))
                matched = [
                    m
                    for m in items
                    if q in str(m.get("from") or "").casefold()
                    or q in str(m.get("subject") or "").casefold()
                ]
                if matched:
                    lines.append("Emails recentes:")
                    for m in matched[:5]:
                        lines.append(
                            f"- [{m.get('id')}] {m.get('from')}: {m.get('subject')}"
                        )
                    lines.append("Quer que prepare um rascunho de resposta a algum?")
                else:
                    lines.append("Sem emails recentes a combinar com a query.")
            except Exception as exc:
                lines.append(f"(Email indisponivel: {exc})")
        else:
            lines.append("Email desactivado — so consultei o calendario (se disponivel).")
        record_action("prepare_meeting", q)
        return SkillResult(
            success=True,
            content="\n".join(lines),
            metadata={"kind": "prepare_meeting", "query": q},
        )
