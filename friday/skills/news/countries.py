"""Country profiles for news / finance briefings (ISO 3166-1 alpha-2)."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass


@dataclass(frozen=True)
class CountryProfile:
    code: str
    name_pt: str
    names: tuple[str, ...]  # aliases for matching (already normalized-ish)
    timezone: str
    currency: str
    market_name: str
    lat_lon: tuple[float, float]
    map_zoom: int
    news_feeds: tuple[str, ...]
    finance_feeds: tuple[str, ...]
    region: str = "world"


# Stable public RSS (validated 2026-08). Prefer BBC regional + a few locals.
_BBC_WORLD = "https://feeds.bbci.co.uk/news/world/rss.xml"
_BBC_EUROPE = "https://feeds.bbci.co.uk/news/world/europe/rss.xml"
_BBC_ASIA = "https://feeds.bbci.co.uk/news/world/asia/rss.xml"
_BBC_US = "https://feeds.bbci.co.uk/news/world/us_and_canada/rss.xml"
_BBC_LATAM = "https://feeds.bbci.co.uk/news/world/latin_america/rss.xml"
_BBC_UK = "https://feeds.bbci.co.uk/news/uk/rss.xml"
_BBC_BIZ = "https://feeds.bbci.co.uk/news/business/rss.xml"
_CNBC = "https://www.cnbc.com/id/100003114/device/rss/rss.html"
_DW_WORLD = "https://rss.dw.com/xml/rss-en-world"
_NPR = "https://feeds.npr.org/1001/rss.xml"
_JT = "https://www.japantimes.co.jp/feed/"
_FOLHA = "https://feeds.folha.uol.com.br/mundo/rss091.xml"
_OBSERVADOR = "https://observador.pt/feed/"
# Country-specific finance RSS (validated 2026-08)
_ECO_PT = "https://eco.sapo.pt/feed/"
_JN_PT = "https://www.jornaldenegocios.pt/rss"
_RTP_ECO_PT = "https://www.rtp.pt/noticias/rss/economia"
_ELP_ES = "https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/section/economia/portada"
_EXP_ES = "https://www.expansion.com/rss/economia.xml"
_LM_FR = "https://www.lemonde.fr/economie/rss_full.xml"
_SPIEGEL_DE = "https://www.spiegel.de/wirtschaft/index.rss"
_INFOMONEY_BR = "https://www.infomoney.com.br/feed/"
_NIKKEI = "https://asia.nikkei.com/rss/feed/nar"

COUNTRIES: dict[str, CountryProfile] = {
    "WW": CountryProfile(
        code="WW",
        name_pt="Mundo",
        names=("mundo", "world", "global", "mundial"),
        timezone="UTC",
        currency="",
        market_name="Mercados globais",
        lat_lon=(20.0, 0.0),
        map_zoom=2,
        news_feeds=(_BBC_WORLD, "https://feeds.bbci.co.uk/news/rss.xml"),
        finance_feeds=(_BBC_BIZ, _CNBC),
        region="world",
    ),
    "PT": CountryProfile(
        code="PT",
        name_pt="Portugal",
        names=("portugal", "portugues", "lisboa", "lisbon"),
        timezone="Europe/Lisbon",
        currency="EUR",
        market_name="Euronext Lisboa / PSI",
        lat_lon=(38.72, -9.14),
        map_zoom=6,
        news_feeds=(_OBSERVADOR, _BBC_EUROPE),
        finance_feeds=(_ECO_PT, _JN_PT, _RTP_ECO_PT),
        region="europe",
    ),
    "ES": CountryProfile(
        code="ES",
        name_pt="Espanha",
        names=("espanha", "spain", "espana", "madrid"),
        timezone="Europe/Madrid",
        currency="EUR",
        market_name="IBEX 35",
        lat_lon=(40.42, -3.70),
        map_zoom=6,
        news_feeds=(_BBC_EUROPE, _DW_WORLD),
        finance_feeds=(_EXP_ES, _ELP_ES),
        region="europe",
    ),
    "FR": CountryProfile(
        code="FR",
        name_pt="Franca",
        names=("franca", "france", "paris"),
        timezone="Europe/Paris",
        currency="EUR",
        market_name="CAC 40",
        lat_lon=(48.86, 2.35),
        map_zoom=6,
        news_feeds=(_BBC_EUROPE, _DW_WORLD),
        finance_feeds=(_LM_FR, _BBC_BIZ),
        region="europe",
    ),
    "DE": CountryProfile(
        code="DE",
        name_pt="Alemanha",
        names=("alemanha", "germany", "deutschland", "berlin"),
        timezone="Europe/Berlin",
        currency="EUR",
        market_name="DAX",
        lat_lon=(52.52, 13.40),
        map_zoom=6,
        news_feeds=(_DW_WORLD, _BBC_EUROPE),
        finance_feeds=(_SPIEGEL_DE, _BBC_BIZ),
        region="europe",
    ),
    "GB": CountryProfile(
        code="GB",
        name_pt="Reino Unido",
        names=(
            "reino unido",
            "inglaterra",
            "uk",
            "britain",
            "england",
            "london",
            "londres",
            "great britain",
        ),
        timezone="Europe/London",
        currency="GBP",
        market_name="FTSE 100",
        lat_lon=(51.50, -0.12),
        map_zoom=6,
        news_feeds=(_BBC_UK, _BBC_EUROPE),
        finance_feeds=(_BBC_BIZ,),
        region="europe",
    ),
    "US": CountryProfile(
        code="US",
        name_pt="Estados Unidos",
        names=(
            "estados unidos",
            "eua",
            "usa",
            "united states",
            "america",
            "washington",
            "nova iorque",
            "new york",
        ),
        timezone="America/New_York",
        currency="USD",
        market_name="S&P 500 / Nasdaq",
        lat_lon=(38.90, -77.04),
        map_zoom=4,
        news_feeds=(_BBC_US, _NPR),
        finance_feeds=(_CNBC, _BBC_BIZ),
        region="americas",
    ),
    "BR": CountryProfile(
        code="BR",
        name_pt="Brasil",
        names=("brasil", "brazil", "brasilia", "sao paulo"),
        timezone="America/Sao_Paulo",
        currency="BRL",
        market_name="Bovespa",
        lat_lon=(-15.79, -47.88),
        map_zoom=4,
        news_feeds=(_FOLHA, _BBC_LATAM),
        finance_feeds=(_INFOMONEY_BR, _BBC_LATAM),
        region="americas",
    ),
    "JP": CountryProfile(
        code="JP",
        name_pt="Japao",
        names=("japao", "japan", "tokyo", "toquio", "nippon"),
        timezone="Asia/Tokyo",
        currency="JPY",
        market_name="Nikkei 225",
        lat_lon=(35.68, 139.69),
        map_zoom=5,
        news_feeds=(_JT, _BBC_ASIA),
        finance_feeds=(_NIKKEI, _BBC_BIZ),
        region="asia",
    ),
}

PILOT_CODES = ("WW", "PT", "ES", "FR", "DE", "GB", "US", "BR", "JP")


def _normalize_key(text: str) -> str:
    text = text.casefold().strip()
    text = unicodedata.normalize("NFD", text)
    return "".join(c for c in text if unicodedata.category(c) != "Mn")


def get_profile(code: str | None) -> CountryProfile | None:
    if not code or not str(code).strip():
        return COUNTRIES["WW"]
    key = str(code).strip().upper()
    if key in ("UK", "GB"):
        key = "GB"
    if key in ("USA",):
        key = "US"
    return COUNTRIES.get(key)


def resolve_country(text: str | None) -> CountryProfile | None:
    """Resolve ISO code or country name to a profile. Empty → WW. Unknown → None."""
    if text is None or not str(text).strip():
        return COUNTRIES["WW"]
    raw = str(text).strip()
    upper = raw.upper()
    if upper == "UK":
        upper = "GB"
    if upper == "USA":
        upper = "US"
    if upper in COUNTRIES:
        return COUNTRIES[upper]

    norm = _normalize_key(raw)
    if norm in ("ww", "mundo", "world", "global", "mundial"):
        return COUNTRIES["WW"]

    best: CountryProfile | None = None
    best_len = 0
    for profile in COUNTRIES.values():
        if profile.code == "WW":
            continue
        for alias in profile.names:
            alias_n = _normalize_key(alias)
            if alias_n == norm or (len(alias_n) > 3 and alias_n in norm):
                if len(alias_n) > best_len:
                    best = profile
                    best_len = len(alias_n)
    return best


def extract_country_from_utterance(norm_text: str) -> CountryProfile | None:
    """Find a country mentioned in already-normalized utterance text."""
    best: CountryProfile | None = None
    best_len = 0
    for profile in COUNTRIES.values():
        if profile.code == "WW":
            continue
        for alias in profile.names:
            alias_n = _normalize_key(alias)
            if not alias_n:
                continue
            # Word-boundary-ish for short aliases
            if len(alias_n) <= 3:
                if re.search(rf"\b{re.escape(alias_n)}\b", norm_text):
                    if len(alias_n) > best_len:
                        best = profile
                        best_len = len(alias_n)
            elif alias_n in norm_text:
                if len(alias_n) > best_len:
                    best = profile
                    best_len = len(alias_n)
    return best


def list_countries_text() -> str:
    lines = [
        f"- {p.code}: {p.name_pt} ({p.market_name or 'n/d'})"
        for code in PILOT_CODES
        if (p := COUNTRIES[code])
    ]
    return "Paises suportados:\n" + "\n".join(lines)


def finance_context_line(profile: CountryProfile) -> str:
    if profile.code == "WW":
        return (
            "Contexto: mercados globais. "
            "Isto nao e aconselhamento financeiro; sem cotacoes em tempo real."
        )
    parts = [f"Pais: {profile.name_pt}", f"foco {profile.market_name}"]
    if profile.currency:
        parts.append(f"moeda {profile.currency}")
    return (
        "Contexto: "
        + "; ".join(parts)
        + ". Isto nao e aconselhamento financeiro; sem cotacoes em tempo real."
    )
