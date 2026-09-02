"""Grounded web research: search_web → fetch top URLs → cite."""

from __future__ import annotations

from typing import Any

from friday.skills.base import SkillResult
from friday.skills.web.fetch_url import FetchUrlSkill
from friday.skills.web.search_web import SearchWebSkill


class ResearchWebSkill:
    name = "research_web"
    description = (
        "Pesquisa na Web e le as melhores paginas (search + fetch). "
        "Usa para factos actuais; a resposta deve citar as URLs devolvidas."
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
                "description": "Resultados de pesquisa (default 5)",
                "default": 5,
            },
            "fetch_top": {
                "type": "integer",
                "description": "Quantas paginas ler a seguir (1-3, default 2)",
                "default": 2,
            },
        },
        "required": ["query"],
    }

    def __init__(self, max_results_default: int = 5) -> None:
        self._search = SearchWebSkill(max_results_default=max_results_default)
        self._fetch = FetchUrlSkill()

    async def execute(self, arguments: dict[str, Any]) -> SkillResult:
        query = (arguments.get("query") or "").strip()
        if not query:
            return SkillResult(success=False, content="", error="Consulta vazia.")

        fetch_top = int(arguments.get("fetch_top") or 2)
        fetch_top = max(1, min(3, fetch_top))

        search = await self._search.execute(arguments)
        if not search.success:
            return search

        results = list((search.metadata or {}).get("results") or [])
        pages: list[dict[str, Any]] = []
        parts = [search.content, "", "## Paginas lidas"]

        for item in results[:fetch_top]:
            url = (item.get("url") or "").strip()
            if not url:
                continue
            page = await self._fetch.execute({"url": url})
            if not page.success:
                parts.append(f"- Falha ao ler {url}: {page.error}")
                continue
            excerpt = (page.content or "")[:1800]
            parts.append(excerpt)
            pages.append(
                {
                    "url": url,
                    "title": (page.metadata or {}).get("title") or item.get("title"),
                    "chars": (page.metadata or {}).get("chars"),
                }
            )

        if not pages:
            return SkillResult(
                success=True,
                content=(
                    search.content
                    + "\n\nNao consegui ler o conteudo das paginas. "
                    "Usa apenas os snippets acima e indica a incerteza."
                ),
                metadata={
                    "kind": "research",
                    "query": query,
                    "results": results,
                    "pages": [],
                    "grounding": {"used_web_tools": True, "score": 0.4},
                },
            )

        content = "\n\n".join(parts)
        urls = [p["url"] for p in pages if p.get("url")]
        return SkillResult(
            success=True,
            content=content,
            metadata={
                "kind": "research",
                "query": query,
                "results": results,
                "pages": pages,
                "url": urls[0] if urls else None,
                "_all_urls": urls + [r.get("url") for r in results if r.get("url")],
            },
        )
