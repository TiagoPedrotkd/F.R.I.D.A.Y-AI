"""Reply confidence / hallucination heuristics beyond URL grounding."""

from __future__ import annotations

import re
from typing import Any

_HEDGE = (
    r"\b(talvez|possivelmente|nao tenho a certeza|não tenho a certeza|"
    r"parece[- ]me|acho que|maybe|perhaps|i think|not sure|might be)\b"
)
_FABRICATE = (
    r"\b(segundo a minha base de conhecimento interna sem fontes|"
    r"com certeza absoluta que|"
    r"as minhas fontes internas confirmam)\b"
)


def confidence_report(
    reply_text: str,
    *,
    grounding: dict[str, Any] | None = None,
    tool_rounds: int = 0,
) -> dict[str, Any]:
    text = reply_text or ""
    lowered = text.casefold()
    g = grounding or {}
    g_score = float(g.get("score") or 0.0)
    hedges = len(re.findall(_HEDGE, lowered, flags=re.I))
    fabricate = bool(re.search(_FABRICATE, lowered, flags=re.I))

    # Base: prefer grounded tool answers; conversational replies get mid confidence
    if g.get("grounded"):
        base = 0.85 + 0.1 * min(1.0, g_score)
    elif tool_rounds > 0:
        base = 0.55 + 0.2 * g_score
    elif g.get("refused"):
        base = 0.9  # honest refusal is high confidence in honesty
    else:
        base = 0.45

    penalty = min(0.35, 0.05 * hedges) + (0.25 if fabricate else 0.0)
    score = max(0.05, min(0.99, base - penalty))

    flags: list[str] = []
    if hedges:
        flags.append("hedging")
    if fabricate:
        flags.append("overclaim")
    if g.get("used_web_tools") and not g.get("grounded"):
        flags.append("weak_citation")
    if g.get("refused"):
        flags.append("source_refusal")
    if g.get("inventing"):
        flags.append("inventing")
        score = min(score, 0.35)

    return {
        "score": round(score, 3),
        "level": "high" if score >= 0.75 else "medium" if score >= 0.45 else "low",
        "flags": flags,
        "grounding_score": g.get("score"),
        "hallucination_risk": (
            "high"
            if score < 0.4 or fabricate or g.get("inventing")
            else "low"
            if score >= 0.75
            else "medium"
        ),
    }
