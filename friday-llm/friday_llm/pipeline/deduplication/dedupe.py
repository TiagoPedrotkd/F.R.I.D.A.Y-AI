"""Exact and approximate deduplication (MinHash)."""

from __future__ import annotations

import hashlib
import random
from typing import Any, Iterable


def exact_dedupe(docs: Iterable[dict[str, Any]]) -> tuple[list[dict[str, Any]], int]:
    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    dropped = 0
    for doc in docs:
        h = doc.get("content_hash") or ""
        if not h or h in seen:
            dropped += 1
            continue
        seen.add(h)
        out.append(doc)
    return out, dropped


def _shingles(text: str, n: int = 5) -> set[str]:
    tokens = text.casefold().split()
    if len(tokens) < n:
        return {" ".join(tokens)} if tokens else set()
    return {" ".join(tokens[i : i + n]) for i in range(len(tokens) - n + 1)}


def _minhash_signature(shingles: set[str], num_perm: int, seeds: list[int]) -> tuple[int, ...]:
    if not shingles:
        return tuple(0 for _ in range(num_perm))
    sig = []
    for seed in seeds:
        m = 2**32 - 1
        best = m
        for sh in shingles:
            h = int(hashlib.md5(f"{seed}:{sh}".encode()).hexdigest(), 16) % m
            best = min(best, h)
        sig.append(best)
    return tuple(sig)


def _minhash_jaccard(a: tuple[int, ...], b: tuple[int, ...]) -> float:
    if not a or not b:
        return 0.0
    matches = sum(1 for x, y in zip(a, b) if x == y)
    return matches / len(a)


def minhash_dedupe(
    docs: list[dict[str, Any]],
    *,
    threshold: float = 0.85,
    num_perm: int = 128,
    seed: int = 42,
) -> tuple[list[dict[str, Any]], int]:
    """Near-dedupe via MinHash signatures."""
    rng = random.Random(seed)
    seeds = [rng.randint(0, 2**31 - 1) for _ in range(num_perm)]
    kept: list[dict[str, Any]] = []
    signatures: list[tuple[int, ...]] = []
    dropped = 0
    for doc in docs:
        sh = _shingles(doc.get("text") or "")
        sig = _minhash_signature(sh, num_perm, seeds)
        duplicate = any(_minhash_jaccard(sig, prev) >= threshold for prev in signatures)
        if duplicate:
            dropped += 1
            continue
        kept.append(doc)
        signatures.append(sig)
    return kept, dropped


def jaccard(a: set[str], b: set[str]) -> float:
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    inter = len(a & b)
    union = len(a | b)
    return inter / union if union else 0.0


def approx_dedupe(
    docs: list[dict[str, Any]],
    *,
    threshold: float = 0.85,
    method: str = "minhash",
    num_perm: int = 128,
    seed: int = 42,
) -> tuple[list[dict[str, Any]], int]:
    if method == "minhash":
        return minhash_dedupe(docs, threshold=threshold, num_perm=num_perm, seed=seed)
    kept: list[dict[str, Any]] = []
    shingle_sets: list[set[str]] = []
    dropped = 0
    for doc in docs:
        sh = _shingles(doc.get("text") or "")
        duplicate = any(jaccard(sh, prev) >= threshold for prev in shingle_sets)
        if duplicate:
            dropped += 1
            continue
        kept.append(doc)
        shingle_sets.append(sh)
    return kept, dropped
