"""Token-budget helpers for chat context."""

from __future__ import annotations

from typing import Any


def estimate_tokens(text: str) -> int:
    """Rough char/4 estimate — good enough for budgeting without a tokenizer."""
    if not text:
        return 0
    return max(1, (len(text) + 3) // 4)


def message_tokens(msg: dict[str, Any]) -> int:
    content = msg.get("content")
    if isinstance(content, str):
        return estimate_tokens(content) + 4
    if isinstance(content, list):
        total = 4
        for part in content:
            if not isinstance(part, dict):
                if isinstance(part, str):
                    total += estimate_tokens(part)
                continue
            if isinstance(part.get("text"), str):
                total += estimate_tokens(part["text"])
            elif part.get("type") == "image_url" or part.get("image_url"):
                # Rough multimodal budget (low-detail image ≈ 85–765 tokens)
                total += 400
            elif isinstance(part, str):
                total += estimate_tokens(part)
        return total
    return 4


def trim_messages_to_budget(
    messages: list[dict[str, Any]],
    *,
    max_tokens: int,
    keep_system: bool = True,
) -> list[dict[str, Any]]:
    """
    Keep system messages (optional) and the newest messages that fit max_tokens.
    """
    if max_tokens <= 0 or not messages:
        return list(messages)

    systems: list[dict[str, Any]] = []
    rest: list[dict[str, Any]] = []
    for m in messages:
        if keep_system and m.get("role") == "system":
            systems.append(m)
        else:
            rest.append(m)

    budget = max_tokens - sum(message_tokens(m) for m in systems)
    if budget <= 0:
        return systems[-1:] if systems else []

    kept: list[dict[str, Any]] = []
    used = 0
    for m in reversed(rest):
        cost = message_tokens(m)
        if used + cost > budget and kept:
            break
        kept.append(m)
        used += cost
    kept.reverse()
    return systems + kept


def format_summary_message(summary: str) -> dict[str, str]:
    return {
        "role": "system",
        "content": f"[Resumo da conversa anterior]\n{summary.strip()}",
    }
