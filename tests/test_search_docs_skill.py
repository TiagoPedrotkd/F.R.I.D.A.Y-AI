"""Tests for search_docs skill and UI payload."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "services" / "agent-api"))

from session_store import extract_ui_payload  # noqa: E402

from friday.config import Settings
from friday.rag.doc_store import reset_doc_store
from friday.skills.rag.search_docs import SearchDocsSkill
from friday_llm.util import write_jsonl


@pytest.mark.asyncio
async def test_search_docs_skill_no_hits(tmp_path: Path):
    corpus = tmp_path / "chunks.jsonl"
    write_jsonl(corpus, [])
    reset_doc_store()
    settings = Settings(
        RAG_ENABLED=True,
        RAG_BACKEND="keyword",
        RAG_CORPUS_PATH=str(corpus),
        RAG_INDEX_DIR=str(tmp_path / "idx"),
    )
    skill = SearchDocsSkill(settings=settings)
    result = await skill.execute({"query": "manual VLAN IoT"})
    assert result.success
    assert "nao encontrei" in result.content.casefold() or "nao invento" in result.content.casefold()
    assert result.metadata.get("count") == 0


@pytest.mark.asyncio
async def test_search_docs_skill_with_hit(tmp_path: Path):
    corpus = tmp_path / "chunks.jsonl"
    write_jsonl(
        corpus,
        [
            {
                "text": "A VLAN IoT isola dispositivos domesticos da rede principal.",
                "title": "Rede VLAN",
                "source": "docs",
                "url_or_document_id": "docs/arquitectura/rede-vlan.md",
                "captured_at_or_version": "git",
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
    skill = SearchDocsSkill(settings=settings)
    result = await skill.execute({"query": "VLAN IoT rede"})
    assert result.success
    assert result.metadata.get("count", 0) >= 1
    ui = extract_ui_payload(result.content, result.metadata)
    assert len(ui["sources"]) >= 1
    assert ui["sources"][0].get("kind") == "document"
    assert ui.get("document_search") is True


def test_search_docs_registered():
    from friday.skills.registry import default_registry

    reg = default_registry()
    assert "search_docs" in reg.names()
