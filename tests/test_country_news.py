"""Tests for country profiles, news/finance by country, and RSS cache."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from friday.llm.intent_router import match_skill, match_skill_with_args
from friday.skills.news import (
    CountryBriefingSkill,
    FinanceNewsSkill,
    ListSupportedCountriesSkill,
    WorldNewsSkill,
)
from friday.skills.news.countries import (
    resolve_country,
    extract_country_from_utterance,
    list_countries_text,
)
from friday.skills.news.countries import _normalize_key
from friday.skills.registry import default_registry


def test_resolve_country_codes_and_names():
    assert resolve_country(None).code == "WW"
    assert resolve_country("").code == "WW"
    assert resolve_country("JP").code == "JP"
    assert resolve_country("japao").code == "JP"
    assert resolve_country("Japão").code == "JP"
    assert resolve_country("UK").code == "GB"
    assert resolve_country("Brasil").code == "BR"
    assert resolve_country("Atlantis") is None


def test_extract_country_from_utterance():
    norm = _normalize_key("noticias do japao")
    assert extract_country_from_utterance(norm).code == "JP"
    norm = _normalize_key("financas na alemanha")
    assert extract_country_from_utterance(norm).code == "DE"


def test_intent_country_news_finance():
    assert match_skill_with_args("Notícias do Japão") == (
        "get_world_news",
        {"country": "JP"},
    )
    assert match_skill_with_args("Finanças na Alemanha") == (
        "get_world_finance_news",
        {"country": "DE"},
    )
    assert match_skill_with_args("O que se passa no Brasil?") == (
        "get_world_news",
        {"country": "BR"},
    )
    assert match_skill("Põe-me a par") == "get_world_news"
    assert match_skill_with_args("Põe-me a par") == ("get_world_news", {})
    assert match_skill("Que países suportados?") == "list_supported_countries"
    name, args = match_skill_with_args("Notícias e finanças em Portugal")
    assert name == "get_country_briefing"
    assert args["country"] == "PT"


def test_registry_has_country_skills():
    names = set(default_registry().names())
    assert "get_country_briefing" in names
    assert "list_supported_countries" in names
    assert "get_news" in names


@pytest.mark.asyncio
async def test_list_supported_countries():
    skill = ListSupportedCountriesSkill()
    result = await skill.execute({})
    assert result.success
    assert "JP" in result.content
    assert "Portugal" in result.content


@pytest.mark.asyncio
async def test_world_news_unknown_country():
    skill = WorldNewsSkill()
    result = await skill.execute({"country": "Atlantis"})
    assert not result.success
    assert "Atlantis" in (result.error or "")


@pytest.mark.asyncio
async def test_world_news_with_mock_rss(tmp_path, monkeypatch):
    import friday.skills.news.rss_common as rss

    monkeypatch.setattr(rss, "_MONITORS_DIR", tmp_path)
    monkeypatch.setattr(rss, "_DATA_DIR", tmp_path / "data")
    monkeypatch.setattr(rss, "_CACHE_DIR", tmp_path / "cache")

    headlines = [
        {"title": "Tokyo markets open", "link": "http://x", "summary": "Japan"},
    ]

    def fake_fetch(urls, limit=8, use_cache=True):
        return headlines

    monkeypatch.setattr(rss, "fetch_rss_headlines", fake_fetch)
    # Skill imports fetch at module level — patch on news package usage
    with patch(
        "friday.skills.news.fetch_rss_headlines", fake_fetch
    ):
        with patch("friday.skills.news.open_monitor", return_value=(True, "opened")):
            skill = WorldNewsSkill()
            result = await skill.execute({"country": "JP", "open_monitor": True})
    assert result.success
    assert result.metadata["country"] == "JP"
    assert "Tokyo" in result.content
    snap = tmp_path / "world_snapshot.html"
    assert snap.is_file()
    html = snap.read_text(encoding="utf-8")
    assert "Japao" in html or "Japão" in html or "setView([35.68" in html


@pytest.mark.asyncio
async def test_finance_disclaimer(tmp_path, monkeypatch):
    import friday.skills.news.rss_common as rss

    monkeypatch.setattr(rss, "_MONITORS_DIR", tmp_path)
    monkeypatch.setattr(rss, "_DATA_DIR", tmp_path / "data")
    monkeypatch.setattr(rss, "_CACHE_DIR", tmp_path / "cache")

    def fake_fetch(urls, limit=8, use_cache=True):
        return [{"title": "DAX rises", "link": "", "summary": ""}]

    with patch("friday.skills.news.fetch_rss_headlines", fake_fetch):
        with patch("friday.skills.news.open_monitor", return_value=(False, "")):
            skill = FinanceNewsSkill()
            result = await skill.execute({"country": "DE", "open_monitor": False})
    assert result.success
    assert "aconselhamento financeiro" in result.content.casefold()
    assert "DAX" in result.content


@pytest.mark.asyncio
async def test_country_briefing(tmp_path, monkeypatch):
    import friday.skills.news.rss_common as rss

    monkeypatch.setattr(rss, "_MONITORS_DIR", tmp_path)
    monkeypatch.setattr(rss, "_DATA_DIR", tmp_path / "data")
    monkeypatch.setattr(rss, "_CACHE_DIR", tmp_path / "cache")

    def fake_fetch(urls, limit=8, use_cache=True):
        return [{"title": "Headline", "link": "", "summary": ""}]

    with patch("friday.skills.news.fetch_rss_headlines", fake_fetch):
        with patch("friday.skills.news.open_monitor", return_value=(True, "ok")):
            skill = CountryBriefingSkill()
            result = await skill.execute({"country": "BR", "open_monitor": True})
    assert result.success
    assert result.metadata["country"] == "BR"
    assert result.metadata["news_ok"]
    assert result.metadata["finance_ok"]


def test_rss_cache(tmp_path, monkeypatch):
    import friday.skills.news.rss_common as rss

    monkeypatch.setattr(rss, "_CACHE_DIR", tmp_path)
    calls = {"n": 0}

    def fake_one(_url):
        calls["n"] += 1

        class E:
            title = "Cached item"
            link = "http://x"
            summary = "s"

        return [E()]

    monkeypatch.setattr(rss, "_fetch_one_feed", fake_one)
    urls = ["http://example.com/feed"]
    a = rss.fetch_rss_headlines(urls, limit=3, use_cache=True)
    b = rss.fetch_rss_headlines(urls, limit=3, use_cache=True)
    assert a[0]["title"] == "Cached item"
    assert b[0]["title"] == "Cached item"
    assert calls["n"] == 1


def test_pt_finance_feeds_are_local():
    profile = resolve_country("PT")
    assert profile is not None
    feeds = list(profile.finance_feeds)
    assert any("eco.sapo.pt" in u for u in feeds)
    assert not all("bbci.co.uk/news/business" in u for u in feeds)


@pytest.mark.asyncio
async def test_finance_pt_headlines_local(tmp_path, monkeypatch):
    import friday.skills.news.rss_common as rss

    monkeypatch.setattr(rss, "_MONITORS_DIR", tmp_path)
    monkeypatch.setattr(rss, "_DATA_DIR", tmp_path / "data")
    monkeypatch.setattr(rss, "_CACHE_DIR", tmp_path / "cache")

    headlines = [
        {
            "title": "PSI sobe com banca em alta",
            "link": "https://eco.sapo.pt/x",
            "summary": "Bolsa de Lisboa",
        },
    ]

    def fake_fetch(urls, limit=8, use_cache=True):
        assert any("eco.sapo.pt" in u for u in urls)
        return headlines

    with patch("friday.skills.news.fetch_rss_headlines", fake_fetch):
        with patch("friday.skills.news.open_monitor", return_value=(False, "")):
            skill = FinanceNewsSkill()
            result = await skill.execute({"country": "PT", "open_monitor": False})
    assert result.success
    assert "Portugal" in result.content
    assert "PSI" in result.content
    text = list_countries_text()
    assert "US:" in text
    assert "JP:" in text
