"""Search authorized local project documents (RAG)."""

from __future__ import annotations

import logging
from typing import Any

from friday.config import Settings, get_settings
from friday.rag.doc_store import get_doc_store
from friday.skills.base import SkillResult
from friday_llm.rag.store import hits_to_ui_results

logger = logging.getLogger(__name__)


class SearchDocsSkill:
    name = "search_docs"
    description = (
        "Pesquisa documentos internos autorizados do projecto (manuais, docs do repo). "
        "Usa para perguntas sobre documentacao interna, manuais ou ficheiros do projecto. "
        "Nao inventes conteudo; cita titulo e fonte. Se nao houver resultados, admite."
    )
    parameters: dict[str, Any] = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Pergunta ou termos de pesquisa nos documentos",
            },
            "top_k": {
                "type": "integer",
                "description": "Numero maximo de excertos",
                "default": 3,
            },
        },
        "required": ["query"],
    }

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()

    async def execute(self, arguments: dict[str, Any]) -> SkillResult:
        query = (arguments.get("query") or "").strip()
        if not query:
            return SkillResult(
                success=False,
                content="",
                error="Preciso de uma pergunta ou termos para pesquisar nos documentos.",
            )

        top_k = int(arguments.get("top_k") or self._settings.rag_top_k)
        top_k = max(1, min(top_k, 8))

        if not self._settings.rag_enabled:
            return SkillResult(
                success=True,
                content=(
                    "Nao recuperei nenhum documento local — a pesquisa documental "
                    "esta desactivada neste ambiente."
                ),
                metadata={"kind": "document", "count": 0, "results": []},
            )

        store = get_doc_store(self._settings)
        hits = store.search(query, top_k=top_k)
        context = store.format_context(hits)
        structured = hits_to_ui_results(hits)

        if not hits:
            return SkillResult(
                success=True,
                content=(
                    "Nao encontrei documentos relevantes para essa pergunta nos ficheiros "
                    "autorizados. Nao invento conteudo de manuais internos."
                ),
                metadata={
                    "kind": "document",
                    "query": query,
                    "count": 0,
                    "results": [],
                    "rag_backend": store.backend,
                },
            )

        titles = ", ".join(h.title or h.url_or_document_id for h in hits[:3] if h.title or h.url_or_document_id)
        spoken = f"Encontrei {len(hits)} excerto(s)"
        if titles:
            spoken += f" em: {titles}."
        spoken += f"\n\n{context}"

        return SkillResult(
            success=True,
            content=spoken,
            metadata={
                "kind": "document",
                "query": query,
                "count": len(hits),
                "results": structured,
                "rag_backend": store.backend,
            },
        )
