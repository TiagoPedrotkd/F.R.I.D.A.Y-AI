"""Count words, characters, and lines."""

from __future__ import annotations

from typing import Any

from friday.skills.base import SkillResult


class WordCountSkill:
    name = "word_count"
    description = (
        "Conta palavras, caracteres e linhas de um texto. "
        "Usa quando o utilizador pedir contagem."
    )
    parameters: dict[str, Any] = {
        "type": "object",
        "properties": {
            "text": {
                "type": "string",
                "description": "Texto a analisar",
            }
        },
        "required": ["text"],
    }

    async def execute(self, arguments: dict[str, Any]) -> SkillResult:
        text = arguments.get("text") or ""
        if not str(text).strip():
            return SkillResult(
                success=False,
                content="",
                error="Preciso do texto para contar. Podes colar o texto?",
            )
        text = str(text)
        words = len(text.split())
        chars = len(text)
        chars_no_space = len(text.replace(" ", "").replace("\n", "").replace("\t", ""))
        lines = text.count("\n") + (1 if text else 0)
        content = (
            f"Palavras: {words}. Caracteres: {chars} "
            f"({chars_no_space} sem espacos). Linhas: {lines}."
        )
        return SkillResult(
            success=True,
            content=content,
            metadata={
                "words": words,
                "characters": chars,
                "characters_no_space": chars_no_space,
                "lines": lines,
            },
        )
