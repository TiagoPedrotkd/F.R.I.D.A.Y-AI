"""IMAP/SMTP email helpers (stdlib)."""

from __future__ import annotations

import email
import imaplib
import logging
import smtplib
import ssl
from dataclasses import dataclass
from email.header import decode_header, make_header
from email.message import EmailMessage
from email.utils import parsedate_to_datetime
from typing import Any

logger = logging.getLogger(__name__)


class EmailError(RuntimeError):
    pass


@dataclass
class EmailSettings:
    imap_host: str
    imap_port: int
    imap_user: str
    imap_password: str
    imap_folder: str = "INBOX"
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = ""
    use_ssl: bool = True


def _decode_mime(value: str | None) -> str:
    if not value:
        return ""
    try:
        return str(make_header(decode_header(value)))
    except Exception:
        return value


def list_emails(cfg: EmailSettings, *, limit: int = 10) -> list[dict[str, Any]]:
    if not cfg.imap_host or not cfg.imap_user:
        raise EmailError("IMAP nao configurado (IMAP_HOST / IMAP_USER)")
    limit = max(1, min(50, int(limit)))
    messages: list[dict[str, Any]] = []
    try:
        if cfg.use_ssl:
            conn = imaplib.IMAP4_SSL(cfg.imap_host, cfg.imap_port)
        else:
            conn = imaplib.IMAP4(cfg.imap_host, cfg.imap_port)
        with conn:
            conn.login(cfg.imap_user, cfg.imap_password)
            conn.select(cfg.imap_folder, readonly=True)
            typ, data = conn.search(None, "ALL")
            if typ != "OK" or not data or not data[0]:
                return []
            ids = data[0].split()
            for msg_id in reversed(ids[-limit:]):
                typ, fetched = conn.fetch(msg_id, "(BODY.PEEK[HEADER.FIELDS (SUBJECT FROM DATE)])")
                if typ != "OK" or not fetched or not fetched[0]:
                    continue
                raw = fetched[0][1]
                msg = email.message_from_bytes(raw)
                date_s = ""
                try:
                    if msg.get("Date"):
                        date_s = parsedate_to_datetime(msg["Date"]).isoformat()
                except Exception:
                    date_s = msg.get("Date") or ""
                messages.append(
                    {
                        "id": msg_id.decode() if isinstance(msg_id, bytes) else str(msg_id),
                        "subject": _decode_mime(msg.get("Subject")),
                        "from": _decode_mime(msg.get("From")),
                        "date": date_s,
                    }
                )
    except EmailError:
        raise
    except Exception as exc:
        raise EmailError(f"Falha IMAP: {exc}") from exc
    return messages


def read_email(cfg: EmailSettings, message_id: str) -> dict[str, Any]:
    if not cfg.imap_host or not cfg.imap_user:
        raise EmailError("IMAP nao configurado")
    mid = (message_id or "").strip().encode()
    if not mid:
        raise EmailError("message_id em falta")
    try:
        if cfg.use_ssl:
            conn = imaplib.IMAP4_SSL(cfg.imap_host, cfg.imap_port)
        else:
            conn = imaplib.IMAP4(cfg.imap_host, cfg.imap_port)
        with conn:
            conn.login(cfg.imap_user, cfg.imap_password)
            conn.select(cfg.imap_folder, readonly=True)
            typ, fetched = conn.fetch(mid, "(RFC822)")
            if typ != "OK" or not fetched or not fetched[0]:
                raise EmailError(f"Mensagem {message_id} nao encontrada")
            raw = fetched[0][1]
            msg = email.message_from_bytes(raw)
            body = ""
            if msg.is_multipart():
                for part in msg.walk():
                    ctype = part.get_content_type()
                    if ctype == "text/plain" and not part.get_filename():
                        charset = part.get_content_charset() or "utf-8"
                        body = part.get_payload(decode=True).decode(charset, errors="replace")
                        break
            else:
                charset = msg.get_content_charset() or "utf-8"
                payload = msg.get_payload(decode=True)
                body = payload.decode(charset, errors="replace") if payload else ""
            return {
                "id": message_id,
                "subject": _decode_mime(msg.get("Subject")),
                "from": _decode_mime(msg.get("From")),
                "to": _decode_mime(msg.get("To")),
                "date": msg.get("Date") or "",
                "body": body[:4000],
            }
    except EmailError:
        raise
    except Exception as exc:
        raise EmailError(f"Falha a ler email: {exc}") from exc


def send_email(
    cfg: EmailSettings,
    *,
    to: str,
    subject: str,
    body: str,
) -> dict[str, Any]:
    host = cfg.smtp_host or cfg.imap_host
    user = cfg.smtp_user or cfg.imap_user
    password = cfg.smtp_password or cfg.imap_password
    from_addr = cfg.smtp_from or user
    if not host or not user or not to:
        raise EmailError("SMTP nao configurado ou destinatario em falta")

    msg = EmailMessage()
    msg["From"] = from_addr
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(body or "")

    try:
        if cfg.smtp_port == 465:
            context = ssl.create_default_context()
            with smtplib.SMTP_SSL(host, cfg.smtp_port, context=context) as smtp:
                smtp.login(user, password)
                smtp.send_message(msg)
        else:
            with smtplib.SMTP(host, cfg.smtp_port, timeout=30) as smtp:
                smtp.ehlo()
                if cfg.use_ssl:
                    smtp.starttls(context=ssl.create_default_context())
                    smtp.ehlo()
                smtp.login(user, password)
                smtp.send_message(msg)
    except Exception as exc:
        raise EmailError(f"Falha SMTP: {exc}") from exc
    return {"to": to, "subject": subject, "from": from_addr}
