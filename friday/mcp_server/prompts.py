"""MCP prompt templates (summarize, explain_code)."""

from __future__ import annotations

SUMMARIZE_PROMPT = """\
Resume o texto seguinte em portugues europeu.
Estilo: {style}
Regras: ideias principais apenas; sem inventar factos; claro e objectivo.

Texto:
{text}
"""

EXPLAIN_CODE_PROMPT = """\
Explica o codigo seguinte passo a passo, em portugues europeu.
Publico: {audience}
Inclui: o que faz, fluxo principal, pontos de atencao e um exemplo de uso se fizer sentido.
Nao reescrevas o codigo inteiro a menos que peçam — explica primeiro.

Codigo:
```{language}
{code}
```
"""

SUMMARIZE_STYLES = ("curto", "executivo", "topicos", "simples", "cinco_linhas")


def build_summarize_prompt(text: str, style: str = "curto") -> str:
    style_map = {
        "curto": "resumo curto (5-8 linhas)",
        "executivo": "resumo executivo (decisoes e impacto)",
        "topicos": "lista de topicos com bullets",
        "simples": "linguagem muito simples, como para iniciante",
        "cinco_linhas": "exactamente cinco linhas",
        "short": "resumo curto (5-8 linhas)",
        "bullets": "lista de topicos com bullets",
    }
    label = style_map.get(style.casefold(), style)
    return SUMMARIZE_PROMPT.format(style=label, text=text.strip())


def build_explain_code_prompt(
    code: str,
    language: str = "python",
    audience: str = "intermedio",
) -> str:
    return EXPLAIN_CODE_PROMPT.format(
        code=code.strip(),
        language=language or "text",
        audience=audience or "intermedio",
    )


def extractive_summary(text: str, max_sentences: int = 5) -> str:
    """Offline fallback when LLM is unavailable."""
    import re

    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    parts = [p.strip() for p in parts if p.strip()]
    if not parts:
        return "Nao encontrei texto para resumir."
    chosen = parts[:max_sentences]
    return " ".join(chosen)
