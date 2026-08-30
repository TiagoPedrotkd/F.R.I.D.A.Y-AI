"""Document RAG runtime (separate from personal Chroma memory)."""

from friday.rag.doc_store import get_doc_store, reset_doc_store

__all__ = ["get_doc_store", "reset_doc_store"]
