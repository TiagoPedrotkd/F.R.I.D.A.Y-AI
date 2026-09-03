"""Helpers for skills that require ConfirmationGate before mutating."""

from __future__ import annotations

from typing import Any

from friday.skills.base import SkillResult


def confirmation_required_result(
    *,
    action: str,
    target: str,
    summary: str,
    consequences: str,
    payload: dict[str, Any],
    preview: dict[str, Any] | None = None,
) -> SkillResult:
    """Return a soft-success that asks the host to open ConfirmationGate."""
    pending = {
        "action": action,
        "target": target,
        "summary": summary,
        "consequences": consequences,
        "payload": payload,
        "preview": preview or {},
    }
    preview_bits = ""
    if preview:
        if preview.get("subject"):
            preview_bits += f" Assunto: {preview.get('subject')}."
        if preview.get("body"):
            body = str(preview.get("body") or "")
            preview_bits += f" Corpo: {body[:160]}{'…' if len(body) > 160 else ''}."
        if preview.get("title"):
            preview_bits += f" Evento: {preview.get('title')} {preview.get('start') or ''}."
        if preview.get("overlaps"):
            preview_bits += " Ha conflitos de calendario."
    content = (
        f"Antes de continuar: vou {summary}. Alvo: {target}."
        f"{preview_bits} {consequences} Confirmas? Diz sim ou nao."
    )
    return SkillResult(
        success=True,
        content=content,
        metadata={"kind": "confirmation_required", "pending": pending},
    )


def is_confirmed(arguments: dict[str, Any]) -> bool:
    return bool(arguments.get("confirmed"))
