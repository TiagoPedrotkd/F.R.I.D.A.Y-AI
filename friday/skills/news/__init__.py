"""World and finance news skills + open monitor skills."""

from __future__ import annotations

from typing import Any

from friday.skills.base import SkillResult
from friday.skills.news.countries import (
    CountryProfile,
    finance_context_line,
    list_countries_text,
    resolve_country,
)
from friday.skills.news.rss_common import (
    DEFAULT_FINANCE_FEEDS,
    DEFAULT_WORLD_FEEDS,
    fetch_rss_headlines,
    open_monitor,
    parse_feed_csv,
    summarize_headlines,
    write_monitor_data,
)

_COUNTRY_PARAM = {
    "country": {
        "type": "string",
        "description": (
            "ISO 3166-1 alpha-2 (JP, BR, US, PT, ...) or country name. "
            "Empty = world (WW)."
        ),
    },
    "limit": {
        "type": "integer",
        "description": "Max headlines (default 8)",
    },
    "open_monitor": {
        "type": "boolean",
        "description": "Open local monitor snapshot (default from AUTO_OPEN_MONITORS)",
    },
}


def _resolve_or_error(country_arg: Any) -> tuple[CountryProfile | None, SkillResult | None]:
    raw = "" if country_arg is None else str(country_arg)
    profile = resolve_country(raw if raw.strip() else None)
    if profile is None:
        return None, SkillResult(
            success=False,
            content="",
            error=(
                f"Ainda nao tenho feeds para '{raw.strip()}'. "
                + list_countries_text()
            ),
        )
    return profile, None


def _feeds_for(
    profile: CountryProfile,
    *,
    kind: str,
    override_csv: str,
) -> list[str]:
    if profile.code == "WW" and override_csv.strip():
        defaults = DEFAULT_WORLD_FEEDS if kind == "world" else DEFAULT_FINANCE_FEEDS
        return parse_feed_csv(override_csv, defaults)
    feeds = profile.news_feeds if kind == "world" else profile.finance_feeds
    return list(feeds)


def _bool_arg(value: Any, default: bool) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() in ("1", "true", "yes")
    return bool(value)


def _offer_monitor(kind: str) -> str:
    if kind == "finance":
        return "Queres que abra o mapa financeiro?"
    return "Queres que abra o mapa?"


class WorldNewsSkill:
    name = "get_world_news"
    description = (
        "Briefing de noticias (mundo ou pais). Usa country=JP/BR/US/... "
        "para um pais. Nao inventes noticias. Resultados sao headlines RSS."
    )
    parameters: dict[str, Any] = {
        "type": "object",
        "properties": dict(_COUNTRY_PARAM),
        "required": [],
    }

    def __init__(
        self,
        feeds_csv: str = "",
        monitor_url: str = "",
        auto_open_monitors: bool = False,
    ) -> None:
        self._feeds_csv = feeds_csv
        self._monitor_url = monitor_url
        self._auto_open = auto_open_monitors

    async def execute(self, arguments: dict[str, Any]) -> SkillResult:
        profile, err = _resolve_or_error(arguments.get("country"))
        if err:
            return err
        assert profile is not None
        limit = int(arguments.get("limit") or 8)
        open_flag = _bool_arg(arguments.get("open_monitor"), self._auto_open)

        feeds = _feeds_for(profile, kind="world", override_csv=self._feeds_csv)
        headlines = fetch_rss_headlines(feeds, limit=limit)
        if not headlines:
            return SkillResult(
                success=False,
                content="",
                error=(
                    f"Nao consegui obter noticias para {profile.name_pt}. "
                    "Tenta mais tarde ou outro pais."
                ),
            )
        write_monitor_data("world", headlines, profile=profile)
        label = (
            "Briefing mundial (headlines):"
            if profile.code == "WW"
            else f"Briefing — {profile.name_pt} (headlines):"
        )
        summary = summarize_headlines(headlines, label)
        summary += "\nIsto e um resumo baseado apenas em headlines, nao no artigo completo."
        opened = False
        if open_flag:
            opened, open_msg = open_monitor("world", self._monitor_url)
            if opened:
                summary += f"\n({open_msg})"
            else:
                summary += f"\n(Nao consegui abrir o monitor: {open_msg})"
        else:
            summary += f"\n{_offer_monitor('world')}"
        return SkillResult(
            success=True,
            content=summary,
            metadata={
                "count": len(headlines),
                "country": profile.code,
                "kind": "news",
                "auto_open_monitor": "world",
                "opened": opened,
                "headlines_only": True,
            },
        )


class FinanceNewsSkill:
    name = "get_world_finance_news"
    description = (
        "Briefing financeiro / mercados por pais ou mundo (headlines, nao cotacoes). "
        "Nao inventes noticias nem precos."
    )
    parameters: dict[str, Any] = {
        "type": "object",
        "properties": dict(_COUNTRY_PARAM),
        "required": [],
    }

    def __init__(
        self,
        feeds_csv: str = "",
        monitor_url: str = "",
        auto_open_monitors: bool = False,
    ) -> None:
        self._feeds_csv = feeds_csv
        self._monitor_url = monitor_url
        self._auto_open = auto_open_monitors

    async def execute(self, arguments: dict[str, Any]) -> SkillResult:
        profile, err = _resolve_or_error(arguments.get("country"))
        if err:
            return err
        assert profile is not None
        limit = int(arguments.get("limit") or 8)
        open_flag = _bool_arg(arguments.get("open_monitor"), self._auto_open)

        feeds = _feeds_for(profile, kind="finance", override_csv=self._feeds_csv)
        headlines = fetch_rss_headlines(feeds, limit=limit)
        if not headlines:
            return SkillResult(
                success=False,
                content="",
                error=(
                    f"Nao consegui obter noticias financeiras para {profile.name_pt}."
                ),
            )
        write_monitor_data("finance", headlines, profile=profile)
        label = (
            "Briefing financeiro (headlines):"
            if profile.code == "WW"
            else f"Briefing financeiro — {profile.name_pt} (headlines):"
        )
        summary = (
            finance_context_line(profile)
            + "\n"
            + summarize_headlines(headlines, label)
            + "\nEstas sao noticias/headlines, nao cotacoes em tempo real."
        )
        opened = False
        if open_flag:
            opened, open_msg = open_monitor("finance", self._monitor_url)
            if opened:
                summary += f"\n({open_msg})"
            else:
                summary += f"\n(Nao consegui abrir o monitor: {open_msg})"
        else:
            summary += f"\n{_offer_monitor('finance')}"
        return SkillResult(
            success=True,
            content=summary,
            metadata={
                "count": len(headlines),
                "country": profile.code,
                "kind": "finance",
                "auto_open_monitor": "finance",
                "opened": opened,
                "headlines_only": True,
                "not_realtime_prices": True,
            },
        )


class CountryBriefingSkill:
    name = "get_country_briefing"
    description = (
        "Briefing combinado de noticias e financas para um pais (country obrigatorio)."
    )
    parameters: dict[str, Any] = {
        "type": "object",
        "properties": {
            "country": _COUNTRY_PARAM["country"],
            "limit": _COUNTRY_PARAM["limit"],
            "open_monitor": _COUNTRY_PARAM["open_monitor"],
        },
        "required": ["country"],
    }

    def __init__(
        self,
        world_feeds_csv: str = "",
        finance_feeds_csv: str = "",
        world_monitor_url: str = "",
        finance_monitor_url: str = "",
        auto_open_monitors: bool = False,
    ) -> None:
        self._news = WorldNewsSkill(
            world_feeds_csv, world_monitor_url, auto_open_monitors=False
        )
        self._finance = FinanceNewsSkill(
            finance_feeds_csv, finance_monitor_url, auto_open_monitors=False
        )
        self._auto_open = auto_open_monitors
        self._world_monitor_url = world_monitor_url

    async def execute(self, arguments: dict[str, Any]) -> SkillResult:
        country = str(arguments.get("country") or "").strip()
        if not country:
            return SkillResult(
                success=False,
                content="",
                error="Indica um pais (ex.: JP, Brasil). " + list_countries_text(),
            )
        profile = resolve_country(country)
        if profile is None:
            return SkillResult(
                success=False,
                content="",
                error=f"Pais desconhecido: {country}. " + list_countries_text(),
            )
        args = {
            "country": country,
            "limit": arguments.get("limit", 5),
            "open_monitor": False,
        }
        news = await self._news.execute(args)
        finance = await self._finance.execute(args)
        parts: list[str] = []
        if news.success:
            parts.append(news.content)
        else:
            parts.append(f"Noticias: {news.error or 'falhou'}")
        if finance.success:
            parts.append(finance.content)
        else:
            parts.append(f"Financas: {finance.error or 'falhou'}")

        open_flag = _bool_arg(arguments.get("open_monitor"), self._auto_open)
        opened = False
        if open_flag and news.success:
            opened, open_msg = open_monitor("world", self._world_monitor_url)
            if opened:
                parts.append(f"({open_msg})")
            else:
                parts.append(f"(Nao consegui abrir o monitor: {open_msg})")
        elif news.success or finance.success:
            parts.append(_offer_monitor("world"))

        ok = news.success or finance.success
        return SkillResult(
            success=ok,
            content="\n\n".join(parts),
            error=None if ok else "Nao consegui obter o briefing do pais.",
            metadata={
                "country": profile.code,
                "kind": "briefing",
                "news_ok": news.success,
                "finance_ok": finance.success,
                "opened": opened,
                "headlines_only": True,
            },
        )


class ListSupportedCountriesSkill:
    name = "list_supported_countries"
    description = (
        "Lista os paises para os quais a FRIDAY tem feeds de noticias/financas."
    )
    parameters: dict[str, Any] = {"type": "object", "properties": {}, "required": []}

    async def execute(self, arguments: dict[str, Any]) -> SkillResult:
        return SkillResult(
            success=True,
            content=list_countries_text(),
            metadata={"count": 9},
        )


class OpenWorldMonitorSkill:
    name = "open_world_monitor"
    description = (
        "Abre o painel/monitor de noticias (mundo ou ultimo pais briefado)."
    )
    parameters: dict[str, Any] = {
        "type": "object",
        "properties": {
            "country": _COUNTRY_PARAM["country"],
        },
        "required": [],
    }

    def __init__(self, monitor_url: str = "") -> None:
        self._monitor_url = monitor_url

    async def execute(self, arguments: dict[str, Any]) -> SkillResult:
        country = arguments.get("country")
        if country:
            profile, err = _resolve_or_error(country)
            if err:
                return err
            assert profile is not None
            write_monitor_data("world", [], profile=profile)
        ok, msg = open_monitor("world", self._monitor_url)
        if not ok:
            return SkillResult(success=False, content="", error=msg)
        return SkillResult(
            success=True,
            content=msg,
            metadata={
                "country": str(country or "WW"),
                "kind": "monitor",
                "monitor_type": "world",
                "opened": True,
            },
        )


class OpenFinanceMonitorSkill:
    name = "open_finance_world_monitor"
    description = "Abre o painel/monitor financeiro (mundo ou pais)."
    parameters: dict[str, Any] = {
        "type": "object",
        "properties": {
            "country": _COUNTRY_PARAM["country"],
        },
        "required": [],
    }

    def __init__(self, monitor_url: str = "") -> None:
        self._monitor_url = monitor_url

    async def execute(self, arguments: dict[str, Any]) -> SkillResult:
        country = arguments.get("country")
        if country:
            profile, err = _resolve_or_error(country)
            if err:
                return err
            assert profile is not None
            write_monitor_data("finance", [], profile=profile)
        ok, msg = open_monitor("finance", self._monitor_url)
        if not ok:
            return SkillResult(success=False, content="", error=msg)
        return SkillResult(
            success=True,
            content=msg,
            metadata={
                "country": str(country or "WW"),
                "kind": "monitor",
                "monitor_type": "finance",
                "opened": True,
            },
        )
