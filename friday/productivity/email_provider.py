"""Email provider — Gmail primary, IMAP/SMTP fallback (Fase 4)."""

from __future__ import annotations

import base64
from email.message import EmailMessage
from typing import Any

from friday.config import Settings, get_settings
from friday.integrations.google_oauth import (
    GoogleOAuthError,
    google_connected,
    google_request,
)
from friday.productivity.email_client import (
    EmailError,
    EmailSettings,
    list_emails as imap_list,
    read_email as imap_read,
    send_email as smtp_send,
)


class EmailProviderError(RuntimeError):
    pass


def use_google(settings: Settings | None = None) -> bool:
    settings = settings or get_settings()
    return bool(settings.google_enabled and google_connected(settings))


def _imap_cfg(settings: Settings) -> EmailSettings:
    return EmailSettings(
        imap_host=settings.imap_host,
        imap_port=settings.imap_port,
        imap_user=settings.imap_user,
        imap_password=settings.imap_password,
        imap_folder=settings.imap_folder,
        smtp_host=settings.smtp_host,
        smtp_port=settings.smtp_port,
        smtp_user=settings.smtp_user,
        smtp_password=settings.smtp_password,
        smtp_from=settings.smtp_from,
        use_ssl=settings.email_use_ssl,
    )


def email_available(settings: Settings | None = None) -> bool:
    settings = settings or get_settings()
    if use_google(settings):
        return True
    return bool(settings.email_enabled and settings.imap_host and settings.imap_user)


def list_emails(
    settings: Settings | None = None, *, limit: int = 10
) -> list[dict[str, Any]]:
    settings = settings or get_settings()
    if use_google(settings):
        return _gmail_list(settings, limit=limit)
    if not settings.email_enabled:
        raise EmailProviderError("Email nao configurado (Google ou IMAP).")
    try:
        return imap_list(_imap_cfg(settings), limit=limit)
    except EmailError as exc:
        raise EmailProviderError(str(exc)) from exc


def read_email(
    settings: Settings | None = None, *, message_id: str
) -> dict[str, Any]:
    settings = settings or get_settings()
    if use_google(settings):
        return _gmail_read(settings, message_id=message_id)
    try:
        return imap_read(_imap_cfg(settings), message_id)
    except EmailError as exc:
        raise EmailProviderError(str(exc)) from exc


def send_email(
    settings: Settings | None = None,
    *,
    to: str,
    subject: str,
    body: str,
) -> dict[str, Any]:
    settings = settings or get_settings()
    if use_google(settings):
        return _gmail_send(settings, to=to, subject=subject, body=body)
    try:
        return smtp_send(_imap_cfg(settings), to=to, subject=subject, body=body)
    except EmailError as exc:
        raise EmailProviderError(str(exc)) from exc


def _gmail_list(settings: Settings, *, limit: int) -> list[dict[str, Any]]:
    limit = max(1, min(50, int(limit)))
    try:
        listing = google_request(
            f"https://gmail.googleapis.com/gmail/v1/users/me/messages?maxResults={limit}",
            settings=settings,
        )
    except GoogleOAuthError as exc:
        raise EmailProviderError(str(exc)) from exc
    messages: list[dict[str, Any]] = []
    for item in listing.get("messages") or []:
        mid = item.get("id") or ""
        if not mid:
            continue
        try:
            meta = google_request(
                f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{mid}"
                f"?format=metadata&metadataHeaders=Subject&metadataHeaders=From"
                f"&metadataHeaders=Date",
                settings=settings,
            )
        except GoogleOAuthError:
            continue
        headers = {
            h.get("name", "").lower(): h.get("value", "")
            for h in (meta.get("payload") or {}).get("headers") or []
        }
        messages.append(
            {
                "id": mid,
                "subject": headers.get("subject") or "(sem assunto)",
                "from": headers.get("from") or "",
                "date": headers.get("date") or "",
            }
        )
    return messages


def _gmail_read(settings: Settings, *, message_id: str) -> dict[str, Any]:
    mid = (message_id or "").strip()
    if not mid:
        raise EmailProviderError("message_id em falta")
    from urllib.parse import quote

    try:
        meta = google_request(
            f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{quote(mid)}?format=full",
            settings=settings,
        )
    except GoogleOAuthError as exc:
        raise EmailProviderError(str(exc)) from exc
    headers = {
        h.get("name", "").lower(): h.get("value", "")
        for h in (meta.get("payload") or {}).get("headers") or []
    }
    body = _extract_gmail_body(meta.get("payload") or {})
    return {
        "id": mid,
        "subject": headers.get("subject") or "",
        "from": headers.get("from") or "",
        "to": headers.get("to") or "",
        "date": headers.get("date") or "",
        "body": body[:4000],
    }


def _extract_gmail_body(payload: dict[str, Any]) -> str:
    if payload.get("body", {}).get("data"):
        return _b64url_decode(payload["body"]["data"])
    for part in payload.get("parts") or []:
        mime = part.get("mimeType") or ""
        if mime == "text/plain" and part.get("body", {}).get("data"):
            return _b64url_decode(part["body"]["data"])
    for part in payload.get("parts") or []:
        nested = _extract_gmail_body(part)
        if nested:
            return nested
    return ""


def _b64url_decode(data: str) -> str:
    padded = data + "=" * (-len(data) % 4)
    try:
        return base64.urlsafe_b64decode(padded.encode("utf-8")).decode(
            "utf-8", errors="replace"
        )
    except Exception:
        return ""


def _gmail_send(
    settings: Settings, *, to: str, subject: str, body: str
) -> dict[str, Any]:
    if not to:
        raise EmailProviderError("destinatario em falta")
    msg = EmailMessage()
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(body or "")
    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode("utf-8").rstrip("=")
    try:
        google_request(
            "https://gmail.googleapis.com/gmail/v1/users/me/messages/send",
            settings=settings,
            method="POST",
            body={"raw": raw},
        )
    except GoogleOAuthError as exc:
        raise EmailProviderError(str(exc)) from exc
    return {"to": to, "subject": subject, "from": "me"}
