"""Search lightweight knowledge graph over RAG corpus."""

from __future__ import annotations

from typing import Any

from friday.config import Settings, get_settings
from friday.rag.knowledge_graph import format_graph_block, search_graph
from friday.skills.base import SkillResult


class SearchKnowledgeGraphSkill:
    name = "search_knowledge_graph"
    description = (
        "Pesquisa relacoes entre componentes/entidades do projecto (grafo leve). "
        "Usa para arquitectura, dependencias, 'o que depende de X', interacoes."
    )
    parameters: dict[str, Any] = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Entidade ou pergunta sobre relacoes",
            },
            "top_k": {"type": "integer", "default": 8},
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
                error="Preciso de uma entidade ou pergunta sobre relacoes.",
            )
        top_k = max(1, min(int(arguments.get("top_k") or 8), 16))
        hits = search_graph(query, top_k=top_k, settings=self._settings)
        block = format_graph_block(hits)
        if not hits:
            return SkillResult(
                success=True,
                content=(
                    "Nao encontrei relacoes no grafo local para essa pergunta. "
                    "O grafo e heuristico (data/rag_graph); podes regenerar com "
                    "`python -m friday_llm.rag.build_kg`."
                ),
                metadata={"kind": "knowledge_graph", "count": 0, "results": []},
            )
        return SkillResult(
            success=True,
            content=block,
            metadata={
                "kind": "knowledge_graph",
                "query": query,
                "count": len(hits),
                "results": hits,
            },
        )
