"""Persistent cross-session memory via ChromaDB (with in-memory fallback)."""

from __future__ import annotations

import logging
import uuid
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_DEFAULT_DIR = _REPO_ROOT / "data" / "chroma"
_shared = None


class ChromaStore:
    """Long-term memory. Uses Chroma if installed; else JSONL file fallback."""

    def __init__(self, persist_dir: str | Path | None = None) -> None:
        self._persist_dir = Path(persist_dir) if persist_dir else _DEFAULT_DIR
        self._collection = None
        self._client = None
        self._fallback: list[dict[str, Any]] = []
        self._fallback_path = self._persist_dir / "memory.jsonl"
        self._available = False
        self._backend = "none"
        self._init()

    def _init(self) -> None:
        self._persist_dir.mkdir(parents=True, exist_ok=True)
        try:
            import chromadb
            from chromadb.config import Settings as ChromaSettings

            self._client = chromadb.PersistentClient(
                path=str(self._persist_dir / "chroma"),
                settings=ChromaSettings(anonymized_telemetry=False),
            )
            self._collection = self._client.get_or_create_collection(
                name="friday_memory",
                metadata={"hnsw:space": "cosine"},
            )
            self._available = True
            self._backend = "chroma"
            logger.info("ChromaStore ready at %s", self._persist_dir)
            return
        except Exception as exc:
            logger.warning("Chroma unavailable (%s) — using JSONL fallback", exc)

        self._load_fallback()
        self._available = True
        self._backend = "jsonl"
        logger.info("ChromaStore JSONL fallback at %s", self._fallback_path)

    def _load_fallback(self) -> None:
        self._fallback = []
        if not self._fallback_path.is_file():
            return
        import json

        for line in self._fallback_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                self._fallback.append(json.loads(line))
            except json.JSONDecodeError:
                continue

    def _save_fallback_item(self, item: dict[str, Any]) -> None:
        import json

        with self._fallback_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(item, ensure_ascii=False) + "\n")

    @property
    def available(self) -> bool:
        return self._available

    @property
    def backend(self) -> str:
        return self._backend

    def add(self, text: str, metadata: dict[str, Any] | None = None) -> None:
        text = (text or "").strip()
        if not text or not self._available:
            return
        meta = {k: str(v) for k, v in (metadata or {}).items()}
        doc_id = str(uuid.uuid4())
        if self._collection is not None:
            self._collection.add(
                documents=[text],
                ids=[doc_id],
                metadatas=[meta or {"source": "friday"}],
            )
            return
        item = {"id": doc_id, "text": text, "metadata": meta}
        self._fallback.append(item)
        self._save_fallback_item(item)

    def query(self, text: str, n: int = 3) -> list[str]:
        text = (text or "").strip()
        if not text or not self._available:
            return []
        n = max(1, min(n, 10))
        if self._collection is not None:
            try:
                result = self._collection.query(query_texts=[text], n_results=n)
                docs = (result.get("documents") or [[]])[0]
                return [d for d in docs if d]
            except Exception as exc:
                logger.warning("Chroma query failed: %s", exc)
                return []

        # Simple keyword overlap fallback
        q_tokens = set(text.casefold().split())
        scored: list[tuple[int, str]] = []
        for item in self._fallback:
            body = item.get("text") or ""
            tokens = set(body.casefold().split())
            score = len(q_tokens & tokens)
            if score > 0:
                scored.append((score, body))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [s[1] for s in scored[:n]]

    def close(self) -> None:
        self._client = None
        self._collection = None


def get_shared_store(persist_dir: str | Path | None = None) -> ChromaStore:
    global _shared
    if _shared is None:
        _shared = ChromaStore(persist_dir=persist_dir)
    return _shared
