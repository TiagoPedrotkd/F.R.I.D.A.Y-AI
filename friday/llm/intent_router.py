"""Deterministic skill routing for local LLMs that ignore tool calls."""

from __future__ import annotations

import re
import unicodedata

from friday.skills.news.countries import extract_country_from_utterance


def _normalize(text: str) -> str:
    text = text.casefold().strip()
    text = unicodedata.normalize("NFD", text)
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    return text


def _extract_url(text: str) -> str | None:
    match = re.search(r"https?://[^\s<>\"']+", text)
    return match.group(0).rstrip(".,);]") if match else None


def _extract_json_blob(text: str) -> str | None:
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        return text[start : end + 1]
    start = text.find("[")
    end = text.rfind("]")
    if start >= 0 and end > start:
        return text[start : end + 1]
    return None


def _extract_quoted_or_after(text: str, markers: tuple[str, ...]) -> str:
    """Text after a marker, or whole text stripped of the command phrase."""
    for m in markers:
        idx = text.casefold().find(m)
        if idx >= 0:
            return text[idx + len(m) :].strip(" :\"'")
    return text.strip()


def _any_pattern(norm: str, patterns: tuple[str, ...]) -> bool:
    return any(re.search(pat, norm) for pat in patterns)


_TIME_PATTERNS = (
    r"\bque horas\b",
    r"\bhoras sao\b",
    r"\bhora atual\b",
    r"\bhora actual\b",
    r"\bque horas sao\b",
    r"\bdiz[- ]?me as horas\b",
    r"\bqual e a hora\b",
    r"\bque horas tem\b",
    r"\bque dia\b",
    r"\bque data\b",
    r"\bdata de hoje\b",
    r"\bdia da semana\b",
    r"\bwhat time\b",
    r"\bcurrent time\b",
    r"\btoday'?s date\b",
    r"\bwhat(?:'s| is) today\b",
)

_NEWS_PATTERNS = (
    r"\bnoticias\b",
    r"\bnotícias\b",
    r"\bno mundo\b",
    r"\bmundial\b",
    r"\bpoe[- ]?me a par\b",
    r"\bbriefing mundial\b",
    r"\bbriefing\b",
    r"\bworld update\b",
    r"\bwhat(?:'s| is) happening\b",
    r"\bbrief me\b",
    r"\bo que (esta|está) a acontecer\b",
    r"\bo que perdi\b",
    r"\bo que se passa\b",
    r"\bheadlines\b",
    r"\bnews\b",
)

_FINANCE_PATTERNS = (
    r"\bfinanceir",
    r"\bmercados\b",
    r"\beconomia\b",
    r"\bfinance update\b",
    r"\bmarket news\b",
    r"\bfinancial briefing\b",
    r"\bbriefing financeiro\b",
    r"\bfinancas\b",
    r"\bfinanças\b",
    r"\bmarkets\b",
)

_OPEN_WORLD = (
    r"\babre o monitor mundial\b",
    r"\babre o monitor\b",
    r"\bworld monitor\b",
    r"\bmapa de acontecimentos\b",
    r"\bmostra[- ]?me o mapa\b",
    r"\bmonitor do\b",
    r"\bmonitor da\b",
)

_OPEN_FINANCE = (
    r"\babre o monitor financeiro\b",
    r"\bfinance monitor\b",
    r"\bpainel dos mercados\b",
    r"\bpainel financeiro\b",
    r"\bdashboard financeiro\b",
)

_CONTINUITY_FINANCE = (
    r"\be as financ",
    r"\be as finanç",
    r"\band (the )?financ",
    r"\band (the )?markets?\b",
    r"\bwhat about (the )?financ",
    r"\be os mercados\b",
)

_CONTINUITY_NEWS = (
    r"\be as noticia",
    r"\be as notícia",
    r"\band (the )?news\b",
    r"\bwhat about (the )?news\b",
)

_BRIEFING_PATTERNS = (
    r"\bnoticias e financ",
    r"\bnotícias e financ",
    r"\bnews and finance\b",
    r"\bcountry (briefing|update)\b",
    r"\bbriefing (completo|do pais|do país)\b",
)

_LIST_COUNTRIES_PATTERNS = (
    r"\bpaises suportados\b",
    r"\bpaíses suportados\b",
    r"\blista (os )?paises\b",
    r"\blista (os )?países\b",
    r"\bwhich countries\b",
    r"\bsupported countries\b",
)

_SEARCH_PATTERNS = (
    r"\bpesquisa\b",
    r"\bpesquisa na web\b",
    r"\bpesquisa na internet\b",
    r"\bprocura\b",
    r"\bprocura na web\b",
    r"\bprocura na internet\b",
    r"\bsearch\b",
    r"\bsearch the web\b",
    r"\bdescobre\b",
    r"\bprocura informacao\b",
    r"\bgoogla\b",
    r"\bno google\b",
)

_SYSTEM_PATTERNS = (
    r"\bsistema operativo\b",
    r"\binformacoes do computador\b",
    r"\binforma[cç][oõ]es do (pc|computador)\b",
    r"\bversao do python\b",
    r"\barquitectura\b",
    r"\bsystem information\b",
    r"\bshow me the system\b",
)

_WORD_PATTERNS = (
    r"\bconta (as )?palavras\b",
    r"\bquantas palavras\b",
    r"\bconta (os )?caracteres\b",
    r"\bquantas linhas\b",
    r"\bcount the words\b",
    r"\bword count\b",
)

_JSON_PATTERNS = (
    r"\bformata (este )?json\b",
    r"\borganiza (este )?json\b",
    r"\bvalida (este )?json\b",
    r"\bpretty[- ]?print\b",
    r"\bjson legivel\b",
)

_JOKE_PATTERNS = (
    r"\bpiada\b",
    r"\bjoke\b",
    r"\bconta[- ]?(me )?(uma )?piada\b",
    r"\bdiz[- ]?(me )?(uma )?piada\b",
    r"\balgo engra[cç]ado\b",
    r"\bfaz[- ]?me rir\b",
)

_REMEMBER_PATTERNS = (
    r"\bguarda (esta |isso |a )?conclus",
    r"\bguarda (isto|isso|esta ideia)\b",
    r"\bguarda na memoria\b",
    r"\bguarda na memória\b",
    r"\bmemoriza\b",
    r"\blembr[ae]-?te (disso|disto|que)\b",
    r"\blembr[ae] que\b",
    r"\bnao te esquecas que\b",
    r"\bnão te esqueças que\b",
    r"\bremember (this|that)\b",
    r"\bsave this\b",
)

_RECALL_PATTERNS = (
    r"\blembras?-?te\b",
    r"\bo que (guardamos|guardaste|memor)\b",
    r"\bo que te pedi para lembrar\b",
    r"\bvolta ao assunto (anterior|guardado)\b",
    r"\brecall\b",
    r"\bwhat did (we|i) save\b",
)

_FETCH_INTENT = r"\b(ler|le|consulta|resume|analisa|read|o que diz|fetch)\b"

_TZ_FROM_TEXT = (
    (r"\bseul\b|\bseoul\b|\bcoreia\b", "Asia/Seoul"),
    (r"\bportugal\b|\blisboa\b|\blisbon\b", "Europe/Lisbon"),
    (r"\blondres\b|\blondon\b", "Europe/London"),
    (r"\bnova iorque\b|\bnew york\b", "America/New_York"),
)


def _match_datetime(norm: str) -> tuple[str, dict] | None:
    if not _any_pattern(norm, _TIME_PATTERNS):
        return None
    args: dict = {}
    for tz_pat, tz in _TZ_FROM_TEXT:
        if re.search(tz_pat, norm):
            args["timezone"] = tz
            break
    return "get_current_datetime", args


def _match_fetch(raw: str, norm: str, url: str | None) -> tuple[str, dict] | None:
    if not url:
        return None
    wants_fetch = bool(re.search(_FETCH_INTENT, norm)) or raw.strip() == url
    if wants_fetch or len(raw) < len(url) + 8:
        return "fetch_url", {"url": url}
    return None


def _match_search(raw: str, norm: str) -> tuple[str, dict] | None:
    if not _any_pattern(norm, _SEARCH_PATTERNS):
        return None
    query = _extract_quoted_or_after(
        raw,
        (
            "pesquisa na web ",
            "pesquisa na internet ",
            "procura na web ",
            "procura na internet ",
            "pesquisa ",
            "pesquisa o ",
            "pesquisa a ",
            "procura ",
            "search ",
            "search the web for ",
        ),
    )
    return "search_web", {"query": query or raw}


def _match_json(raw: str, norm: str) -> tuple[str, dict] | None:
    if not _any_pattern(norm, _JSON_PATTERNS):
        return None
    return "format_json", {"json_text": _extract_json_blob(raw) or ""}


def _match_word_count(raw: str, norm: str) -> tuple[str, dict] | None:
    if not _any_pattern(norm, _WORD_PATTERNS):
        return None
    text = _extract_quoted_or_after(
        raw,
        (
            "conta as palavras ",
            "conta as palavras deste texto ",
            "conta as palavras: ",
            "count the words ",
            "word count ",
        ),
    )
    if text.casefold() in norm and len(text) < 40 and "palavra" in text.casefold():
        text = ""
    return "word_count", {"text": text}


def _match_remember(raw: str, norm: str) -> tuple[str, dict] | None:
    if not _any_pattern(norm, _REMEMBER_PATTERNS):
        return None
    text = _extract_quoted_or_after(
        raw,
        (
            "guarda esta conclusao: ",
            "guarda esta conclusão: ",
            "guarda isto: ",
            "guarda isso: ",
            "guarda na memoria: ",
            "guarda na memória: ",
            "memoriza: ",
            "memoriza que ",
            "lembra que ",
            "lembra-te que ",
            "remember this: ",
            "guarda ",
        ),
    )
    return "remember", {"text": text or raw}


def _match_country_routes(norm: str) -> tuple[str, dict] | None:
    country = extract_country_from_utterance(norm)
    country_args = {"country": country.code} if country else {}

    if _any_pattern(norm, _LIST_COUNTRIES_PATTERNS):
        return "list_supported_countries", {}
    if country and _any_pattern(norm, _BRIEFING_PATTERNS):
        return "get_country_briefing", {"country": country.code}
    # Continuity utterances — country filled by ToolRunner from session
    if _any_pattern(norm, _CONTINUITY_FINANCE):
        return "get_world_finance_news", dict(country_args)
    if _any_pattern(norm, _CONTINUITY_NEWS):
        return "get_world_news", dict(country_args)
    if _any_pattern(norm, _OPEN_FINANCE) or (
        country and re.search(r"\bpainel financeiro\b|\bmonitor financeiro\b", norm)
    ):
        return "open_finance_world_monitor", dict(country_args)
    if _any_pattern(norm, _OPEN_WORLD):
        return "open_world_monitor", dict(country_args)
    if _any_pattern(norm, _FINANCE_PATTERNS):
        return "get_world_finance_news", dict(country_args)
    if _any_pattern(norm, _NEWS_PATTERNS):
        return "get_world_news", dict(country_args)
    if country and re.search(r"\b(passa|acontece|update|situacao|situação)\b", norm):
        return "get_world_news", {"country": country.code}
    return None


def _match_rag(raw: str) -> tuple[str, dict] | None:
    from friday_llm.rag.router import route_query

    decision = route_query(raw)
    if decision.route == "rag":
        return "search_docs", {"query": raw}
    return None


def match_skill_with_args(user_text: str) -> tuple[str, dict] | None:
    """
    Return (skill_name, arguments) if utterance maps to a known skill.
    """
    raw = user_text.strip()
    norm = _normalize(raw)

    hit = _match_country_routes(norm)
    if hit:
        return hit

    hit = _match_datetime(norm)
    if hit:
        return hit

    url = _extract_url(raw)
    hit = _match_fetch(raw, norm, url)
    if hit and (re.search(_FETCH_INTENT, norm) or raw.strip() == url):
        return hit

    hit = _match_rag(raw)
    if hit:
        return hit

    hit = _match_search(raw, norm)
    if hit:
        return hit
    if _any_pattern(norm, _SYSTEM_PATTERNS):
        return "get_system_info", {}
    hit = _match_json(raw, norm)
    if hit:
        return hit
    hit = _match_word_count(raw, norm)
    if hit:
        return hit
    hit = _match_remember(raw, norm)
    if hit:
        return hit
    if _any_pattern(norm, _RECALL_PATTERNS):
        return "recall", {"query": raw}
    if _any_pattern(norm, _JOKE_PATTERNS):
        return "tell_joke", {}

    return _match_fetch(raw, norm, url)


def match_skill(user_text: str) -> str | None:
    """Return skill name only (backwards compatible)."""
    hit = match_skill_with_args(user_text)
    return hit[0] if hit else None
