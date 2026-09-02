"""Build RAG corpus and embed into Chroma (friday_docs collection)."""

from __future__ import annotations

import argparse
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from friday_llm.pipeline.build_datasets.rag_chunker import chunk_documents
from friday_llm.pipeline.ingest.repo_docs import ingest_repo_markdown, write_extracted_batch
from friday_llm.pipeline.registry.catalog import update_catalog_from_build
from friday_llm.util import content_hash, load_yaml, read_jsonl, resolve_path, write_jsonl

logger = logging.getLogger(__name__)

_COLLECTION = "friday_docs"


def _normalize_seed_doc(row: dict[str, Any]) -> dict[str, Any]:
    text = str(row.get("text") or "").strip()
    doc_id = str(row.get("document_id") or content_hash(text)[:16])
    url = str(row.get("url_or_document_id") or row.get("url_or_path") or doc_id)
    return {
        "document_id": doc_id,
        "title": str(row.get("title") or doc_id),
        "source": str(row.get("source") or "seed"),
        "url_or_path": url,
        "url_or_document_id": url,
        "captured_at_or_version": str(row.get("captured_at_or_version") or "seed"),
        "language": str(row.get("language") or "pt"),
        "permissions": str(row.get("permissions") or "project_docs"),
        "license": str(row.get("license") or "Apache-2.0"),
        "text": text,
        "content_hash": row.get("content_hash") or content_hash(text),
    }


def build_rag_corpus(config_path: str) -> dict[str, Any]:
    cfg = load_yaml(config_path)
    paths = cfg.get("paths") or {}
    repo_cfg = cfg.get("repo_docs") or {}
    rag_cfg = cfg.get("rag") or {}

    globs = list(repo_cfg.get("globs") or ["docs/**/*.md"])
    excluded = list(cfg.get("excluded_paths") or [])
    license_name = str(repo_cfg.get("license") or "Apache-2.0")
    language = str(repo_cfg.get("language") or "pt")

    repo_docs = list(
        ingest_repo_markdown(
            globs,
            license_name=license_name,
            language=language,
            excluded_paths=excluded,
        )
    )
    extracted_path = resolve_path(paths.get("extracted") or "friday-llm/data/extracted/repo_docs.jsonl")
    write_extracted_batch(repo_docs, extracted_path)

    seeds_path = resolve_path(paths.get("seeds") or "friday-llm/data/rag/friday_docs_seed.jsonl")
    seed_docs = [_normalize_seed_doc(r) for r in read_jsonl(seeds_path)] if seeds_path.is_file() else []

    merged: list[dict[str, Any]] = []
    seen_hashes: set[str] = set()
    for doc in repo_docs + seed_docs:
        h = str(doc.get("content_hash") or content_hash(str(doc.get("text") or "")))
        if h in seen_hashes:
            continue
        seen_hashes.add(h)
        merged.append(doc)

    chunks = chunk_documents(
        merged,
        chunk_chars=int(rag_cfg.get("chunk_chars") or 2000),
        chunk_overlap=int(rag_cfg.get("chunk_overlap") or 200),
    )
    chunks_path = resolve_path(paths.get("chunks") or "friday-llm/data/rag/chunks.jsonl")
    write_jsonl(chunks_path, chunks)

    catalog_path = paths.get("registry") or "friday-llm/data/registry/datasets.jsonl"
    update_catalog_from_build(
        catalog_path,
        rag_path=chunks_path,
    )

    stats = {
        "run_id": cfg.get("run_id"),
        "built_at": datetime.now(timezone.utc).isoformat(),
        "repo_documents": len(repo_docs),
        "seed_documents": len(seed_docs),
        "unique_documents": len(merged),
        "chunks": len(chunks),
        "chunks_path": str(chunks_path),
        "extracted_path": str(extracted_path),
        "dataset_id": rag_cfg.get("dataset_id") or "friday-rag-docs-v1",
    }
    report_path = resolve_path(cfg.get("report_json") or "friday-llm/reports/phase5_rag_build.json")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(stats, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info("RAG corpus: %s chunks → %s", len(chunks), chunks_path)
    return stats


def index_rag_corpus(config_path: str) -> dict[str, Any]:
    cfg = load_yaml(config_path)
    paths = cfg.get("paths") or {}
    chunks_path = resolve_path(paths.get("chunks") or "friday-llm/data/rag/chunks.jsonl")
    index_dir = resolve_path(paths.get("index_dir") or "data/rag_chroma")
    embedding_model = str(
        cfg.get("embedding_model") or "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    )

    rows = read_jsonl(chunks_path)
    if not rows:
        raise FileNotFoundError(f"No RAG chunks at {chunks_path}. Run build first.")

    index_dir.mkdir(parents=True, exist_ok=True)
    chroma_path = index_dir / "chroma"
    chroma_path.mkdir(parents=True, exist_ok=True)

    import chromadb
    from chromadb.config import Settings as ChromaSettings

    from friday_llm.rag.embeddings import encode_texts, load_embedding_model

    client = chromadb.PersistentClient(
        path=str(chroma_path),
        settings=ChromaSettings(anonymized_telemetry=False),
    )
    try:
        client.delete_collection(_COLLECTION)
    except Exception:
        pass
    collection = client.get_or_create_collection(
        name=_COLLECTION,
        metadata={"hnsw:space": "cosine"},
    )

    tokenizer, model = load_embedding_model(embedding_model)
    ids: list[str] = []
    documents: list[str] = []
    metadatas: list[dict[str, str]] = []
    for i, row in enumerate(rows):
        text = str(row.get("text") or "").strip()
        if not text:
            continue
        chunk_id = str(row.get("content_hash") or content_hash(text))[:32] + f"-{i}"
        url = str(
            row.get("url_or_document_id")
            or row.get("url_or_path")
            or row.get("document_id")
            or ""
        )
        ids.append(chunk_id)
        documents.append(text)
        metadatas.append(
            {
                "title": str(row.get("title") or "")[:200],
                "source": str(row.get("source") or "")[:120],
                "url_or_document_id": url[:300],
                "captured_at_or_version": str(row.get("captured_at_or_version") or "")[:80],
                "language": str(row.get("language") or "pt")[:16],
                "content_hash": str(row.get("content_hash") or content_hash(text))[:64],
                "permissions": str(row.get("permissions") or "project_docs")[:40],
            }
        )

    batch_size = 32
    for start in range(0, len(documents), batch_size):
        end = start + batch_size
        batch_docs = documents[start:end]
        embeddings = encode_texts(tokenizer, model, batch_docs)
        collection.add(
            ids=ids[start:end],
            documents=batch_docs,
            metadatas=metadatas[start:end],
            embeddings=embeddings,
        )

    stats = {
        "indexed_at": datetime.now(timezone.utc).isoformat(),
        "embedding_model": embedding_model,
        "index_dir": str(index_dir),
        "collection": _COLLECTION,
        "chunk_count": collection.count(),
        "chunks_path": str(chunks_path),
    }
    meta_path = index_dir / "index_meta.json"
    meta_path.write_text(json.dumps(stats, indent=2), encoding="utf-8")
    logger.info("Indexed %s chunks into %s", collection.count(), chroma_path)
    return stats


def smoke_search(config_path: str, query: str | None = None) -> dict[str, Any]:
    from friday.config import Settings
    from friday.rag.doc_store import reset_doc_store, get_doc_store

    cfg = load_yaml(config_path)
    paths = cfg.get("paths") or {}
    chunks = str(resolve_path(paths.get("chunks") or "friday-llm/data/rag/chunks.jsonl"))
    index_dir = resolve_path(paths.get("index_dir") or "data/rag_chroma")
    embedding_model = str(
        cfg.get("embedding_model")
        or "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    )

    # Prefer embedding when Chroma index exists; fall back to keyword.
    chroma_ok = (index_dir / "chroma").is_dir()
    settings = Settings(
        RAG_ENABLED=True,
        RAG_BACKEND="embedding" if chroma_ok else "keyword",
        RAG_CORPUS_PATH=chunks,
        RAG_INDEX_DIR=str(index_dir),
        RAG_EMBEDDING_MODEL=embedding_model,
    )
    reset_doc_store()
    store = get_doc_store(settings)

    queries = [query] if query else list(cfg.get("smoke_queries") or ["LM Studio"])
    results: dict[str, Any] = {"backend": store.backend, "queries": {}}
    for q in queries:
        hits = store.search(q, top_k=3)
        results["queries"][q] = [h.to_dict() for h in hits]
    return results


def main(argv: list[str] | None = None) -> None:
    logging.basicConfig(level=logging.INFO)
    p = argparse.ArgumentParser(description="Build and index RAG corpus")
    p.add_argument("--config", default="friday-llm/configs/fase5_rag.yaml")
    p.add_argument(
        "--only",
        choices=["build", "index", "smoke", "gate"],
        default=None,
    )
    p.add_argument("--query", default=None)
    args = p.parse_args(argv)

    if args.only == "build" or args.only is None:
        build_rag_corpus(args.config)
    if args.only == "index" or args.only is None:
        index_rag_corpus(args.config)
    if args.only == "smoke":
        out = smoke_search(args.config, query=args.query)
        print(json.dumps(out, ensure_ascii=False, indent=2))
    if args.only == "gate" or args.only is None:
        from friday_llm.rag.quality_gate import run_quality_gate

        gate = run_quality_gate(args.config)
        print(json.dumps(gate, ensure_ascii=False, indent=2))
        if not gate.get("passed", False):
            raise SystemExit(2)

if __name__ == "__main__":
    main()
