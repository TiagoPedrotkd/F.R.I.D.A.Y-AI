"""Unified document RAG store with embedding + keyword fallback."""

from __future__ import annotations

import logging
from typing import Protocol

from friday.config import Settings, get_settings
from friday.rag.embedding_store import EmbeddingRagStore
from friday_llm.rag.store import KeywordRagStore, RagHit, format_rag_context

logger = logging.getLogger(__name__)

_shared: "DocRagStore | None" = None


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
    global _shared
    if _shared is None:
        _shared = _build_store(settings or get_settings())
    return _shared


def reset_doc_store() -> None:
    """Clear singleton (tests)."""
    global _shared
    _shared = None
