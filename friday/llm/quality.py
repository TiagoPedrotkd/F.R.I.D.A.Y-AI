"""Lightweight post-response quality heuristics (Phase 4)."""

from __future__ import annotations

import re
from typing import Any


def score_response(
    response: str,
    *,
    user_text: str = "",
    has_personal_context: bool = False,
    used_tools: bool = False,
    routing_primary: str = "general",
) -> dict[str, float]:
    text = (response or "").strip()
    low = text.casefold()
    scores = {
        "factuality": 0.75,
        "personalization": 0.55,
        "actionability": 0.6,
        "safety": 0.85,
        "confidence": 0.7,
    }
    if not text:
        return {k: 0.2 for k in scores}

    if has_personal_context and any(
        w in low for w in ("senhor", "perfil", "habito", "objetivo", "prefer")
    ):
        scores["personalization"] = 0.85
    elif has_personal_context:
        scores["personalization"] = 0.7

    if used_tools or "segundo" in low or "fonte" in low or "http" in low:
        scores["factuality"] = 0.88

    if re.search(r"\b(podes|deve|hoje|amanha|passos?|plano)\b", low):
        scores["actionability"] = 0.8

    if any(w in low for w in ("nao tenho a certeza", "incerto", "nao sei", "faltam dados")):
        scores["confidence"] = 0.55
        scores["factuality"] = min(scores["factuality"], 0.8)

    if any(w in low for w in ("garanto", "100%", "sem risco", "definitivamente seguro")):
        scores["safety"] = 0.5
        scores["confidence"] = 0.45

    if routing_primary != "general" and routing_primary.replace("_", " ") in low:
        scores["personalization"] = min(1.0, scores["personalization"] + 0.05)

    # length sanity
    if len(text) < 20:
        scores["actionability"] = min(scores["actionability"], 0.5)

    return {k: round(float(v), 2) for k, v in scores.items()}


def needs_low_confidence_hedge(scores: dict[str, float], threshold: float = 0.7) -> bool:
    return any(v < threshold for v in scores.values())


def format_hedge(scores: dict[str, float]) -> str:
    weak = [k for k, v in scores.items() if v < 0.7]
    return (
        f" [Baixa confianca em: {', '.join(weak)}. "
        f"Scores={scores}. Confirma ou pede mais dados se precisares.]"
    )


def update_domain_stats(
    path: Any,
    domain: str,
    rating: str,
) -> dict[str, Any]:
    """Append-friendly domain approval stats (file-backed)."""
    import json
    from pathlib import Path

    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    data: dict[str, Any] = {}
    if p.is_file():
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            data = {}
    bucket = data.setdefault(domain or "general", {"up": 0, "down": 0, "meh": 0})
    key = "up" if rating == "up" else "down" if rating == "down" else "meh"
    bucket[key] = int(bucket.get(key) or 0) + 1
    total = bucket["up"] + bucket["down"] + bucket["meh"]
    bucket["approval_rate"] = round(bucket["up"] / total, 3) if total else 0.0
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return data
