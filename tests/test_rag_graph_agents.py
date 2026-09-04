"""RAG router ops patterns, knowledge graph, reflect gating."""

from friday.llm.intent_router import match_skill
from friday.llm.tool_runner import ChatReply, ToolRunner
from friday.rag.knowledge_graph import (
    extract_edges_from_text,
    format_graph_block,
    search_graph,
)
from friday_llm.rag.router import route_query


def test_rag_router_ops_ports():
    d = route_query("Como correr o agent-api na porta 8090?")
    assert d.route == "rag"


def test_rag_router_rag_chroma():
    d = route_query("Onde fica o indice rag_chroma friday_docs?")
    assert d.route == "rag"


def test_intent_search_docs_ops():
    assert match_skill("Onde fica o rag_chroma?") == "search_docs"


def test_intent_knowledge_graph():
    assert match_skill("O que depende do agent-api na arquitectura?") == (
        "search_knowledge_graph"
    )


def test_kg_extract_arrows():
    edges = extract_edges_from_text(
        "Web UI depende de agent-api\nagent-api → LM Studio\n",
        doc="facts.md",
    )
    assert any(e["target"].lower().find("agent") >= 0 or "agent" in e["source"].lower() for e in edges)
    assert any("LM Studio" in e.get("target", "") or "lm studio" in e.get("target", "").lower() for e in edges)


def test_kg_format_and_search_smoke():
    # Uses on-disk graph if present; empty is ok
    hits = search_graph("agent-api")
    block = format_graph_block(hits)
    if hits:
        assert "KNOWLEDGE GRAPH" in block
        assert "agent" in block.casefold() or "api" in block.casefold()


def test_reflect_skips_greeting():
    class _Dummy:
        pass

    # ToolRunner needs client/registry — only test static helper
    assert ToolRunner._is_trivial_utterance("Ola") is True
    assert ToolRunner._is_trivial_utterance("Bom dia") is True
    assert ToolRunner._is_trivial_utterance("Como funciona a arquitectura do agent-api?") is False


def test_should_reflect_complex():
    class FakeRunner:
        def _is_trivial_utterance(self, t):
            return ToolRunner._is_trivial_utterance(t)

        def _should_reflect(self, user_text, reply):
            return ToolRunner._should_reflect(self, user_text, reply)

    r = FakeRunner()
    reply = ChatReply(text="x" * 40, skill_metadata={"quality_scores": {"a": 0.5}})
    assert r._should_reflect("Ola", reply) is False
    assert r._should_reflect("Analisa a arquitectura e dependencias", reply) is True
