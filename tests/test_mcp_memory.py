"""Tests for MCP prompts, memory, and map geocode."""

from __future__ import annotations

import pytest

from friday.mcp_server.prompts import (
    build_explain_code_prompt,
    build_summarize_prompt,
    extractive_summary,
)
from friday.memory.chroma_store import ChromaStore
from friday.skills.local.memory_skills import RecallSkill, RememberSkill
from friday.skills.news.rss_common import guess_lat_lon, write_monitor_data


def test_summarize_prompt_contains_text():
    p = build_summarize_prompt("Ola mundo. Segunda frase.", style="curto")
    assert "Ola mundo" in p
    assert "Resume" in p or "resumo" in p.casefold()


def test_explain_code_prompt():
    p = build_explain_code_prompt("def f():\n  return 1", language="python")
    assert "def f" in p
    assert "passo a passo" in p.casefold() or "Explica" in p


def test_extractive_summary():
    text = "Um. Dois. Tres. Quatro."
    out = extractive_summary(text, max_sentences=2)
    assert "Um" in out
    assert "Dois" in out


def test_guess_lat_lon_ukraine():
    lat, lon = guess_lat_lon("Conflict intensifies in Ukraine near Kyiv")
    assert lat > 40


def test_write_monitor_includes_leaflet(tmp_path, monkeypatch):
    import friday.skills.news.rss_common as rss

    monkeypatch.setattr(rss, "_MONITORS_DIR", tmp_path)
    monkeypatch.setattr(rss, "_DATA_DIR", tmp_path / "data")
    snap = write_monitor_data(
        "world",
        [{"title": "News from Portugal Lisbon", "link": "http://x", "summary": ""}],
    )
    html = snap.read_text(encoding="utf-8")
    assert "leaflet" in html.casefold()
    assert "L.marker" in html


@pytest.mark.asyncio
async def test_remember_and_recall(tmp_path):
    store = ChromaStore(persist_dir=tmp_path)
    assert store.available
    store.add("O projecto FRIDAY usa Phi-4 localmente.", metadata={"label": "test"})
    hits = store.query("Phi-4", n=2)
    assert hits
    assert any("Phi-4" in h for h in hits)

    # skills
    from friday.memory import chroma_store as cs

    old = cs._shared
    cs._shared = store
    try:
        rem = RememberSkill()
        r1 = await rem.execute({"text": "A porta do laboratorio e 42."})
        assert r1.success
        rec = RecallSkill()
        r2 = await rec.execute({"query": "laboratorio porta"})
        assert r2.success
        assert "42" in r2.content
    finally:
        cs._shared = old


def test_create_mcp_server_imports():
    pytest.importorskip("mcp")
    from friday.mcp_server.server import create_mcp_server

    server = create_mcp_server()
    assert server is not None
