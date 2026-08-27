"""Acceptance tests for conversational contract (mocked I/O)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from friday.config import Settings
from friday.llm.intent_router import match_skill, match_skill_with_args
from friday.llm.tool_runner import ToolRunner
from friday.memory.short_term import ShortTermMemory
from friday.safety.confirmation import ConfirmationGate, PendingAction
from friday.skills.news import FinanceNewsSkill, WorldNewsSkill
from friday.skills.registry import SkillRegistry, default_registry
from friday.skills.web.fetch_url import FetchUrlSkill, _validate_url
from friday.skills.web.search_web import SearchWebSkill
from friday.tts.speech_text import prepare_speech_text


def _settings(**kwargs) -> Settings:
    values = {
        "lm_studio_base_url_host": "http://localhost:1234/v1",
        "auto_open_monitors": False,
    }
    values.update(kwargs)
    return Settings.model_construct(**values)


@pytest.mark.asyncio
async def test_que_horas_sao_calls_datetime():
    assert match_skill("Que horas são?") == "get_current_datetime"
    runner = ToolRunner(_settings(), default_registry(_settings()), client=MagicMock())
    reply = await runner.chat_with_tools("Que horas são?")
    assert reply.tool_rounds == 1
    assert "Sao" in reply.text or "são" in reply.text.casefold() or ":" in reply.text


def test_que_dia_e_hoje():
    assert match_skill("Que dia é hoje?") == "get_current_datetime"


def test_what_time_is_it_english():
    assert match_skill("What time is it?") == "get_current_datetime"


def test_noticias_japao_country():
    assert match_skill_with_args("Quais são as notícias do Japão?") == (
        "get_world_news",
        {"country": "JP"},
    )


@pytest.mark.asyncio
async def test_e_as_financas_reuses_country(tmp_path, monkeypatch):
    import friday.skills.news.rss_common as rss

    monkeypatch.setattr(rss, "_MONITORS_DIR", tmp_path)
    monkeypatch.setattr(rss, "_DATA_DIR", tmp_path / "data")
    monkeypatch.setattr(rss, "_CACHE_DIR", tmp_path / "cache")

    def fake_fetch(urls, limit=8, use_cache=True):
        return [{"title": "Nikkei note", "link": "http://x", "summary": ""}]

    session = ShortTermMemory()
    session.last_country = "JP"
    settings = _settings(auto_open_monitors=False)
    registry = default_registry(settings)
    runner = ToolRunner(settings, registry, client=MagicMock(), session=session)

    with patch("friday.skills.news.fetch_rss_headlines", fake_fetch):
        reply = await runner.chat_with_tools("E as finanças?", session=session)
    assert reply.tool_rounds == 1
    assert session.last_country == "JP"
    assert "Nikkei" in reply.text or "financ" in reply.text.casefold()
    assert "cotacoes em tempo real" in reply.text.casefold() or "headlines" in reply.text.casefold()


@pytest.mark.asyncio
async def test_news_described_as_headlines(tmp_path, monkeypatch):
    import friday.skills.news.rss_common as rss

    monkeypatch.setattr(rss, "_MONITORS_DIR", tmp_path)
    monkeypatch.setattr(rss, "_DATA_DIR", tmp_path / "data")
    monkeypatch.setattr(rss, "_CACHE_DIR", tmp_path / "cache")

    with patch(
        "friday.skills.news.fetch_rss_headlines",
        return_value=[{"title": "Story", "link": "", "summary": ""}],
    ):
        skill = WorldNewsSkill(auto_open_monitors=False)
        result = await skill.execute({"country": "WW", "open_monitor": False})
    assert result.success
    assert "headlines" in result.content.casefold()
    assert result.metadata.get("headlines_only") is True
    assert "Queres que abra o mapa" in result.content


@pytest.mark.asyncio
async def test_finance_not_realtime_prices(tmp_path, monkeypatch):
    import friday.skills.news.rss_common as rss

    monkeypatch.setattr(rss, "_MONITORS_DIR", tmp_path)
    monkeypatch.setattr(rss, "_DATA_DIR", tmp_path / "data")
    monkeypatch.setattr(rss, "_CACHE_DIR", tmp_path / "cache")

    with patch(
        "friday.skills.news.fetch_rss_headlines",
        return_value=[{"title": "Markets up", "link": "", "summary": ""}],
    ):
        skill = FinanceNewsSkill(auto_open_monitors=False)
        result = await skill.execute({"country": "US", "open_monitor": False})
    assert "tempo real" in result.content.casefold()
    assert result.metadata.get("not_realtime_prices") is True


@pytest.mark.asyncio
async def test_search_web_structured_sources():
    skill = SearchWebSkill()
    fake = [
        {
            "title": "Phi-4",
            "body": "Microsoft model",
            "href": "https://example.com/phi4",
        }
    ]

    class _FakeDDGS:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def text(self, query, max_results=5):
            return fake

    import ddgs as ddgs_mod

    with patch.object(ddgs_mod, "DDGS", _FakeDDGS):
        result = await skill.execute({"query": "Phi-4 latest"})
    assert result.success
    assert result.metadata["results"][0]["url"] == "https://example.com/phi4"
    assert result.metadata["results"][0]["source"] == "example.com"
    assert "Fontes" in result.content


@pytest.mark.asyncio
async def test_search_empty_is_honest():
    skill = SearchWebSkill()
    result = await skill.execute({"query": ""})
    assert not result.success


@pytest.mark.asyncio
async def test_phantom_tools_rejected():
    runner = ToolRunner(_settings(), default_registry(_settings()), client=MagicMock())
    reply = await runner._run_skill_direct("read_webpage", {"url": "https://x.com"})
    assert "nao tenho a ferramenta" in reply.text.casefold() or "ferramenta" in reply.text.casefold()
    reply2 = await runner._run_skill_direct("get_system_status", {})
    assert "ferramenta" in reply2.text.casefold()


def test_system_info_intent():
    assert match_skill("Que sistema operativo estou a usar?") == "get_system_info"


def test_word_count_intent():
    assert match_skill("Conta as palavras deste texto") == "word_count"


def test_format_json_intent():
    name, args = match_skill_with_args('Formata este JSON: {"a":1}')
    assert name == "format_json"
    assert "a" in args["json_text"]


def test_general_question_no_tool():
    assert match_skill("Ola, tudo bem?") is None
    assert match_skill("Explica o que e uma lista em Python") is None


def test_english_greeting_language_hint():
    mem = ShortTermMemory()
    mem.set_language_hint("Hello Friday, how are you?")
    assert mem.last_language == "en"


def test_tts_short_natural():
    out = prepare_speech_text("**Resposta** curta.\n- item")
    assert "**" not in out
    assert len(out) < 200


def test_tts_strips_markdown_keeps_meaning():
    out = prepare_speech_text("A **resposta** e 42.")
    assert "resposta" in out and "42" in out


def test_open_monitor_intent():
    assert match_skill("Abre o monitor mundial") == "open_world_monitor"


@pytest.mark.asyncio
async def test_auto_open_false_offers_monitor(tmp_path, monkeypatch):
    import friday.skills.news.rss_common as rss

    monkeypatch.setattr(rss, "_MONITORS_DIR", tmp_path)
    monkeypatch.setattr(rss, "_DATA_DIR", tmp_path / "data")
    monkeypatch.setattr(rss, "_CACHE_DIR", tmp_path / "cache")
    with patch(
        "friday.skills.news.fetch_rss_headlines",
        return_value=[{"title": "H", "link": "", "summary": ""}],
    ):
        with patch("friday.skills.news.open_monitor") as open_mock:
            skill = WorldNewsSkill(auto_open_monitors=False)
            result = await skill.execute({"country": "PT"})
    open_mock.assert_not_called()
    assert result.metadata["opened"] is False
    assert "Queres que abra" in result.content


@pytest.mark.asyncio
async def test_never_claims_opened_on_failure(tmp_path, monkeypatch):
    import friday.skills.news.rss_common as rss

    monkeypatch.setattr(rss, "_MONITORS_DIR", tmp_path)
    monkeypatch.setattr(rss, "_DATA_DIR", tmp_path / "data")
    monkeypatch.setattr(rss, "_CACHE_DIR", tmp_path / "cache")
    with patch(
        "friday.skills.news.fetch_rss_headlines",
        return_value=[{"title": "H", "link": "", "summary": ""}],
    ):
        with patch(
            "friday.skills.news.open_monitor",
            return_value=(False, "falhou"),
        ):
            skill = WorldNewsSkill(auto_open_monitors=True)
            result = await skill.execute({"country": "WW", "open_monitor": True})
    assert result.metadata["opened"] is False
    assert "Nao consegui abrir o monitor" in result.content


def test_confirmation_gate_blocks_until_explicit():
    gate = ConfirmationGate()
    msg = gate.request(
        PendingAction(
            action="delete_file",
            target="notes.txt",
            summary="apagar o ficheiro notes.txt",
            consequences="o ficheiro nao podera ser recuperado",
        )
    )
    assert "Confirmas" in msg
    status, _ = gate.interpret("talvez amanha")
    assert status == "waiting"
    status, action = gate.interpret("sim")
    assert status == "confirmed"
    assert action and action.target == "notes.txt"
    # Old yes cannot authorize a new action
    gate.request(
        PendingAction(
            action="send_email",
            target="a@b.com",
            summary="enviar email",
        )
    )
    status, _ = gate.interpret("ola")
    assert status == "waiting"


def test_fetch_url_blocks_localhost():
    assert _validate_url("http://127.0.0.1/secret") is not None
    assert _validate_url("http://localhost/x") is not None
    assert _validate_url("https://example.com/ok") is None


@pytest.mark.asyncio
async def test_fetch_url_invalid_scheme():
    skill = FetchUrlSkill()
    result = await skill.execute({"url": "file:///etc/passwd"})
    assert not result.success


def test_prompt_has_no_phantom_tools():
    from friday.llm.prompts import FRIDAY_SYSTEM_PROMPT

    assert "read_webpage" not in FRIDAY_SYSTEM_PROMPT
    assert "get_system_status" not in FRIDAY_SYSTEM_PROMPT
    assert "get_country_briefing" in FRIDAY_SYSTEM_PROMPT
    assert "fetch_url" in FRIDAY_SYSTEM_PROMPT
