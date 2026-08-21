"""Cross-session memory skills."""

from __future__ import annotations

from typing import Any

from friday.memory.chroma_store import get_shared_store
from friday.skills.base import SkillResult


class RememberSkill:
    name = "remember"
    description = (
        "Guarda um facto ou conclusao na memoria longa entre sessoes. "
        "Usa quando o utilizador disser 'guarda', 'lembra-te', 'memoriza'."
    )
    parameters: dict[str, Any] = {
        "type": "object",
        "properties": {
            "text": {
                "type": "string",
                "description": "Texto a guardar",
            },
            "label": {
                "type": "string",
                "description": "Etiqueta opcional",
            },
        },
        "required": ["text"],
    }

    async def execute(self, arguments: dict[str, Any]) -> SkillResult:
        text = (arguments.get("text") or "").strip()
        if not text:
            return SkillResult(
                success=False,
                content="",
                error="Preciso do texto a guardar.",
            )
        store = get_shared_store()
        if not store.available:
            return SkillResult(
                success=False,
                content="",
                error="Memoria longa indisponivel neste momento.",
            )
        label = (arguments.get("label") or "").strip()
        store.add(text, metadata={"label": label} if label else None)
        return SkillResult(
            success=True,
            content="Guardei isso na memoria para sessoes futuras.",
            metadata={"backend": store.backend},
        )


class RecallSkill:
    name = "recall"
    description = (
        "Recupera informacao guardada. Usa para 'lembras-te', "
        "'o que guardamos', 'volta ao assunto guardado'."
    )
    parameters: dict[str, Any] = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "O que procurar na memoria",
            },
            "n": {
                "type": "integer",
                "default": 3,
            },
        },
        "required": ["query"],
    }

    async def execute(self, arguments: dict[str, Any]) -> SkillResult:
        query = (arguments.get("query") or "").strip()
        if not query:
            return SkillResult(
                success=False,
                content="",
                error="Preciso de saber o que procurar na memoria.",
            )
        store = get_shared_store()
        if not store.available:
            return SkillResult(
                success=False,
                content="",
                error="Memoria longa indisponivel neste momento.",
            )
        n = int(arguments.get("n") or 3)
        hits = store.query(query, n=n)
        if not hits:
            return SkillResult(
                success=False,
                content="",
                error="Nao encontrei resultados suficientes na memoria.",
            )
        body = "Lembro-me disto:\n" + "\n".join(f"- {h}" for h in hits)
        return SkillResult(success=True, content=body, metadata={"count": len(hits)})
