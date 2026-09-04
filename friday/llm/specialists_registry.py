"""Specialist LoRA registry — domain → adapter path (+ pillar from catalog)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from friday.config import Settings, get_settings


def specialists_root(settings: Settings | None = None) -> Path:
    settings = settings or get_settings()
    # friday-llm/checkpoints/specialists relative to repo
    repo = Path(settings.prefs_dir).resolve().parents[1]
    return repo / "friday-llm" / "checkpoints" / "specialists"


def _catalog_enrichment(domain: str) -> dict[str, Any]:
    try:
        from friday.llm.domain_router import domain_pillar, domain_subarea, load_pillars

        pillar = domain_pillar(domain)
        subarea = domain_subarea(domain)
        title = None
        if pillar:
            title = (load_pillars().get(pillar) or {}).get("title")
        out: dict[str, Any] = {}
        if pillar:
            out["pillar"] = pillar
        if subarea:
            out["subarea"] = subarea
        if title:
            out["pillar_title"] = title
        return out
    except Exception:
        return {}


def list_specialists(settings: Settings | None = None) -> list[dict[str, Any]]:
    root = specialists_root(settings)
    root.mkdir(parents=True, exist_ok=True)
    items: list[dict[str, Any]] = []
    for domain_dir in sorted(root.iterdir() if root.is_dir() else []):
        if not domain_dir.is_dir() or domain_dir.name.startswith("."):
            continue
        adapter = domain_dir / "adapter"
        meta_path = domain_dir / "meta.json"
        meta: dict[str, Any] = {}
        if meta_path.is_file():
            try:
                meta = json.loads(meta_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                meta = {}
        item: dict[str, Any] = {
            "domain": domain_dir.name,
            "adapter_path": str(adapter) if adapter.is_dir() else None,
            "ready": adapter.is_dir()
            and (adapter / "adapter_config.json").is_file(),
            "meta": meta,
        }
        enrich = _catalog_enrichment(domain_dir.name)
        # meta.json overrides catalog when explicitly set
        if meta.get("pillar"):
            item["pillar"] = meta["pillar"]
        elif enrich.get("pillar"):
            item["pillar"] = enrich["pillar"]
        if meta.get("subarea"):
            item["subarea"] = meta["subarea"]
        elif enrich.get("subarea"):
            item["subarea"] = enrich["subarea"]
        if enrich.get("pillar_title"):
            item["pillar_title"] = enrich["pillar_title"]
        items.append(item)
    return items


def resolve_specialist(domain: str, settings: Settings | None = None) -> dict[str, Any] | None:
    domain = (domain or "").strip().casefold()
    if not domain or domain == "general":
        return None
    for item in list_specialists(settings):
        if item["domain"].casefold() == domain:
            return item
    return None


def format_specialist_hint(item: dict[str, Any] | None) -> str:
    if not item or not item.get("ready"):
        return ""
    pillar_line = ""
    if item.get("pillar"):
        title = item.get("pillar_title") or item["pillar"]
        pillar_line = f"Pillar: {item['pillar']} ({title})\n"
        if item.get("subarea"):
            pillar_line += f"Subarea: {item['subarea']}\n"
    return (
        f"=== SPECIALIST ===\n"
        f"Active domain pack: {item['domain']}\n"
        f"{pillar_line}"
        f"Adapter: {item.get('adapter_path')}\n"
        f"Use domain expertise in tone and recommendations. "
        f"LM Studio may need this adapter loaded for weight-level effect; "
        f"otherwise treat as stylistic specialist instructions."
    )
