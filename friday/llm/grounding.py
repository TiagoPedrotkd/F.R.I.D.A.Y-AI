"""Web source-required grounding helpers + excerpt-bound claim checks."""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import urlparse

_FACTUAL_PATTERNS = (
    r"\b(pesquisa|pesquisar|procura|procurar|search|google)\b",
    r"\b(versao mais recente|versão mais recente|latest version|changelog)\b",
    r"\b(quanto custa|pre[cç]o (de|do|da)|current price)\b",
    r"\b(who is|quem (e|é) o|quem (e|é) a)\b.{0,40}\b(ceo|presidente|ministro)\b",
    r"\b(noticias?|notícias?|headlines)\b",
    r"https?://",
    r"\b(lookup|look up)\b",
)


_SOURCE_URL_RE = re.compile(r"https?://[^\s\]\)\"'<>]+", re.I)
_TOKEN_RE = re.compile(r"[a-z0-9àáâãéêíóôõúç]{4,}", re.I)
_STOP = frozenset(
    {
        "para",
        "como",
        "sobre",
        "this",
        "that",
        "with",
        "from",
        "have",
        "will",
        "sendo",
        "onde",
        "quando",
        "porque",
        "which",
        "there",
        "their",
        "about",
    }
)


def needs_web_grounding(user_text: str) -> bool:
    """Heuristic: current/external facts should be tool-grounded."""
    lowered = user_text.casefold()
    return any(re.search(pat, lowered) for pat in _FACTUAL_PATTERNS)


def extract_urls_from_tool_meta(metadata: dict[str, Any] | None) -> list[str]:
    urls: list[str] = []
    if not metadata:
        return urls
    if metadata.get("url"):
        urls.append(str(metadata["url"]))
    for r in metadata.get("results") or []:
        if isinstance(r, dict) and r.get("url"):
            urls.append(str(r["url"]))
    seen: set[str] = set()
    out: list[str] = []
    for u in urls:
        if u not in seen:
            seen.add(u)
            out.append(u)
    return out


def extract_cited_urls(reply_text: str) -> list[str]:
    return _SOURCE_URL_RE.findall(reply_text or "")


def snippets_from_meta(metadata: dict[str, Any] | None) -> list[str]:
    """Collect textual evidence from tool metadata for claim checks."""
    if not metadata:
        return []
    out: list[str] = []
    for key in ("content", "snippet", "text", "summary"):
        val = metadata.get(key)
        if isinstance(val, str) and val.strip():
            out.append(val)
    for r in metadata.get("results") or []:
        if not isinstance(r, dict):
            continue
        for key in ("snippet", "content", "text", "title"):
            val = r.get(key)
            if isinstance(val, str) and val.strip():
                out.append(val)
    return out


def _tokens(text: str) -> set[str]:
    return {
        t
        for t in _TOKEN_RE.findall((text or "").casefold())
        if t not in _STOP and not t.isdigit()
    }


def excerpt_support_score(reply_text: str, snippets: list[str]) -> dict[str, Any]:
    """
    Measure how much of the reply vocabulary is supported by tool excerpts.
    Not full NLI — token overlap per sentence as a cheap claim check.
    """
    sentences = [
        s.strip()
        for s in re.split(r"[.!?]\s+|\n+", reply_text or "")
        if len(s.strip()) > 20
    ]
    if not sentences or not snippets:
        return {
            "support": 0.0,
            "supported_sentences": 0,
            "total_sentences": len(sentences),
            "unsupported": [],
        }

    corpus = _tokens(" ".join(snippets))
    if not corpus:
        return {
            "support": 0.0,
            "supported_sentences": 0,
            "total_sentences": len(sentences),
            "unsupported": sentences[:5],
        }

    supported = 0
    unsupported: list[str] = []
    for sent in sentences:
        st = _tokens(sent)
        if not st:
            continue
        overlap = len(st & corpus) / max(1, len(st))
        if overlap >= 0.28:
            supported += 1
        else:
            unsupported.append(sent[:160])

    total = max(1, supported + len(unsupported))
    support = supported / total
    return {
        "support": round(support, 3),
        "supported_sentences": supported,
        "total_sentences": supported + len(unsupported),
        "unsupported": unsupported[:5],
    }


def grounding_score(
    reply_text: str,
    *,
    tool_urls: list[str],
    used_web_tools: bool,
    snippets: list[str] | None = None,
) -> dict[str, Any]:
    """
    Score how well the reply is grounded in tool sources + excerpt overlap.
    """
    cited = extract_cited_urls(reply_text)
    tool_hosts = {_host(u) for u in tool_urls if u}
    cited_hosts = {_host(u) for u in cited if u}
    overlap = tool_hosts & cited_hosts if tool_hosts else set()

    excerpt = excerpt_support_score(reply_text, snippets or [])
    support = float(excerpt.get("support") or 0.0)
    has_snippets = bool(snippets)

    if used_web_tools and tool_urls:
        if overlap or cited:
            score = 1.0 if overlap else 0.7
        else:
            score = 0.4
        if has_snippets:
            score = round(0.65 * score + 0.35 * support, 3)
            if support < 0.25 and len(reply_text or "") > 80 and not overlap:
                score = min(score, 0.45)
        else:
            score = round(score, 3)
    elif used_web_tools:
        score = round(0.3 * 0.5 + 0.5 * support, 3) if has_snippets else 0.3
    else:
        score = 0.0

    grounded = score >= 0.7 or (bool(overlap) and score >= 0.65)
    if used_web_tools and has_snippets and support < 0.25 and not overlap:
        grounded = False

    inventing = bool(
        used_web_tools
        and has_snippets
        and support < 0.2
        and len(excerpt.get("unsupported") or []) >= 2
        and not overlap
    )

    return {
        "score": score,
        "tool_urls": tool_urls,
        "cited_urls": cited,
        "overlap_hosts": sorted(overlap),
        "used_web_tools": used_web_tools,
        "grounded": grounded,
        "excerpt": excerpt,
        "inventing": inventing,
    }


def _host(url: str) -> str:
    try:
        return (urlparse(url).netloc or "").casefold()
    except Exception:
        return ""


SOURCE_REQUIRED_INSTRUCTION = """\
## Modo source-required (activo)
Para factos actuais ou externos: chama research_web (ou search_web + fetch_url),
depois responde so com base nessas fontes e menciona URLs. Cada afirmação
factual deve reflectir excertos das ferramentas. Se as ferramentas
falharem ou nao houver fontes, diz explicitamente que nao podes confirmar —
nunca inventes.
"""


NO_SOURCE_REFUSAL_PT = (
    "Nao consegui confirmar isto com fontes actuais. "
    "Sem resultados de pesquisa ou pagina, nao invento factos. "
    "Quer que tente outra consulta?"
)
NO_SOURCE_REFUSAL_EN = (
    "I could not confirm this from current sources. "
    "Without search or page results, I will not invent facts. "
    "Shall I try another query?"
)

INVENTED_REFUSAL_PT = (
    "Encontrei fontes, mas a resposta nao ficou suficientemente alinhada "
    "com os excertos. Preferi nao inventar. Quer que reformule com citacoes?"
)
INVENTED_REFUSAL_EN = (
    "I found sources, but the draft was not well supported by the excerpts. "
    "I prefer not to invent. Shall I retry with tighter citations?"
)
