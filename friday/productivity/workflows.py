"""Multi-step gated productivity workflows (one ConfirmationGate step at a time)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from friday.safety.confirmation import PendingAction


@dataclass
class WorkflowStep:
    action: str
    target: str
    summary: str
    consequences: str = ""
    payload: dict[str, Any] = field(default_factory=dict)
    preview: dict[str, Any] = field(default_factory=dict)


@dataclass
class WorkflowQueue:
    """Session-scoped queue; advances after each confirmed step."""

    steps: list[WorkflowStep] = field(default_factory=list)
    index: int = 0
    label: str = ""

    def current(self) -> WorkflowStep | None:
        if 0 <= self.index < len(self.steps):
            return self.steps[self.index]
        return None

    def to_pending(self) -> PendingAction | None:
        step = self.current()
        if not step:
            return None
        return PendingAction(
            action=step.action,
            target=step.target,
            summary=step.summary,
            consequences=step.consequences
            or (f"Passo {self.index + 1}/{len(self.steps)} do workflow {self.label}."),
            payload=dict(step.payload),
            preview=dict(step.preview),
        )

    def advance(self) -> PendingAction | None:
        self.index += 1
        return self.to_pending()

    def done(self) -> bool:
        return self.index >= len(self.steps)


def build_meeting_invite_workflow(
    *,
    title: str,
    start: str,
    end: str | None,
    to: str,
    body: str = "",
    remind_hours_before: int = 24,
) -> WorkflowQueue:
    """create_calendar_event → send_email agenda → schedule_local_reminder."""
    end = end or ""
    steps = [
        WorkflowStep(
            action="create_calendar_event",
            target=title,
            summary=f"criar o evento '{title}' em {start}",
            consequences="O evento sera gravado no calendario CalDAV.",
            payload={"title": title, "start": start, "end": end or None, "description": ""},
            preview={"title": title, "start": start, "end": end},
        ),
        WorkflowStep(
            action="send_email",
            target=to,
            summary=f"enviar agenda de '{title}' para {to}",
            consequences="A mensagem sera enviada via SMTP.",
            payload={
                "to": to,
                "subject": f"Agenda: {title}",
                "body": body
                or f"Segue a reuniao '{title}' marcada para {start}.",
            },
            preview={
                "to": to,
                "subject": f"Agenda: {title}",
                "body": body
                or f"Segue a reuniao '{title}' marcada para {start}.",
            },
        ),
        WorkflowStep(
            action="schedule_local_reminder",
            target=title,
            summary=f"agendar lembrete {remind_hours_before}h antes de '{title}'",
            consequences="Fica um alerta local na FRIDAY (nao envia email sozinho).",
            payload={
                "title": title,
                "event_start": start,
                "hours_before": remind_hours_before,
                "message": f"Lembrete: reuniao '{title}' amanha/em breve ({start}).",
            },
            preview={
                "title": title,
                "event_start": start,
                "hours_before": remind_hours_before,
            },
        ),
    ]
    return WorkflowQueue(steps=steps, label="meeting_invite")
