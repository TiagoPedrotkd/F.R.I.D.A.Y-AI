"""Domain routing for FRIDAY — leaf domains under 6 MoE pillars."""

from __future__ import annotations

import re
import unicodedata
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

# Fallback when domains.yaml is missing — patterns + pillar/subarea meta.
_DEFAULT_DOMAIN_META: dict[str, dict[str, Any]] = {
    "general": {"patterns": [], "pillar": None, "subarea": None},
    "productivity": {
        "patterns": [
            r"\bagenda\b",
            r"\breuniao\b",
            r"\bemail\b",
            r"\bcalendario\b",
            r"\bcompromisso\b",
            r"\bmeeting\b",
            r"\binbox\b",
        ],
        "pillar": "business",
        "subarea": "management_strategy",
    },
    "finance": {
        "patterns": [
            r"\bfinanc",
            r"\binvest",
            r"\borcamento\b",
            r"\bbudget\b",
            r"\bacoe?s\b",
            r"\bbitcoin\b",
            r"\bdinheiro\b",
            r"\bimposto",
        ],
        "pillar": "business",
        "subarea": "finance_economics",
    },
    "tech": {
        "patterns": [
            r"\bcodigo\b",
            r"\bpython\b",
            r"\bapi\b",
            r"\bserver\b",
            r"\bllm\b",
            r"\bgit\b",
            r"\bdocker\b",
            r"\bdebug",
        ],
        "pillar": "stem",
        "subarea": "software_devops",
    },
    "health_sport": {
        "patterns": [
            r"\btreino\b",
            r"\bworkout\b",
            r"\bexercic",
            r"\bfutebol\b",
            r"\bgym\b",
            r"\blesao\b",
        ],
        "pillar": "practical",
        "subarea": "games_entertainment",
    },
    "taekwondo": {
        "patterns": [
            r"\btaekwondo\b",
            r"\btkd\b",
            r"\bpoomsae\b",
            r"\bkick\b",
            r"\bcinto\b",
            r"\bdojang\b",
        ],
        "pillar": "practical",
        "subarea": "games_entertainment",
    },
    "nutrition": {
        "patterns": [
            r"\bcomida\b",
            r"\bdieta\b",
            r"\bnutric",
            r"\brefeicao\b",
            r"\bcalorias\b",
            r"\bproteina\b",
        ],
        "pillar": "life_health",
        "subarea": "clinical_medicine",
    },
    "sleep": {
        "patterns": [
            r"\bsono\b",
            r"\bdormir\b",
            r"\binsonia\b",
            r"\bsleep\b",
            r"\bcircadian",
        ],
        "pillar": "life_health",
        "subarea": "neuroscience_cognition",
    },
}

_DEFAULT_PILLARS: dict[str, dict[str, Any]] = {
    "stem": {"title": "Exatas, Tecnologia e Engenharia (STEM)", "subareas": {}},
    "life_health": {"title": "Ciencias Biologicas, Saude e Medicina", "subareas": {}},
    "humanities": {"title": "Humanidades e Ciencias Sociais", "subareas": {}},
    "language": {"title": "Linguagem, Comunicacao e Expressao", "subareas": {}},
    "business": {"title": "Negocios, Economia e Operacoes", "subareas": {}},
    "practical": {"title": "Conhecimento Pratico, Artes e Cotidiano", "subareas": {}},
}


def _normalize(text: str) -> str:
    text = text.casefold().strip()
    text = unicodedata.normalize("NFD", text)
    return "".join(c for c in text if unicodedata.category(c) != "Mn")


@lru_cache(maxsize=1)
def _load_raw() -> dict[str, Any]:
    path = Path(__file__).with_name("domains.yaml")
    if path.is_file():
        try:
            raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
            if isinstance(raw, dict) and (raw.get("domains") or raw.get("pillars")):
                return raw
        except Exception:
            pass
    return {
        "pillars": dict(_DEFAULT_PILLARS),
        "domains": {
            k: {
                "patterns": list(v["patterns"]),
                "pillar": v.get("pillar"),
                "subarea": v.get("subarea"),
            }
            for k, v in _DEFAULT_DOMAIN_META.items()
        },
    }


def clear_catalog_cache() -> None:
    """Test helper — invalidate cached YAML."""
    _load_raw.cache_clear()


def load_pillars() -> dict[str, dict[str, Any]]:
    raw = _load_raw()
    pillars = raw.get("pillars") or {}
    out: dict[str, dict[str, Any]] = {}
    for name, cfg in pillars.items():
        if isinstance(cfg, dict):
            out[str(name)] = cfg
        else:
            out[str(name)] = {"title": str(cfg), "subareas": {}}
    return out or dict(_DEFAULT_PILLARS)


def load_domain_meta() -> dict[str, dict[str, Any]]:
    """domain -> {patterns, pillar, subarea}."""
    raw = _load_raw()
    domains = raw.get("domains") or {}
    out: dict[str, dict[str, Any]] = {}
    for name, cfg in domains.items():
        key = str(name)
        if isinstance(cfg, dict):
            out[key] = {
                "patterns": list(cfg.get("patterns") or []),
                "pillar": cfg.get("pillar"),
                "subarea": cfg.get("subarea"),
            }
        elif isinstance(cfg, list):
            fallback = _DEFAULT_DOMAIN_META.get(key, {})
            out[key] = {
                "patterns": list(cfg),
                "pillar": fallback.get("pillar"),
                "subarea": fallback.get("subarea"),
            }
    if not out:
        return {
            k: {
                "patterns": list(v["patterns"]),
                "pillar": v.get("pillar"),
                "subarea": v.get("subarea"),
            }
            for k, v in _DEFAULT_DOMAIN_META.items()
        }
    # Ensure general exists
    out.setdefault("general", {"patterns": [], "pillar": None, "subarea": None})
    return out


def domain_pillar(domain: str) -> str | None:
    want = (domain or "").strip().casefold()
    for name, m in load_domain_meta().items():
        if name.casefold() == want:
            return m.get("pillar")  # type: ignore[no-any-return]
    return None


def domain_subarea(domain: str) -> str | None:
    want = (domain or "").strip().casefold()
    for name, m in load_domain_meta().items():
        if name.casefold() == want:
            return m.get("subarea")  # type: ignore[no-any-return]
    return None


def _load_catalog() -> dict[str, list[str]]:
    """Backward-compatible: domain -> patterns."""
    return {name: list(meta["patterns"]) for name, meta in load_domain_meta().items()}


def pillar_scores(ranked: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Aggregate leaf weights: pillar weight = max of children."""
    agg: dict[str, float] = {}
    for item in ranked:
        pillar = item.get("pillar")
        if not pillar:
            continue
        w = float(item.get("weight") or 0)
        agg[str(pillar)] = max(agg.get(str(pillar), 0.0), w)
    ordered = sorted(agg.items(), key=lambda x: x[1], reverse=True)
    titles = load_pillars()
    return [
        {
            "pillar": p,
            "weight": round(w, 3),
            "title": (titles.get(p) or {}).get("title") or p,
        }
        for p, w in ordered
    ]


def primary_pillar(ranked: list[dict[str, Any]]) -> str | None:
    scores = pillar_scores(ranked)
    if not scores:
        return None
    return str(scores[0]["pillar"])


def route_domains(
    query: str,
    *,
    domains_of_interest: list[str] | None = None,
    top_k: int = 3,
) -> list[dict[str, Any]]:
    """Return top_k leaf domains with weights and pillar/subarea."""
    norm = _normalize(query)
    meta = load_domain_meta()
    interest = {d.casefold() for d in (domains_of_interest or [])}
    scores: dict[str, float] = {name: 0.0 for name in meta}
    scores.setdefault("general", 0.15)

    for name, cfg in meta.items():
        if name == "general":
            continue
        hits = 0
        for pat in cfg.get("patterns") or []:
            if re.search(pat, norm):
                hits += 1
        if hits:
            scores[name] = min(1.0, 0.35 + 0.2 * hits)
        # Boost by leaf interest or matching pillar id
        pillar = (cfg.get("pillar") or "").casefold()
        if name.casefold() in interest or any(
            name.casefold() in i or i in name.casefold() for i in interest
        ):
            scores[name] = min(1.0, scores[name] + 0.15)
        elif pillar and pillar in interest:
            scores[name] = min(1.0, scores[name] + 0.1)

    if max(scores.values()) <= 0.15:
        scores["general"] = 0.55

    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    out: list[dict[str, Any]] = []
    for d, w in ranked:
        if w <= 0:
            continue
        cfg = meta.get(d) or {}
        item: dict[str, Any] = {"domain": d, "weight": round(w, 3)}
        if cfg.get("pillar"):
            item["pillar"] = cfg["pillar"]
        if cfg.get("subarea"):
            item["subarea"] = cfg["subarea"]
        out.append(item)
        if len(out) >= top_k:
            break
    return out


def format_routing_block(weights: list[dict[str, Any]]) -> str:
    if not weights:
        return "=== ROUTING ===\n- general: 1.0\nPrimary: general"
    lines = [
        "=== ROUTING ===",
        "MoE: six pillars (stem, life_health, humanities, language, business, practical).",
        "Active leaf domains (weights):",
    ]
    for item in weights:
        extra = ""
        if item.get("pillar"):
            extra = f" [{item['pillar']}"
            if item.get("subarea"):
                extra += f"/{item['subarea']}"
            extra += "]"
        lines.append(f"- {item['domain']}: {item['weight']}{extra}")

    p_scores = pillar_scores(weights)
    if p_scores:
        lines.append("Active pillars (max child weight):")
        for ps in p_scores[:3]:
            lines.append(f"- {ps['pillar']}: {ps['weight']} ({ps['title']})")

    lines.append("Prioritize the highest-weight leaf; blend secondary domains smoothly.")
    primary = weights[0]["domain"] if weights else "general"
    lines.append(f"Primary: {primary}")
    pp = primary_pillar(weights)
    if pp:
        lines.append(f"Pillar: {pp}")
    return "\n".join(lines)
