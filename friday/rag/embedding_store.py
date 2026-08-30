"""Embedding-backed document store via Chroma (collection friday_docs)."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from friday_llm.rag.store import RagHit, format_rag_context

logger = logging.getLogger(__name__)

_COLLECTION = "friday_docs"


def _doc_url(meta: dict[str, Any]) -> str:
    return str(
        meta.get("url_or_document_id")
        or meta.get("url_or_path")
        or meta.get("document_id")
        or ""
    )


class EmbeddingRagStore:
    """Vector search over authorized project documents."""

    def __init__(
        self,
        index_dir: str | Path,
        *,
        embedding_model: str,
        corpus_path: str | Path | None = None,
    ) -> None:
        self.index_dir = Path(index_dir)
        self.embedding_model_name = embedding_model
        self.corpus_path = corpus_path
        self._client = None
        self._collection = None
        self._tokenizer = None
        self._model = None
        self._available = False
        self._init()

    def _init(self) -> None:
        chroma_path = self.index_dir / "chroma"
        if not chroma_path.is_dir():
            logger.warning("RAG Chroma index missing at %s", chroma_path)
            return
        try:
            import chromadb
            from chromadb.config import Settings as ChromaSettings

            self._client = chromadb.PersistentClient(
                path=str(chroma_path),
                settings=ChromaSettings(anonymized_telemetry=False),
            )
            self._collection = self._client.get_or_create_collection(
                name=_COLLECTION,
                metadata={"hnsw:space": "cosine"},
            )
            if self._collection.count() == 0:
                logger.warning("RAG collection %s is empty", _COLLECTION)
                return
            from friday_llm.rag.embeddings import encode_texts, load_embedding_model

            self._tokenizer, self._model = load_embedding_model(self.embedding_model_name)
            self._available = True
            logger.info(
                "EmbeddingRagStore ready (%s, %s docs)",
                self.embedding_model_name,
                self._collection.count(),
            )
        except Exception as exc:
            logger.warning("EmbeddingRagStore unavailable: %s", exc)

    @property
    def available(self) -> bool:
        return self._available

    @property
    def backend(self) -> str:
        return "embedding"

    def search(self, query: str, *, top_k: int = 3) -> list[RagHit]:
        if not self._available or not self._collection or not self._model or not self._tokenizer:
            return []
        q = (query or "").strip()
        if not q:
            return []
        from friday_llm.rag.embeddings import encode_texts

        embedding = encode_texts(self._tokenizer, self._model, [q])
        result = self._collection.query(
            query_embeddings=embedding,
            n_results=max(1, top_k),
            include=["documents", "metadatas", "distances"],
        )
        hits: list[RagHit] = []
        docs = (result.get("documents") or [[]])[0]
        metas = (result.get("metadatas") or [[]])[0]
        dists = (result.get("distances") or [[]])[0]
        for text, meta, dist in zip(docs, metas, dists):
            meta = meta or {}
            score = round(max(0.0, 1.0 - float(dist)), 4)
            hits.append(
                RagHit(
                    text=str(text or "")[:800],
                    title=str(meta.get("title") or ""),
                    source=str(meta.get("source") or ""),
                    url_or_document_id=_doc_url(meta),
                    captured_at_or_version=str(meta.get("captured_at_or_version") or ""),
                    language=str(meta.get("language") or ""),
                    score=score,
                )
            )
        return hits

    def format_context(self, hits: list[RagHit]) -> str:
        return format_rag_context(hits)
