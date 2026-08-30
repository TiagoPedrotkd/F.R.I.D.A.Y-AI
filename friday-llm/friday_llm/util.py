"""Shared helpers for friday_llm."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

import yaml

_REPO_ROOT = Path(__file__).resolve().parents[2]


def repo_root() -> Path:
    return _REPO_ROOT


def resolve_path(path: str | Path) -> Path:
    p = Path(path)
    if p.is_absolute():
        return p
    return (_REPO_ROOT / p).resolve()


def load_yaml(path: str | Path) -> dict[str, Any]:
    with resolve_path(path).open(encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


_PII_PATTERNS = [
    re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I),
    re.compile(r"\b(?:\+351\s?)?(?:9\d{2}[\s-]?\d{3}[\s-]?\d{3})\b"),
    re.compile(r"\b(?:sk|api)[_-][a-zA-Z0-9]{16,}\b"),
]


def looks_like_pii(text: str) -> bool:
    return any(p.search(text) for p in _PII_PATTERNS)


def estimate_tokens(text: str) -> int:
    """Rough token estimate (chars/4) when no tokenizer loaded."""
    return max(1, len(text) // 4)


