"""Lightweight knowledge graph over RAG corpus (no Neo4j)."""

from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any

from friday.config import Settings, get_settings

_ARROW = re.compile(
    r"(.{2,60}?)\s*(?:→|->|depende de|depends on)\s*(.{2,60}?)(?:\n|$)",
    re.I,
)
_MD_LINK = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
_HEADING = re.compile(r"^#{1,3}\s+(.+)$", re.M)


def graph_dir(settings: Settings | None = None) -> Path:
    settings = settings or get_settings()
    # Prefer sibling of rag_index_dir
    return Path(settings.rag_index_dir).resolve().parent / "rag_graph"


def _norm_entity(s: str) -> str:
    s = re.sub(r"\s+", " ", (s or "").strip())
    return s[:80]


def load_edges(settings: Settings | None = None) -> list[dict[str, Any]]:
    path = graph_dir(settings) / "edges.jsonl"
    if not path.is_file():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return rows


def load_entity_index(settings: Settings | None = None) -> dict[str, list[str]]:
    path = graph_dir(settings) / "entity_index.json"
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return {str(k): list(v) for k, v in (data or {}).items()}
    except (OSError, json.JSONDecodeError):
        return {}


def search_graph(
    query: str,
    *,
    top_k: int = 8,
    settings: Settings | None = None,
) -> list[dict[str, Any]]:
    """Return edges/entities matching query tokens."""
    q = (query or "").casefold()
    tokens = [t for t in re.split(r"[^\wÀ-ú]+", q) if len(t) > 2]
    if not tokens:
        return []
    edges = load_edges(settings)
    scored: list[tuple[float, dict[str, Any]]] = []
    for e in edges:
        blob = " ".join(
            [
                str(e.get("source") or ""),
                str(e.get("relation") or ""),
                str(e.get("target") or ""),
                str(e.get("doc") or ""),
            ]
        ).casefold()
        hits = sum(1 for t in tokens if t in blob)
        if hits:
            scored.append((float(hits), e))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [e for _, e in scored[:top_k]]


def format_graph_block(hits: list[dict[str, Any]]) -> str:
    if not hits:
        return ""
    lines = ["=== KNOWLEDGE GRAPH ===", "Relations (heuristic):"]
    for e in hits[:8]:
        src = e.get("source")
        rel = e.get("relation") or "related_to"
        tgt = e.get("target")
        doc = e.get("doc") or ""
        lines.append(f"- {src} —{rel}→ {tgt}" + (f" [{doc}]" if doc else ""))
    return "\n".join(lines)


def extract_edges_from_text(text: str, *, doc: str = "") -> list[dict[str, Any]]:
    edges: list[dict[str, Any]] = []
    for m in _ARROW.finditer(text):
        edges.append(
            {
                "source": _norm_entity(m.group(1)),
                "relation": "depends_on",
                "target": _norm_entity(m.group(2)),
                "doc": doc,
            }
        )
    for m in _MD_LINK.finditer(text):
        edges.append(
            {
                "source": _norm_entity(m.group(1)),
                "relation": "links_to",
                "target": _norm_entity(m.group(2)),
                "doc": doc,
            }
        )
    headings = _HEADING.findall(text)
    # Pair consecutive headings as soft hierarchy
    for i in range(len(headings) - 1):
        edges.append(
            {
                "source": _norm_entity(headings[i]),
                "relation": "section_of",
                "target": _norm_entity(headings[i + 1]),
                "doc": doc,
            }
        )
    return edges


def build_entity_index(edges: list[dict[str, Any]]) -> dict[str, list[str]]:
    idx: dict[str, set[str]] = defaultdict(set)
    for e in edges:
        doc = str(e.get("doc") or "")
        for key in ("source", "target"):
            ent = str(e.get(key) or "").casefold()
            if ent and doc:
                idx[ent].add(doc)
    return {k: sorted(v) for k, v in sorted(idx.items())}
