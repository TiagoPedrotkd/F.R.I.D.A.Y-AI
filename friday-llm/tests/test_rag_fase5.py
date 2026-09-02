"""Tests for Fase 5 RAG (no embedding model download in CI)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from friday.config import Settings
from friday.llm.intent_router import match_skill_with_args
from friday.rag.doc_store import get_doc_store, reset_doc_store
from friday_llm.rag.index import build_rag_corpus, smoke_search
from friday_llm.rag.store import KeywordRagStore, format_rag_context, hits_to_ui_results
from friday_llm.util import load_yaml, resolve_path, write_jsonl


def test_keyword_store_url_or_document_id(tmp_path: Path):
    corpus = tmp_path / "chunks.jsonl"
    write_jsonl(
        corpus,
        [
            {
                "text": "A VLAN IoT deve estar isolada da rede principal.",
                "title": "Manual rede",
                "source": "repo_docs",
                "url_or_document_id": "docs/arquitectura/rede-vlan.md",
                "captured_at_or_version": "git",
                "language": "pt",
            }
        ],
    )
    store = KeywordRagStore(corpus)
    hits = store.search("VLAN IoT manual")
    assert len(hits) == 1
    assert hits[0].url_or_document_id == "docs/arquitectura/rede-vlan.md"


def test_format_rag_context_empty():
    assert "nenhum documento" in format_rag_context([]).casefold()


def test_hits_to_ui_results():
    from friday_llm.rag.store import RagHit

    hits = [
        RagHit(
            text="excerpt",
            title="Manual",
            source="repo",
            url_or_document_id="docs/x.md",
            captured_at_or_version="git",
            language="pt",
            score=0.8,
        )
    ]
    rows = hits_to_ui_results(hits)
    assert rows[0]["kind"] == "document"
    assert rows[0]["url"] == "docs/x.md"


def test_intent_router_rag():
    hit = match_skill_with_args("O que diz o manual interno sobre VLAN?")
    assert hit is not None
    assert hit[0] == "search_docs"
    assert hit[1]["query"]

    hit2 = match_skill_with_args("Na documentação do projeto, como funciona o RAG?")
    assert hit2 is not None
    assert hit2[0] == "search_docs"


def test_build_rag_corpus(tmp_path: Path):
    cfg = tmp_path / "fase5.yaml"
    seeds = tmp_path / "seeds.jsonl"
    write_jsonl(
        seeds,
        [
            {
                "document_id": "seed-1",
                "title": "Seed doc",
                "source": "seed",
                "url_or_path": "seed/1.md",
                "text": "LM Studio API em localhost porta 1234 para o agente F.R.I.D.A.Y.",
                "language": "pt",
            }
        ],
    )
    chunks = tmp_path / "chunks.jsonl"
    extracted = tmp_path / "extracted.jsonl"
    cfg.write_text(
        f"""
run_id: test-rag
paths:
  registry: {tmp_path.as_posix()}/catalog.jsonl
  extracted: {extracted.as_posix()}
  seeds: {seeds.as_posix()}
  chunks: {chunks.as_posix()}
  index_dir: {tmp_path.as_posix()}/index
repo_docs:
  globs:
    - docs/fase-0/*.md
rag:
  chunk_chars: 500
  chunk_overlap: 50
report_json: {tmp_path.as_posix()}/build.json
""",
        encoding="utf-8",
    )
    stats = build_rag_corpus(str(cfg))
    assert stats["chunks"] >= 1
    assert chunks.is_file()


def test_doc_store_keyword_fallback(tmp_path: Path):
    corpus = tmp_path / "chunks.jsonl"
    write_jsonl(
        corpus,
        [
            {
                "text": "Tres camadas: pesos CPT, SFT e RAG com tools.",
                "title": "Conhecimento",
                "source": "audit",
                "url_or_document_id": "friday-llm/reports/phase0_audit.md",
            }
        ],
    )
    reset_doc_store()
    settings = Settings(
        RAG_ENABLED=True,
        RAG_BACKEND="keyword",
        RAG_CORPUS_PATH=str(corpus),
        RAG_INDEX_DIR=str(tmp_path / "idx"),
    )
    store = get_doc_store(settings)
    assert store.backend == "keyword"
    hits = store.search("camadas RAG tools")
    assert len(hits) >= 1


def test_fase5_config_valid():
    cfg = load_yaml("friday-llm/configs/fase5_rag.yaml")
    assert cfg.get("run_id")
    assert resolve_path(cfg["paths"]["chunks"]).parent.exists()


def test_smoke_search_uses_available_backend():
    out = smoke_search("friday-llm/configs/fase5_rag.yaml", query="LM Studio")
    assert out["backend"] in ("keyword", "embedding")
    assert "LM Studio" in out["queries"]
    # When Chroma index exists, prefer embedding
    from pathlib import Path

    if Path("data/rag_chroma/chroma").is_dir():
        assert out["backend"] == "embedding"
        assert len(out["queries"]["LM Studio"]) >= 1


def test_normalize_embedding_model_short_id():
    from friday_llm.rag.embeddings import normalize_embedding_model

    assert (
        normalize_embedding_model("paraphrase-multilingual-MiniLM-L12-v2")
        == "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    )
