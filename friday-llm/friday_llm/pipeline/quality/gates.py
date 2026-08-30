"""Quality gates placeholder — extend with toxicity classifiers later."""

from __future__ import annotations

from typing import Any


def basic_quality_ok(doc: dict[str, Any]) -> bool:
    text = doc.get("text") or ""
    if not text.strip():
        return False
    # Reject mostly non-alphanumeric garbage
    letters = sum(c.isalpha() for c in text)
    return letters / max(1, len(text)) > 0.4
