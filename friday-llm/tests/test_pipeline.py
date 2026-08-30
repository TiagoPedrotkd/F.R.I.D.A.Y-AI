"""Unit tests for friday_llm pipeline (no HF download, no GPU train)."""

from __future__ import annotations

import json
from pathlib import Path

from friday_llm.pipeline.build_datasets.rag_chunker import chunk_document
from friday_llm.pipeline.build_datasets.sft_builder import build_sft_dataset, validate_sft_tools
from friday_llm.pipeline.cleaning.clean import CleanStats, clean_document, normalize_unicode
from friday_llm.pipeline.deduplication.dedupe import approx_dedupe, exact_dedupe, minhash_dedupe
from friday_llm.pipeline.ingest.repo_docs import ingest_repo_markdown
from friday_llm.pipeline.quality.contamination import (
    build_forbidden_corpus,
    is_eval_contaminated,
)
from friday_llm.pipeline.registry.catalog import load_catalog, validate_entry
from friday_llm.rag.router import route_query
from friday_llm.rag.store import LocalRagStore
from friday_llm.util import content_hash, looks_like_pii, read_jsonl, resolve_path


def test_normalize_and_clean_keeps_good_doc():
    stats = CleanStats()
    doc = clean_document(
        {
            "text": normalize_unicode(
                "A F.R.I.D.A.Y. separa pesos, RAG e tools. " * 20
            ),
            "source": "test",
            "language": "por",
        },
        min_chars=50,
        stats=stats,
    )
    assert doc is not None
    assert doc["content_hash"] == content_hash(doc["text"])
    assert stats.kept == 1


def test_clean_drops_pii_and_short():
    stats = CleanStats()
    assert (
        clean_document({"text": "contact me@example.com now " * 20}, stats=stats)
        is None
    )
    assert looks_like_pii("token sk_abcdefghijklmnopqrstuvwxyz")
    assert clean_document({"text": "curto"}, min_chars=50, stats=stats) is None


def test_clean_drops_eval_leak():
    eval_path = resolve_path("friday-llm/data/evaluation/friday_eval.jsonl")
    forbidden_hashes, forbidden_shingles = build_forbidden_corpus(str(eval_path), None)
    checker = lambda text: is_eval_contaminated(  # noqa: E731
        text, forbidden_hashes=forbidden_hashes, forbidden_shingles=forbidden_shingles
    )
    stats = CleanStats()
    eval_row = next(
        r for r in read_jsonl(eval_path) if r.get("id") == "pt_time_tool"
    )
    leaked_text = f"{eval_row['input']} {eval_row['rubric']} " * 8
    leaked = clean_document(
        {"text": leaked_text, "source": "test"},
        min_chars=50,
        contamination_checker=checker,
        stats=stats,
    )
    assert leaked is None
    assert stats.reasons.get("eval_leak", 0) >= 1


def test_exact_and_approx_dedupe():
    a = {"text": "hello world " * 30, "content_hash": content_hash("hello world " * 30)}
    b = {"text": a["text"], "content_hash": a["content_hash"]}
    kept, dropped = exact_dedupe([a, b])
    assert len(kept) == 1 and dropped == 1
    near = {
        "text": "hello world " * 29 + "hello worlds ",
        "content_hash": "x",
    }
    kept2, dropped2 = approx_dedupe([a, near], threshold=0.5)
    assert len(kept2) >= 1


def test_minhash_dedupe_drops_near_duplicate():
    base = "the quick brown fox jumps over the lazy dog " * 8
    a = {"text": base, "content_hash": content_hash(base)}
    b = {"text": base[:-5] + "dogs ", "content_hash": content_hash(base[:-5] + "dogs ")}
    kept, dropped = minhash_dedupe([a, b], threshold=0.75)
    assert len(kept) == 1 and dropped == 1


def test_ingest_repo_markdown_finds_docs():
    docs = list(
        ingest_repo_markdown(
            ["friday-llm/README.md"],
            excluded_paths=["friday-llm/tests"],
        )
    )
    assert docs
    assert docs[0]["source"] == "repo_docs"
    assert docs[0]["url_or_path"]


def test_rag_chunk_provenance_fields():
    doc = {
        "document_id": "abc",
        "title": "Test Doc",
        "text": ("Paragraph one about VLAN IoT isolation.\n\n" * 5)
        + ("Paragraph two about network segmentation.\n\n" * 5),
        "source": "repo_docs",
        "url_or_path": "docs/test.md",
        "captured_at_or_version": "git",
        "language": "pt",
        "permissions": "project_docs",
        "license": "Apache-2.0",
    }
    chunks = chunk_document(doc, chunk_chars=200, chunk_overlap=20)
    assert chunks
    row = chunks[0]
    for field in (
        "text",
        "title",
        "source",
        "url_or_document_id",
        "captured_at_or_version",
        "language",
        "permissions",
        "content_hash",
    ):
        assert field in row


def test_sft_tools_subset_of_registry():
    seed_path = resolve_path("friday-llm/data/sft/seed_sft.jsonl")
    rows = [
        json.loads(line)
        for line in seed_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    train, holdout, meta = build_sft_dataset(rows, expand_from_registry=True, seed=42)
    assert len(train) + len(holdout) >= 40
    assert meta["invalid_tools"] == []
    assert validate_sft_tools(train + holdout) == []


def test_catalog_schema_validation():
    rows = load_catalog("friday-llm/data/registry/datasets.jsonl")
    assert rows
    for entry in rows:
        assert validate_entry(entry) == []


def test_router_tools_rag_model():
    assert route_query("Que horas sao?").suggested_tool == "get_current_datetime"
    assert route_query("Noticias do Japao").route == "tool"
    assert route_query("O que diz o manual sobre VLAN").route == "rag"
    assert route_query("Na documentação do projeto, como ligo o LM Studio?").route == "rag"
    assert route_query("Pesquisa na web o Phi-4").route == "tool"
    assert route_query("https://example.com/x").suggested_tool == "fetch_url"
    assert route_query("Explica o que e uma hash function").route == "model"


def test_rag_store_returns_sources(tmp_path):
    path = tmp_path / "docs.jsonl"
    path.write_text(
        '{"document_id":"1","title":"VLAN","source":"docs","url_or_path":"docs/x.md",'
        '"captured_at_or_version":"v0","language":"pt",'
        '"text":"A VLAN IoT isola cameras da rede principal."}\n',
        encoding="utf-8",
    )
    store = LocalRagStore(path)
    hits = store.search("VLAN IoT cameras")
    assert hits
    assert hits[0].url_or_document_id
    assert hits[0].score > 0


def test_fase1_build_offline():
    from friday_llm.pipeline.build_datasets.cli import build_from_config

    report = build_from_config(
        "friday-llm/configs/fase1_data.yaml",
        allow_network=False,
    )
    assert report["cpt_docs"] > 0
    assert report["eval_validation"]["ok"] is True
    assert Path(report["cpt_path"]).is_file()
    assert Path(report["rag_path"]).is_file()
