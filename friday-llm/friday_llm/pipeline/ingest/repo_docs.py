"""Ingest authorized markdown from the repository for RAG (not CPT)."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from friday_llm.util import content_hash, repo_root, resolve_path

logger = logging.getLogger(__name__)

_DEFAULT_EXCLUDE_PARTS = (
    "data/chroma",
    "data/news_cache",
    "apps/web/src/demo",
    "/tests/",
    "friday-llm/data/evaluation",
    "friday-llm/tests",
    "node_modules",
    ".venv",
)


def _is_excluded(path: Path, excluded: list[str]) -> bool:
    posix = path.as_posix().casefold()
    for part in excluded:
        if part.casefold() in posix:
            return True
    return False


def ingest_repo_markdown(
    globs: list[str],
    *,
    license_name: str = "Apache-2.0",
    language: str = "pt",
    excluded_paths: list[str] | None = None,
) -> Iterator[dict[str, Any]]:
    """Yield document dicts from repo markdown files."""
    root = repo_root()
    excluded = list(_DEFAULT_EXCLUDE_PARTS) + (excluded_paths or [])
    seen: set[str] = set()

    for pattern in globs:
        for path in sorted(root.glob(pattern)):
            if not path.is_file() or path.suffix.lower() not in (".md", ".markdown"):
                continue
            rel = path.relative_to(root).as_posix()
            if rel in seen or _is_excluded(path, excluded):
                continue
            seen.add(rel)
            try:
                text = path.read_text(encoding="utf-8")
            except OSError as exc:
                logger.warning("Skip %s: %s", rel, exc)
                continue
            text = text.strip()
            if len(text) < 50:
                continue
            title = path.stem.replace("-", " ").replace("_", " ")
            yield {
                "document_id": content_hash(rel)[:16],
                "text": text,
                "title": title,
                "source": "repo_docs",
                "url": "",
                "url_or_path": rel,
                "crawl": "repo",
                "captured_at": datetime.now(timezone.utc).isoformat(),
                "captured_at_or_version": "git",
                "language": language,
                "license": license_name,
                "permissions": "project_docs",
                "content_hash": content_hash(text),
                "metadata": {"ingested_from": rel},
            }


def write_extracted_batch(docs: list[dict[str, Any]], out_path: Path) -> Path:
    from friday_llm.util import write_jsonl

    out_path = resolve_path(out_path)
    write_jsonl(out_path, docs)
    return out_path
