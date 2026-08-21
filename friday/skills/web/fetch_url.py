"""Fetch and extract main text from a URL."""

from __future__ import annotations

import logging
from typing import Any
from urllib.parse import urlparse

import httpx

from friday.skills.base import SkillResult

logger = logging.getLogger(__name__)

_MAX_CHARS = 4000


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
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            return SkillResult(
                success=False,
                content="",
                error="Preciso que confirme o endereco (URL http ou https).",
            )

        try:
            async with httpx.AsyncClient(
                follow_redirects=True,
                timeout=20.0,
                headers={"User-Agent": "FRIDAY-AI/0.2"},
            ) as client:
                resp = await client.get(url)
                resp.raise_for_status()
                html = resp.text
        except Exception as exc:
            logger.warning("fetch_url download failed: %s", exc)
            return SkillResult(
                success=False,
                content="",
                error="Nao consegui abrir essa pagina.",
            )

        text = ""
        try:
            import trafilatura

            text = trafilatura.extract(html, include_comments=False) or ""
        except Exception as exc:
            logger.debug("trafilatura failed: %s", exc)

        if not text.strip():
            # Fallback: strip tags lightly
            import re

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

        return SkillResult(
            success=True,
            content=f"Conteudo de {url}:\n{truncated}",
            metadata={"url": url, "chars": len(text)},
        )
