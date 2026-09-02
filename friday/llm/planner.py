"""Multi-step tool plans: regex fast-path + constrained LLM planner."""

from __future__ import annotations

import json
import logging
import re
import time
from dataclasses import dataclass
from typing import Any, Protocol

from friday.llm.intent_router import _normalize, match_skill_with_args

logger = logging.getLogger(__name__)

# Cost control: max LLM planner calls per process window
_planner_calls: list[float] = []
_PLANNER_WINDOW_S = 60.0


@dataclass
class PlanStep:
    skill: str
    arguments: dict[str, Any]
    reason: str = ""


class _Completer(Protocol):
    def create_completion(self, **kwargs: Any) -> Any: ...


_CALC_AND_SEARCH = re.compile(
    r"(calcula|calcular|quanto e|quanto é).{0,80}(pesquisa|procura|search)",
    re.I | re.S,
)
_SEARCH_AND_REMEMBER = re.compile(
    r"(pesquisa|procura|search).{0,120}(guarda|memoriza|remember)",
    re.I | re.S,
)
_DOCS_AND_WEB = re.compile(
    r"(manual|documento|docs?).{0,80}(e|depois|also).{0,40}(web|internet|pesquisa)",
    re.I | re.S,
)

_COMPOUND_HINT = re.compile(
    r"\b(e depois|depois|também|tambem|also|then|first|primeiro|em seguida|"
    r"e também|além disso|alem disso|seguido de|e em seguida)\b",
    re.I,
)

_MULTI_SKILL_HINT = re.compile(
    r"\b(pesquisa|procura|search|manual|docs?|calcula|noticia|notícia|"
    r"lembra|guarda|remember|abre o monitor|briefing)\b",
    re.I,
)


def plan_steps_regex(user_text: str) -> list[PlanStep]:
    """Deterministic compound intents (fast path)."""
    raw = (user_text or "").strip()
    if not raw:
        return []
    norm = _normalize(raw)
    steps: list[PlanStep] = []

    if _SEARCH_AND_REMEMBER.search(raw) or _SEARCH_AND_REMEMBER.search(norm):
        search = match_skill_with_args(raw)
        if search and search[0] in ("research_web", "search_web"):
            steps.append(PlanStep(search[0], search[1], "pesquisa"))
            topic = search[1].get("query") or raw
            steps.append(
                PlanStep(
                    "remember",
                    {"text": f"Pesquisa pedida: {topic}"},
                    "guardar pedido",
                )
            )
            return steps

    if _DOCS_AND_WEB.search(raw) or _DOCS_AND_WEB.search(norm):
        steps.append(PlanStep("search_docs", {"query": raw}, "docs internos"))
        steps.append(PlanStep("research_web", {"query": raw}, "web"))
        return steps

    if _CALC_AND_SEARCH.search(raw) or _CALC_AND_SEARCH.search(norm):
        from friday.llm.intent_router import _match_calculate

        calc_hit = _match_calculate(raw, norm)
        if calc_hit:
            steps.append(PlanStep(calc_hit[0], calc_hit[1], "calculo"))
        search = match_skill_with_args(
            re.sub(
                r"(calcula|calcular|quanto e|quanto é)[^.]{0,60}",
                "pesquisa ",
                raw,
                flags=re.I,
            )
        )
        if search and search[0] in ("research_web", "search_web"):
            steps.append(PlanStep(search[0], search[1], "pesquisa"))
        return steps if len(steps) >= 2 else []

    return []


def plan_steps(user_text: str) -> list[PlanStep]:
    """Regex-only entry (backwards compatible)."""
    return plan_steps_regex(user_text)


def _should_invoke_llm_planner(user_text: str, *, mode: str) -> bool:
    raw = (user_text or "").strip()
    if not raw:
        return False
    mode = (mode or "hint").casefold()
    if mode in ("off", "0", "false", "no"):
        return False
    if mode in ("hint", "compound"):
        return bool(_COMPOUND_HINT.search(raw))
    # aggressive: multi-skill vocabulary, long multi-clause, or compound hints
    if _COMPOUND_HINT.search(raw):
        return True
    skill_hits = len(_MULTI_SKILL_HINT.findall(raw))
    if skill_hits >= 2:
        return True
    if len(raw) >= 60 and ("," in raw or " e " in raw.casefold() or "?" in raw):
        return skill_hits >= 1
    return False


def _budget_allows(max_per_minute: int) -> bool:
    if max_per_minute <= 0:
        return True
    now = time.monotonic()
    while _planner_calls and now - _planner_calls[0] > _PLANNER_WINDOW_S:
        _planner_calls.pop(0)
    return len(_planner_calls) < max_per_minute


def plan_steps_llm(
    user_text: str,
    *,
    skill_names: list[str],
    client: _Completer,
    model_hint: str | None = None,
    max_per_minute: int = 12,
) -> list[PlanStep]:
    """
    Constrained LLM planner: returns 2–4 steps as JSON, validated against skill_names.
    Falls back to [] on any parse/validation failure.
    """
    raw = (user_text or "").strip()
    if not raw:
        return []
    if len(skill_names) < 2:
        return []
    if not _budget_allows(max_per_minute):
        logger.info("LLM planner skipped (rate budget)")
        return []

    allowed = sorted(set(skill_names))
    # Prefer a small skill subset to keep prompt cheap
    preferred = [
        s
        for s in allowed
        if s
        in {
            "research_web",
            "search_web",
            "search_docs",
            "fetch_url",
            "calculate",
            "remember",
            "recall",
            "get_world_news",
            "get_country_briefing",
            "get_current_datetime",
            "open_world_monitor",
        }
    ] or allowed[:16]

    system = (
        "Escribes um plano JSON curto para um assistente com ferramentas. "
        'Formato exacto: {"steps":[{"skill":"...","arguments":{},"reason":"..."}]} '
        "Usa APENAS skills da lista. Max 4 steps. Sem markdown. "
        "Se for uma unica accao obvia, devolve {\"steps\":[]}."
    )
    user = (
        f"Skills permitidas: {', '.join(preferred)}\n"
        f"Pedido do utilizador: {raw}"
    )
    try:
        _planner_calls.append(time.monotonic())
        kwargs: dict[str, Any] = {
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "max_tokens": 220,
            "temperature": 0.0,
        }
        if model_hint:
            kwargs["model"] = model_hint
        resp = client.create_completion(**kwargs)
        content = (resp.choices[0].message.content or "").strip()
    except Exception as exc:
        logger.debug("LLM planner failed: %s", exc)
        return []

    data = _parse_plan_json(content)
    if not data:
        return []
    steps: list[PlanStep] = []
    for item in data[:4]:
        if not isinstance(item, dict):
            continue
        skill = str(item.get("skill") or "").strip()
        if skill not in allowed:
            continue
        args = item.get("arguments") if isinstance(item.get("arguments"), dict) else {}
        reason = str(item.get("reason") or "")[:80]
        steps.append(PlanStep(skill=skill, arguments=args, reason=reason))
    return steps if len(steps) >= 2 else []


def plan_steps_hybrid(
    user_text: str,
    *,
    skill_names: list[str] | None = None,
    client: _Completer | None = None,
    mode: str = "hint",
    max_per_minute: int = 12,
) -> list[PlanStep]:
    """
    Regex first; LLM planner according to mode:
      off | hint (compound cues) | aggressive (multi-skill / long asks)
    Skips LLM if a single intent router skill already matches cleanly (cost control),
    unless mode=aggressive and compound cues are present.
    """
    hit = plan_steps_regex(user_text)
    if hit:
        return hit
    if client is None or not skill_names:
        return []

    single = match_skill_with_args(user_text or "")
    mode_l = (mode or "hint").casefold()
    if single and mode_l != "aggressive":
        return []
    if single and mode_l == "aggressive" and not _COMPOUND_HINT.search(user_text or ""):
        # Single clear skill + no compound language → skip planner
        return []

    if not _should_invoke_llm_planner(user_text or "", mode=mode_l):
        return []
    return plan_steps_llm(
        user_text or "",
        skill_names=skill_names,
        client=client,
        max_per_minute=max_per_minute,
    )


def _parse_plan_json(content: str) -> list[dict[str, Any]]:
    text = content.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        text = "\n".join(lines[1:-1] if len(lines) > 2 else lines).strip()
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", text, re.S)
        if not m:
            return []
        try:
            data = json.loads(m.group(0))
        except json.JSONDecodeError:
            return []
    if isinstance(data, dict):
        steps = data.get("steps")
        return list(steps) if isinstance(steps, list) else []
    if isinstance(data, list):
        return data
    return []
