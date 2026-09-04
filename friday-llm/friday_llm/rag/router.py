"""Knowledge router: weights vs RAG vs live tools."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

Route = Literal["model", "rag", "tool", "clarify"]


@dataclass
class RouteDecision:
    route: Route
    reason: str
    suggested_tool: str | None = None


_TIME = re.compile(
    r"\b(horas?|hora|que dia|que data|data de hoje|dia da semana|what time|today'?s date)\b",
    re.I,
)
_NEWS = re.compile(
    r"\b(not[ií]cias?|news|headlines|poe[- ]?me a par|briefing|o que se passa)\b",
    re.I,
)
_FINANCE = re.compile(
    r"\b(finan[cç]as?|mercados?|markets?|cota[cç][oõ]es?|stock price|economia)\b",
    re.I,
)
_SEARCH = re.compile(
    r"\b(pesquisa|procura|search|google|googla|na web|na internet|vers[aã]o mais recente)\b",
    re.I,
)
_URL = re.compile(r"https?://\S+", re.I)
_DOC = re.compile(
    r"\b("
    r"documento|documentacao|documentação|manual|pdf|readme|"
    r"segundo o (ficheiro|documento|manual)|"
    r"na documentacao|na documentação|"
    r"documentacao do projeto|documentação do projeto|"
    r"docs? do (repo|projecto|projeto)|"
    r"manual interno|ficheiros? internos?|"
    r"documentos internos|arquivo interno|"
    r"o que diz (o |a )?(manual|documento|documentacao|documentação|readme)|"
    r"pesquisa nos documentos|procura nos documentos|"
    r"internal doc|"
    # Setup / ops facts (prefer RAG over inventing)
    r"lm[_ ]?studio|agent[- ]?api|porta\s*(8090|5173|1234|8080)|"
    r"rag[_ ]?chroma|friday_docs|search_docs|"
    r"wake[- ]?word|openwakeword|hey jarvis|"
    r"whisper|piper|"
    r"lm_studio_model|\.env|"
    r"como (correr|arrancar|ligar|configurar) (o |a )?(agent|api|ui|web|friday)|"
    r"onde fica (o |a )?(indice|índice|index|pasta)|"
    r"tres camadas|três camadas|cpt.*sft.*rag|camadas de conhecimento"
    r")\b",
    re.I,
)
_NOW = re.compile(r"\b(agora|neste segundo|tempo real|right now|live)\b", re.I)


def route_query(text: str) -> RouteDecision:
    t = text.strip()
    if _URL.search(t):
        return RouteDecision("tool", "URL provided → fetch_url", "fetch_url")
    if _TIME.search(t):
        return RouteDecision("tool", "Datetime requires live tool", "get_current_datetime")
    if _FINANCE.search(t) and _NOW.search(t):
        return RouteDecision(
            "tool",
            "Live prices/news → tools (not weights/archive)",
            "get_world_finance_news",
        )
    if _NEWS.search(t):
        return RouteDecision("tool", "News → get_world_news", "get_world_news")
    if _FINANCE.search(t):
        return RouteDecision("tool", "Finance headlines → tool", "get_world_finance_news")
    if _SEARCH.search(t):
        return RouteDecision("tool", "Current web info → search_web", "search_web")
    if _DOC.search(t):
        return RouteDecision("rag", "Exact/updatable document → RAG with sources")
    if len(t.split()) < 3 and t.endswith("?"):
        return RouteDecision("clarify", "Too vague — ask a short clarification")
    return RouteDecision("model", "Stable general knowledge may use model weights")
