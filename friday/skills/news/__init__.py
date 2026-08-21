"""World and finance news skills + open monitor skills."""

from __future__ import annotations

from typing import Any

from friday.skills.base import SkillResult
from friday.skills.news.rss_common import (
    DEFAULT_FINANCE_FEEDS,
    DEFAULT_WORLD_FEEDS,
    fetch_rss_headlines,
    open_monitor,
    parse_feed_csv,
    summarize_headlines,
    write_monitor_data,
)


class WorldNewsSkill:
    name = "get_world_news"
    description = (
        "Briefing de noticias mundiais. Usa para 'o que esta a acontecer', "
        "'poe-me a par', 'world update'. Nao inventes noticias."
    )
    parameters: dict[str, Any] = {
        "type": "object",
        "properties": {},
        "required": [],
    }

    def __init__(self, feeds_csv: str = "", monitor_url: str = "") -> None:
        self._feeds_csv = feeds_csv
        self._monitor_url = monitor_url

    async def execute(self, arguments: dict[str, Any]) -> SkillResult:
        feeds = parse_feed_csv(self._feeds_csv, DEFAULT_WORLD_FEEDS)
        headlines = fetch_rss_headlines(feeds, limit=8)
        if not headlines:
            return SkillResult(
                success=False,
                content="",
                error="Nao consegui consultar essa informacao neste momento.",
            )
        write_monitor_data("world", headlines)
        opened, open_msg = open_monitor("world", self._monitor_url)
        summary = summarize_headlines(headlines, "Briefing mundial:")
        if opened:
            summary += f"\n({open_msg})"
        return SkillResult(
            success=True,
            content=summary,
            metadata={
                "count": len(headlines),
                "auto_open_monitor": "world",
                "opened": opened,
            },
        )


class FinanceNewsSkill:
    name = "get_world_finance_news"
    description = (
        "Briefing financeiro / mercados (headlines, nao cotacoes). "
        "Nao inventes noticias nem precos."
    )
    parameters: dict[str, Any] = {
        "type": "object",
        "properties": {},
        "required": [],
    }

    def __init__(self, feeds_csv: str = "", monitor_url: str = "") -> None:
        self._feeds_csv = feeds_csv
        self._monitor_url = monitor_url

    async def execute(self, arguments: dict[str, Any]) -> SkillResult:
        feeds = parse_feed_csv(self._feeds_csv, DEFAULT_FINANCE_FEEDS)
        headlines = fetch_rss_headlines(feeds, limit=8)
        if not headlines:
            return SkillResult(
                success=False,
                content="",
                error="Nao consegui consultar essa informacao neste momento.",
            )
        write_monitor_data("finance", headlines)
        opened, open_msg = open_monitor("finance", self._monitor_url)
        summary = summarize_headlines(headlines, "Briefing financeiro:")
        if opened:
            summary += f"\n({open_msg})"
        return SkillResult(
            success=True,
            content=summary,
            metadata={
                "count": len(headlines),
                "auto_open_monitor": "finance",
                "opened": opened,
            },
        )


class OpenWorldMonitorSkill:
    name = "open_world_monitor"
    description = "Abre o painel/monitor mundial de noticias."
    parameters: dict[str, Any] = {"type": "object", "properties": {}, "required": []}

    def __init__(self, monitor_url: str = "") -> None:
        self._monitor_url = monitor_url

    async def execute(self, arguments: dict[str, Any]) -> SkillResult:
        ok, msg = open_monitor("world", self._monitor_url)
        if not ok:
            return SkillResult(success=False, content="", error=msg)
        return SkillResult(success=True, content=msg)


class OpenFinanceMonitorSkill:
    name = "open_finance_world_monitor"
    description = "Abre o painel/monitor financeiro."
    parameters: dict[str, Any] = {"type": "object", "properties": {}, "required": []}

    def __init__(self, monitor_url: str = "") -> None:
        self._monitor_url = monitor_url

    async def execute(self, arguments: dict[str, Any]) -> SkillResult:
        ok, msg = open_monitor("finance", self._monitor_url)
        if not ok:
            return SkillResult(success=False, content="", error=msg)
        return SkillResult(success=True, content=msg)
