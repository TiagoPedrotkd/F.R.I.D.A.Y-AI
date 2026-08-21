"""Summarize and explain_code skills (same logic as MCP templates)."""

from __future__ import annotations

import logging
from typing import Any

from friday.mcp_server.prompts import (
    build_explain_code_prompt,
    build_summarize_prompt,
    extractive_summary,
)
from friday.skills.base import SkillResult

logger = logging.getLogger(__name__)


def _llm(prompt: str, max_tokens: int = 512) -> str | None:
    try:
        from friday.config import get_settings
        from friday.llm.client import LlmClient

        client = LlmClient(get_settings())
        resp = client.create_completion(
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens,
            temperature=0.3,
        )
        return (resp.choices[0].message.content or "").strip() or None
    except Exception as exc:
        logger.warning("LLM for summarize/explain failed: %s", exc)
        return None


class SummarizeSkill:
    name = "summarize"
    description = (
        "Resume um texto longo. Preferivel quando pedirem resumo formal "
        "via ferramenta; o modelo tambem pode resumir directamente."
    )
    parameters: dict[str, Any] = {
        "type": "object",
        "properties": {
            "text": {"type": "string"},
            "style": {
                "type": "string",
                "description": "curto|executivo|topicos|simples|cinco_linhas",
                "default": "curto",
            },
        },
        "required": ["text"],
    }

    async def execute(self, arguments: dict[str, Any]) -> SkillResult:
        text = (arguments.get("text") or "").strip()
        if not text:
            return SkillResult(success=False, content="", error="Preciso do texto.")
        style = arguments.get("style") or "curto"
        out = _llm(build_summarize_prompt(text, style=style))
        if out:
            return SkillResult(success=True, content=out)
        return SkillResult(success=True, content=extractive_summary(text))


class ExplainCodeSkill:
    name = "explain_code"
    description = (
        "Explica codigo passo a passo. Usa quando pedirem explicar codigo "
        "de forma estruturada."
    )
    parameters: dict[str, Any] = {
        "type": "object",
        "properties": {
            "code": {"type": "string"},
            "language": {"type": "string", "default": "python"},
            "audience": {"type": "string", "default": "intermedio"},
        },
        "required": ["code"],
    }

    async def execute(self, arguments: dict[str, Any]) -> SkillResult:
        code = (arguments.get("code") or "").strip()
        if not code:
            return SkillResult(success=False, content="", error="Preciso do codigo.")
        prompt = build_explain_code_prompt(
            code,
            language=arguments.get("language") or "python",
            audience=arguments.get("audience") or "intermedio",
        )
        out = _llm(prompt, max_tokens=800)
        if out:
            return SkillResult(success=True, content=out)
        return SkillResult(
            success=False,
            content="",
            error="Nao consegui consultar essa informacao neste momento.",
        )
