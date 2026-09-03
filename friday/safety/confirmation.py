"""Confirmation gate for irreversible / privileged future actions."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from typing import Any


def _normalize(text: str) -> str:
    text = text.casefold().strip()
    text = unicodedata.normalize("NFD", text)
    return "".join(c for c in text if unicodedata.category(c) != "Mn")


_AFFIRM = re.compile(
    r"^(sim|yes|ok|okay|confirma|confirm|pode|podes|avanca|go ahead|faz|do it)\b",
    re.I,
)
_DENY = re.compile(
    r"^(nao|não|no|cancela|cancel|para|stop|desiste)\b",
    re.I,
)


# Skills that must not mutate until ConfirmationGate confirms.
GATED_SKILLS = frozenset(
    {
        "create_calendar_event",
        "cancel_calendar_event",
        "modify_calendar_event",
        "send_email",
        "draft_email_reply",
        "schedule_local_reminder",
    }
)


@dataclass
class PendingAction:
    action: str
    target: str
    summary: str
    consequences: str = ""
    payload: dict[str, Any] = field(default_factory=dict)
    preview: dict[str, Any] = field(default_factory=dict)

    def prompt_message(self) -> str:
        parts = [
            f"Antes de continuar: vou {self.summary}.",
            f"Alvo: {self.target}.",
        ]
        if self.preview:
            if self.preview.get("subject"):
                parts.append(f"Assunto: {self.preview['subject']}.")
            if self.preview.get("body"):
                body = str(self.preview["body"])
                parts.append(f"Corpo: {body[:200]}{'…' if len(body) > 200 else ''}.")
            if self.preview.get("title"):
                parts.append(
                    f"Evento: {self.preview.get('title')} "
                    f"{self.preview.get('start') or ''}."
                )
        if self.consequences:
            parts.append(f"Consequencias: {self.consequences}.")
        parts.append("Confirmas? Diz sim ou nao.")
        return " ".join(parts)


class ConfirmationGate:
    """
    Holds at most one pending irreversible action.

    A prior "sim" never authorizes a different action. Only the next user
    utterance can confirm or deny the current pending action.
    """

    def __init__(self) -> None:
        self._pending: PendingAction | None = None

    @property
    def pending(self) -> PendingAction | None:
        return self._pending

    def request(self, action: PendingAction) -> str:
        self._pending = action
        return action.prompt_message()

    def clear(self) -> None:
        self._pending = None

    def interpret(self, user_text: str) -> tuple[str, PendingAction | None]:
        """
        Returns (status, action) where status is:
        - "none" — nothing pending
        - "confirmed" — user affirmed current pending
        - "denied" — user denied
        - "waiting" — pending but utterance is not a clear yes/no
        """
        if self._pending is None:
            return "none", None
        norm = _normalize(user_text)
        if _AFFIRM.search(norm):
            action = self._pending
            self._pending = None
            return "confirmed", action
        if _DENY.search(norm):
            action = self._pending
            self._pending = None
            return "denied", action
        return "waiting", self._pending


# Policy for privileged skills (email, files, calendar, shell, purchases):
CONFIRMATION_POLICY = """
A FRIDAY pede confirmacao explicita antes de:
- Enviar emails ou mensagens (send_email / draft_email_reply)
- Criar, alterar ou cancelar eventos de calendario
- Apagar ou substituir ficheiros
- Executar comandos potencialmente perigosos
- Fazer compras ou pagamentos
- Partilhar informacao ou documentos
- Qualquer accao irreversivel

A confirmacao deve incluir a accao exacta, o alvo, preview (assunto/corpo ou titulo/hora) e
consequencias relevantes. Uma resposta afirmativa antiga nao autoriza
uma accao nova — usa ConfirmationGate.request / interpret.
"""
