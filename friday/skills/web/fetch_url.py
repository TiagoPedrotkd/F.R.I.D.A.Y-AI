"""Fetch and extract main text from a URL (with SSRF guards)."""

from __future__ import annotations

import ipaddress
import logging
import re
import socket
from typing import Any
from urllib.parse import urlparse

import httpx

from friday.skills.base import SkillResult

logger = logging.getLogger(__name__)

_MAX_CHARS = 4000
_TIMEOUT = 20.0
_TEXT_TYPES = (
    "text/",
    "application/json",
    "application/xml",
    "application/xhtml",
    "application/atom",
    "application/rss",
)


def _is_blocked_host(hostname: str) -> bool:
    host = (hostname or "").strip().casefold().rstrip(".")
    if not host:
        return True
    if host in ("localhost", "localhost.localdomain") or host.endswith(".localhost"):
        return True
    if host.endswith(".local") or host.endswith(".internal"):
        return True
    # Literal IPs
    try:
        ip = ipaddress.ip_address(host)
        return (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_reserved
            or ip.is_multicast
            or ip.is_unspecified
        )
    except ValueError:
        pass
    # Resolve DNS and check all addresses
    try:
        infos = socket.getaddrinfo(host, None)
    except socket.gaierror:
        return True
    for info in infos:
        addr = info[4][0]
        try:
            ip = ipaddress.ip_address(addr)
        except ValueError:
            continue
        if (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_reserved
            or ip.is_multicast
            or ip.is_unspecified
        ):
            return True
    return False


def _validate_url(url: str) -> str | None:
    """Return error message or None if OK."""
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        return "Preciso que confirme o endereco (URL http ou https)."
    host = parsed.hostname or ""
    if _is_blocked_host(host):
        return "Esse endereco nao e permitido por seguranca."
    return None


def _extract_title(html: str) -> str:
    m = re.search(r"<title[^>]*>(.*?)</title>", html, flags=re.I | re.S)
    if not m:
        return ""
    title = re.sub(r"\s+", " ", m.group(1)).strip()
    return title[:200]


class FetchUrlSkill:
    name = "fetch_url"
    description = (
        "Le uma pagina web e extrai o texto principal. "
        "Usa quando houver um URL para ler, consultar ou resumir."
    )
    parameters: dict[str, Any] = {
        "type": "object",
        "properties": {
            "url": {
                "type": "string",
                "description": "URL http(s) a ler",
            }
        },
        "required": ["url"],
    }

    async def execute(self, arguments: dict[str, Any]) -> SkillResult:
        url = (arguments.get("url") or "").strip()
        if not url:
            return SkillResult(
                success=False,
                content="",
                error="Preciso que confirme o endereco (URL).",
            )
        err = _validate_url(url)
        if err:
            return SkillResult(success=False, content="", error=err)

        try:
            async with httpx.AsyncClient(
                follow_redirects=True,
                timeout=_TIMEOUT,
                headers={"User-Agent": "FRIDAY-AI/0.2"},
            ) as client:
                resp = await client.get(url)
                resp.raise_for_status()
                # Re-validate final URL after redirects (SSRF)
                final = str(resp.url)
                err_final = _validate_url(final)
                if err_final:
                    return SkillResult(success=False, content="", error=err_final)
                ctype = (resp.headers.get("content-type") or "").casefold()
                if ctype and not any(ctype.startswith(t) for t in _TEXT_TYPES):
                    return SkillResult(
                        success=False,
                        content="",
                        error="Essa pagina nao parece texto legivel.",
                    )
                html = resp.text
        except Exception as exc:
            logger.warning("fetch_url download failed: %s", exc)
            return SkillResult(
                success=False,
                content="",
                error="Nao consegui abrir essa pagina.",
            )

        title = _extract_title(html)
        text = ""
        try:
            import trafilatura

            text = trafilatura.extract(html, include_comments=False) or ""
        except Exception as exc:
            logger.debug("trafilatura failed: %s", exc)

        if not text.strip():
            text = re.sub(r"<script[\s\S]*?</script>", " ", html, flags=re.I)
            text = re.sub(r"<style[\s\S]*?</style>", " ", text, flags=re.I)
            text = re.sub(r"<[^>]+>", " ", text)
            text = re.sub(r"\s+", " ", text).strip()

        if not text.strip():
            return SkillResult(
                success=False,
                content="",
                error="Nao encontrei resultados suficientes nesta pagina.",
            )

        truncated = text[:_MAX_CHARS]
        if len(text) > _MAX_CHARS:
            truncated += "..."

        header = f"Conteudo de {url}"
        if title:
            header += f" — {title}"
        return SkillResult(
            success=True,
            content=f"{header}:\n{truncated}",
            metadata={
                "url": url,
                "title": title,
                "chars": len(text),
                "source": urlparse(url).hostname or "",
            },
        )
