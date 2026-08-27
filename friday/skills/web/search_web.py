"""Web search via DuckDuckGo (structured results + sources)."""

from __future__ import annotations

import logging
from typing import Any
from urllib.parse import urlparse

from friday.skills.base import SkillResult

logger = logging.getLogger(__name__)


def _hostname(url: str) -> str:
    try:
        return (urlparse(url).hostname or "").removeprefix("www.")
    except Exception:
        return ""


class SearchWebSkill:
    name = "search_web"
    description = (
        "Pesquisa na Internet. Usa para factos actualizados ou quando pedirem "
        "para procurar/search. Nao inventes resultados."
    )
    parameters: dict[str, Any] = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Consulta de pesquisa",
            },
            "max_results": {
                "type": "integer",
                "description": "Numero maximo de resultados",
                "default": 5,
            },
        },
        "required": ["query"],
    }

    def __init__(self, max_results_default: int = 5) -> None:
        self._max_default = max_results_default

    async def execute(self, arguments: dict[str, Any]) -> SkillResult:
        query = (arguments.get("query") or "").strip()
        if not query:
            return SkillResult(
                success=False,
                content="",
                error="Preciso de um termo de pesquisa.",
            )
        max_results = int(arguments.get("max_results") or self._max_default)
        max_results = max(1, min(max_results, 10))

        try:
            from ddgs import DDGS
        except ImportError:
            try:
                from duckduckgo_search import DDGS  # type: ignore
            except ImportError:
                return SkillResult(
                    success=False,
                    content="",
                    error="Nao consegui consultar essa informacao neste momento. "
                    "(pacote de pesquisa em falta)",
                )

        try:
            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=max_results))
        except Exception as exc:
            logger.warning("search_web failed: %s", exc)
            return SkillResult(
                success=False,
                content="",
                error="Nao consegui consultar essa informacao neste momento. "
                "A ferramenta de pesquisa nao esta a responder.",
            )

        if not results:
            return SkillResult(
                success=False,
                content="",
                error="Nao encontrei resultados suficientes.",
            )

        structured: list[dict[str, str]] = []
        lines: list[str] = []
        for i, item in enumerate(results[:max_results], 1):
            title = (item.get("title") or item.get("href") or "Sem titulo").strip()
            snippet = (item.get("body") or item.get("snippet") or "").strip()
            href = (item.get("href") or item.get("link") or "").strip()
            source = _hostname(href)
            date = str(item.get("date") or item.get("published") or "").strip()
            entry = {
                "title": title,
                "url": href,
                "snippet": snippet[:240],
                "source": source,
            }
            if date:
                entry["date"] = date
            structured.append(entry)
            src_bit = f" [{source}]" if source else ""
            lines.append(f"{i}. {title}{src_bit} — {snippet[:160]} ({href})")

        sources = ", ".join(
            dict.fromkeys(e["source"] for e in structured if e.get("source"))
        )
        content = f"Resultados para '{query}':\n" + "\n".join(lines)
        if sources:
            content += f"\nFontes: {sources}."

        return SkillResult(
            success=True,
            content=content,
            metadata={
                "query": query,
                "count": len(structured),
                "results": structured,
            },
        )
