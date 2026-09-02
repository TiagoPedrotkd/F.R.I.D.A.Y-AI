"""Unified document RAG store with embedding + keyword fallback + hot-reload."""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Protocol

from friday.config import Settings, get_settings
from friday.rag.embedding_store import EmbeddingRagStore
from friday_llm.rag.store import KeywordRagStore, RagHit, format_rag_context

logger = logging.getLogger(__name__)

_shared: "DocRagStore | None" = None
_shared_fingerprint: str | None = None
_shared_checked_at: float = 0.0


class DocRagStore(Protocol):
    @property
    def available(self) -> bool: ...

    @property
    def backend(self) -> str: ...

    def search(self, query: str, *, top_k: int = 3) -> list[RagHit]: ...

    def format_context(self, hits: list[RagHit]) -> str: ...


class _KeywordAdapter:
    def __init__(self, store: KeywordRagStore) -> None:
        self._store = store

    @property
    def available(self) -> bool:
        return bool(self._store.docs)

    @property
    def backend(self) -> str:
        return "keyword"

    def search(self, query: str, *, top_k: int = 3) -> list[RagHit]:
        return self._store.search(query, top_k=top_k)

    def format_context(self, hits: list[RagHit]) -> str:
        return format_rag_context(hits)


def index_fingerprint(index_dir: Path, corpus_path: Path) -> str:
    """Version bump signal: index_meta mtime + chroma dir mtime + corpus mtime."""
    parts: list[str] = []
    meta = index_dir / "index_meta.json"
    chroma = index_dir / "chroma"
    for p in (meta, chroma, corpus_path):
        try:
            if p.exists():
                parts.append(f"{p}:{p.stat().st_mtime_ns}:{p.stat().st_size if p.is_file() else 0}")
            else:
                parts.append(f"{p}:missing")
        except OSError:
            parts.append(f"{p}:err")
    return "|".join(parts)


def _build_store(settings: Settings) -> DocRagStore:
    corpus = str(settings.rag_corpus_path)
    if not settings.rag_enabled:
        logger.info("RAG disabled (RAG_ENABLED=false)")
        return _KeywordAdapter(KeywordRagStore(corpus))

    backend = (settings.rag_backend or "embedding").casefold()
    if backend == "embedding":
        emb = EmbeddingRagStore(
            settings.rag_index_dir,
            embedding_model=settings.rag_embedding_model,
            corpus_path=corpus,
        )
        if emb.available:
            return emb
        logger.warning("Embedding RAG unavailable; falling back to keyword search")

    return _KeywordAdapter(KeywordRagStore(corpus))


def get_doc_store(settings: Settings | None = None) -> DocRagStore:
    """Return shared store; auto-reload when index_meta / corpus fingerprint changes."""
    global _shared, _shared_fingerprint, _shared_checked_at
    settings = settings or get_settings()
    now = time.monotonic()
    # Throttle filesystem checks
    if _shared is not None and (now - _shared_checked_at) < 2.0:
        return _shared
    _shared_checked_at = now
    fp = index_fingerprint(Path(settings.rag_index_dir), Path(settings.rag_corpus_path))
    if _shared is None or fp != _shared_fingerprint:
        if _shared is not None:
            logger.info("RAG store hot-reload (index fingerprint changed)")
        _shared = _build_store(settings)
        _shared_fingerprint = fp
    return _shared


def reset_doc_store() -> None:
    """Clear singleton (tests / admin reload)."""
    global _shared, _shared_fingerprint, _shared_checked_at
    _shared = None
    _shared_fingerprint = None
    _shared_checked_at = 0.0


def reload_doc_store(settings: Settings | None = None) -> DocRagStore:
    """Force rebuild of the shared store."""
    reset_doc_store()
    return get_doc_store(settings)
