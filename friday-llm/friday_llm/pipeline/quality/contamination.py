"""Detect eval / holdout leakage into CPT corpus."""

from __future__ import annotations

import re
from typing import Any

from friday_llm.util import content_hash, read_jsonl, resolve_path


def _shingles(text: str, n: int = 5) -> set[str]:
    tokens = re.findall(r"\w+", text.casefold())
    if len(tokens) < n:
        return {" ".join(tokens)} if tokens else set()
    return {" ".join(tokens[i : i + n]) for i in range(len(tokens) - n + 1)}


def build_forbidden_corpus(
  eval_path: str | None = None,
  sft_holdout_path: str | None = None,
) -> tuple[set[str], list[set[str]]]:
    """Return content hashes and shingle sets from eval + SFT holdout."""
    hashes: set[str] = set()
    shingles: list[set[str]] = []

    if eval_path:
        for row in read_jsonl(resolve_path(eval_path)):
            inp = str(row.get("input") or "")
            rub = str(row.get("rubric") or "")
            blob = f"{inp} {rub}".strip()
            if blob:
                hashes.add(content_hash(blob))
                shingles.append(_shingles(blob))

    if sft_holdout_path:
        for row in read_jsonl(resolve_path(sft_holdout_path)):
            for msg in row.get("messages") or []:
                content = str(msg.get("content") or "")
                if content:
                    hashes.add(content_hash(content))
                    shingles.append(_shingles(content))

    return hashes, shingles


def is_eval_contaminated(
    text: str,
    *,
    forbidden_hashes: set[str],
    forbidden_shingles: list[set[str]],
    jaccard_threshold: float = 0.6,
) -> bool:
    h = content_hash(text)
    if h in forbidden_hashes:
        return True
    sh = _shingles(text)
    if not sh:
        return False
    for prev in forbidden_shingles:
        if not prev:
            continue
        inter = len(sh & prev)
        union = len(sh | prev)
        if union and inter / union >= jaccard_threshold:
            return True
    return False
