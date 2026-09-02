"""Unit tests for grounding, context budget, calculate, session persistence."""

from __future__ import annotations

import pytest

from friday.llm.grounding import grounding_score, needs_web_grounding
from friday.memory.context_budget import trim_messages_to_budget
from friday.memory.session_persistence import SessionPersistence
from friday.memory.short_term import ShortTermMemory
from friday.skills.local.calculate import CalculateSkill, safe_eval


def test_needs_web_grounding_search():
    assert needs_web_grounding("Pesquisa a versao mais recente do Phi-4")
    assert not needs_web_grounding("Ola Friday, como estas hoje?")


def test_grounding_score_with_citation():
    g = grounding_score(
        "Segundo https://example.com/a a versao e X.",
        tool_urls=["https://example.com/a"],
        used_web_tools=True,
    )
    assert g["grounded"] is True
    assert g["score"] >= 0.7


def test_trim_messages_keeps_newest():
    msgs = [
        {"role": "system", "content": "sys"},
        {"role": "user", "content": "a" * 400},
        {"role": "assistant", "content": "b" * 400},
        {"role": "user", "content": "recent"},
    ]
    out = trim_messages_to_budget(msgs, max_tokens=80)
    assert out[0]["role"] == "system"
    assert out[-1]["content"] == "recent"


def test_short_term_summary_on_overflow():
    mem = ShortTermMemory(max_messages=4, keep_recent=2)
    mem.add_user("u1")
    mem.add_assistant("a1")
    mem.add_user("u2")
    mem.add_assistant("a2")
    mem.add_user("u3")  # triggers compact
    assert mem.session_summary
    hist = mem.history_for_llm()
    assert hist[0]["role"] == "system"
    assert "Resumo" in hist[0]["content"]


def test_session_persistence_roundtrip(tmp_path):
    mem = ShortTermMemory(max_messages=10)
    mem.add_user("hello")
    mem.add_assistant("hi")
    mem.last_country = "PT"
    persist = SessionPersistence(tmp_path)
    persist.save("abc123", mem)
    loaded = persist.load("abc123")
    assert loaded is not None
    restored = ShortTermMemory.from_dict(loaded["memory"])
    assert restored.last_country == "PT"
    assert len(restored) == 2


def test_safe_eval():
    assert safe_eval("2+3*4") == 14


@pytest.mark.asyncio
async def test_calculate_skill():
    skill = CalculateSkill()
    result = await skill.execute({"expression": "17*23+5"})
    assert result.success
    assert "396" in result.content


def test_prefs_store_roundtrip(tmp_path):
    from friday.memory.prefs_store import PrefsStore

    store = PrefsStore(tmp_path)
    updated = store.update({"language": "en", "volume": 0.5})
    assert updated["language"] == "en"
    assert store.get()["volume"] == 0.5


def test_prompt_version_constant():
    from friday.llm.prompts import PROMPT_VERSION, prompt_meta

    assert PROMPT_VERSION.startswith("v")
    assert prompt_meta()["prompt_version"] == PROMPT_VERSION


def test_plan_docs_and_web():
    from friday.llm.planner import plan_steps

    steps = plan_steps("Consulta o manual interno e depois pesquisa na web sobre VLAN")
    assert len(steps) >= 2
    assert steps[0].skill == "search_docs"
    assert steps[1].skill == "research_web"


def test_plan_empty_for_simple_chat():
    from friday.llm.planner import plan_steps

    assert plan_steps("Ola Friday") == []


def test_confidence_report_levels():
    from friday.quality.confidence import confidence_report

    high = confidence_report(
        "Segundo https://example.com a versao e 1.",
        grounding={"score": 1.0, "grounded": True, "used_web_tools": True},
        tool_rounds=1,
    )
    assert high["level"] == "high"
    low = confidence_report(
        "Com certeza absoluta que inventei isto.",
        grounding={"score": 0.0, "grounded": False},
        tool_rounds=0,
    )
    assert low["hallucination_risk"] in ("medium", "high")
