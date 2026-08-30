"""FastMCP server for F.R.I.D.A.Y — tools + prompts usable from Cursor / MCP clients."""

from __future__ import annotations

import json
import logging
from typing import Any

from friday.mcp_server.prompts import (
    build_explain_code_prompt,
    build_summarize_prompt,
    extractive_summary,
)

logger = logging.getLogger(__name__)


def _llm_complete(prompt: str, max_tokens: int = 512) -> str | None:
    """Best-effort call to local LM Studio; returns None on failure."""
    try:
        from friday.config import get_settings
        from friday.llm.client import LlmClient

        client = LlmClient(get_settings())
        client.ensure_model_ready()
        resp = client.create_completion(
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens,
            temperature=0.3,
        )
        return (resp.choices[0].message.content or "").strip() or None
    except Exception as exc:
        logger.warning("MCP LLM call failed: %s", exc)
        return None


def _register_prompts(mcp: Any) -> None:
    @mcp.prompt(name="summarize")
    def summarize_prompt(text: str, style: str = "curto") -> str:
        """Template MCP para resumir texto (o cliente LLM preenche/usa o prompt)."""
        return build_summarize_prompt(text, style=style)

    @mcp.prompt(name="explain_code")
    def explain_code_prompt(
        code: str,
        language: str = "python",
        audience: str = "intermedio",
    ) -> str:
        """Template MCP para explicar codigo passo a passo."""
        return build_explain_code_prompt(code, language=language, audience=audience)


def _register_llm_tools(mcp: Any) -> None:
    @mcp.tool(name="summarize")
    def summarize_tool(text: str, style: str = "curto") -> str:
        """Resume texto. Usa LLM local se disponivel; senao resumo extractivo."""
        if not (text or "").strip():
            return "Preciso do texto para resumir."
        out = _llm_complete(build_summarize_prompt(text, style=style))
        return out or extractive_summary(text)

    @mcp.tool(name="explain_code")
    def explain_code_tool(
        code: str,
        language: str = "python",
        audience: str = "intermedio",
    ) -> str:
        """Explica codigo passo a passo via LLM local (ou mensagem de falha)."""
        if not (code or "").strip():
            return "Preciso do codigo para explicar."
        out = _llm_complete(
            build_explain_code_prompt(code, language=language, audience=audience),
            max_tokens=800,
        )
        if out:
            return out
        return (
            "Nao consegui consultar o modelo local neste momento. "
            "Confirma que o LM Studio esta com o servidor activo."
        )


def _register_local_tools(mcp: Any) -> None:
    @mcp.tool(name="get_current_datetime")
    async def get_current_datetime(timezone: str = "Europe/Lisbon") -> str:
        """Hora e data actuais (nunca inventar)."""
        from friday.skills.local.datetime_skill import DateTimeSkill

        result = await DateTimeSkill().execute({"timezone": timezone})
        return result.content if result.success else (result.error or "Erro")

    @mcp.tool(name="get_system_info")
    async def get_system_info() -> str:
        """Informacoes do computador local."""
        from friday.skills.local.system_info import SystemInfoSkill

        result = await SystemInfoSkill().execute({})
        return result.content if result.success else (result.error or "Erro")

    @mcp.tool(name="remember")
    def remember(text: str, label: str = "") -> str:
        """Guarda um facto na memoria longa (Chroma)."""
        from friday.memory.chroma_store import get_shared_store

        store = get_shared_store()
        if not store.available:
            return "Memoria longa indisponivel (Chroma nao inicializado)."
        store.add(text, metadata={"label": label} if label else None)
        return "Guardei essa informacao na memoria."

    @mcp.tool(name="recall")
    def recall(query: str, n: int = 3) -> str:
        """Recupera factos guardados relacionados com a pergunta."""
        from friday.memory.chroma_store import get_shared_store

        store = get_shared_store()
        if not store.available:
            return "Memoria longa indisponivel."
        hits = store.query(query, n=n)
        if not hits:
            return "Nao encontrei nada relacionado na memoria."
        return "Memoria:\n" + "\n".join(f"- {h}" for h in hits)

    @mcp.tool(name="search_docs")
    async def search_docs(query: str, top_k: int = 3) -> str:
        """Pesquisa documentos internos autorizados (RAG). Cita fontes; admite se vazio."""
        from friday.config import get_settings
        from friday.skills.rag.search_docs import SearchDocsSkill

        result = await SearchDocsSkill(settings=get_settings()).execute(
            {"query": query, "top_k": top_k}
        )
        return result.content if result.success else (result.error or "Erro na pesquisa.")

    @mcp.resource("friday://capabilities")
    def capabilities() -> str:
        return json.dumps(
            {
                "prompts": ["summarize", "explain_code"],
                "tools": [
                    "summarize",
                    "explain_code",
                    "get_current_datetime",
                    "get_system_info",
                    "remember",
                    "recall",
                    "search_docs",
                ],
            },
            indent=2,
        )


def create_mcp_server():
    """Build and return an MCPServer instance (MCP SDK 2.x)."""
    from mcp.server.mcpserver import MCPServer

    mcp = MCPServer(
        name="friday",
        instructions=(
            "F.R.I.D.A.Y MCP server: summarize, explain_code, and local assistant tools. "
            "Prefer these tools for factual/local actions; do not invent time or news."
        ),
    )
    _register_prompts(mcp)
    _register_llm_tools(mcp)
    _register_local_tools(mcp)
    return mcp


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    mcp = create_mcp_server()
    if hasattr(mcp, "run") and callable(mcp.run):
        try:
            mcp.run(transport="stdio")
            return
        except TypeError:
            pass
    import asyncio

    asyncio.run(mcp.run_stdio_async())


if __name__ == "__main__":
    main()
