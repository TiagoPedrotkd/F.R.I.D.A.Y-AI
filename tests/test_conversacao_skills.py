"""Tests for conversational skills and intent routing."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from friday.llm.intent_router import match_skill, match_skill_with_args
from friday.skills.local.datetime_skill import DateTimeSkill
from friday.skills.local.format_json import FormatJsonSkill
from friday.skills.local.system_info import SystemInfoSkill
from friday.skills.local.word_count import WordCountSkill
from friday.skills.news.rss_common import summarize_headlines, write_monitor_data
from friday.skills.registry import default_registry
from friday.skills.web.fetch_url import FetchUrlSkill
from friday.skills.web.search_web import SearchWebSkill


@pytest.mark.asyncio
async def test_datetime_includes_weekday():
    skill = DateTimeSkill()
    result = await skill.execute({"timezone": "Europe/Lisbon"})
    assert result.success
    assert "Sao" in result.content
    assert result.metadata and "weekday" in result.metadata


@pytest.mark.asyncio
async def test_word_count():
    skill = WordCountSkill()
    result = await skill.execute({"text": "ola mundo friday"})
    assert result.success
    assert "Palavras: 3" in result.content


@pytest.mark.asyncio
async def test_format_json_valid():
    skill = FormatJsonSkill()
    result = await skill.execute({"json_text": '{"a":1}'})
    assert result.success
    assert '"a": 1' in result.content


@pytest.mark.asyncio
async def test_format_json_invalid():
    skill = FormatJsonSkill()
    result = await skill.execute({"json_text": "{bad"})
    assert not result.success
    assert "invalido" in (result.error or "").casefold()


@pytest.mark.asyncio
async def test_system_info():
    skill = SystemInfoSkill()
    result = await skill.execute({})
    assert result.success
    assert "Python" in result.content
    assert result.metadata and "hostname" in result.metadata


def test_default_registry_has_core_skills():
    names = set(default_registry().names())
    assert "get_current_datetime" in names
    assert "get_current_time" in names  # alias
    assert "get_world_news" in names
    assert "search_web" in names
    assert "fetch_url" in names
    assert "format_json" in names


def test_intent_time_and_news():
    assert match_skill("Que horas são?") == "get_current_datetime"
    assert match_skill_with_args("Que horas são em Seul?") == (
        "get_current_datetime",
        {"timezone": "Asia/Seoul"},
    )
    assert match_skill("Põe-me a par") == "get_world_news"
    assert match_skill("Briefing financeiro") == "get_world_finance_news"
    assert match_skill("Abre o monitor mundial") == "open_world_monitor"
    assert match_skill("Abre o monitor financeiro") == "open_finance_world_monitor"


def test_intent_search_system_json():
    assert match_skill("Pesquisa o Phi-4") == "search_web"
    name, args = match_skill_with_args("Pesquisa o Phi-4")
    assert name == "search_web"
    assert "Phi-4" in args["query"]
    assert match_skill("Que sistema operativo estou a usar?") == "get_system_info"
    name, args = match_skill_with_args('Formata este JSON: {"x":1}')
    assert name == "format_json"
    assert '"x"' in args["json_text"]


def test_intent_fetch_url():
    name, args = match_skill_with_args("Lê https://example.com/page")
    assert name == "fetch_url"
    assert args["url"].startswith("https://example.com")


def test_summarize_and_write_monitor(tmp_path, monkeypatch):
    headlines = [{"title": "Test A", "link": "http://x", "summary": "s"}]
    assert "Test A" in summarize_headlines(headlines, "Briefing:")

    import friday.skills.news.rss_common as rss

    monkeypatch.setattr(rss, "_MONITORS_DIR", tmp_path)
    monkeypatch.setattr(rss, "_DATA_DIR", tmp_path / "data")
    snap = write_monitor_data("world", headlines)
    assert snap.is_file()
    assert "Test A" in snap.read_text(encoding="utf-8")


@pytest.mark.asyncio
async def test_fetch_url_invalid():
    skill = FetchUrlSkill()
    result = await skill.execute({"url": "not-a-url"})
    assert not result.success


@pytest.mark.asyncio
async def test_search_web_empty_query():
    skill = SearchWebSkill()
    result = await skill.execute({"query": ""})
    assert not result.success


@pytest.mark.asyncio
async def test_open_monitor_mocked():
    from friday.skills.news import OpenWorldMonitorSkill

    with patch("friday.skills.news.rss_common.webbrowser.open") as open_mock:
        skill = OpenWorldMonitorSkill()
        # Ensure snapshot or template exists path — may fail if missing; create via write
        write_monitor_data("world", [{"title": "H", "link": "", "summary": ""}])
        result = await skill.execute({})
        assert result.success
        open_mock.assert_called_once()
