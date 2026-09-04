"""Build lightweight knowledge graph JSONL from RAG chunks / markdown."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from friday.rag.knowledge_graph import (
    build_entity_index,
    extract_edges_from_text,
)
from friday_llm.util import read_jsonl, resolve_path, write_jsonl


def build_kg(
    *,
    chunks_path: str = "friday-llm/data/rag/chunks.jsonl",
    facts_glob: str = "friday-llm/data/rag/facts/**/*.md",
    out_dir: str = "data/rag_graph",
) -> dict[str, Any]:
    root_out = resolve_path(out_dir)
    root_out.mkdir(parents=True, exist_ok=True)

    edges: list[dict[str, Any]] = []
    chunks_file = resolve_path(chunks_path)
    if chunks_file.is_file():
        for row in read_jsonl(chunks_file):
            text = str(row.get("text") or "")
            doc = str(
                (row.get("metadata") or {}).get("source")
                or row.get("source")
                or row.get("document_id")
                or ""
            )
            edges.extend(extract_edges_from_text(text, doc=doc))

    # Prefer curated facts for clean arrows
    for path in sorted(resolve_path(".").glob(facts_glob)):
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        rel = path.as_posix()
        edges.extend(extract_edges_from_text(text, doc=rel))

    # Dedupe
    seen: set[str] = set()
    unique: list[dict[str, Any]] = []
    for e in edges:
        key = f"{e.get('source')}|{e.get('relation')}|{e.get('target')}|{e.get('doc')}"
        if key in seen:
            continue
        seen.add(key)
        unique.append(e)

    edges_path = root_out / "edges.jsonl"
    write_jsonl(edges_path, unique)
    idx = build_entity_index(unique)
    idx_path = root_out / "entity_index.json"
    idx_path.write_text(json.dumps(idx, ensure_ascii=False, indent=2), encoding="utf-8")
    meta = {
        "edges": len(unique),
        "entities": len(idx),
        "edges_path": str(edges_path),
        "entity_index_path": str(idx_path),
    }
    (root_out / "meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return meta


def main() -> None:
    p = argparse.ArgumentParser(description="Build FRIDAY lightweight RAG knowledge graph")
    p.add_argument("--chunks", default="friday-llm/data/rag/chunks.jsonl")
    p.add_argument("--out", default="data/rag_graph")
    args = p.parse_args()
    meta = build_kg(chunks_path=args.chunks, out_dir=args.out)
    print(json.dumps(meta, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
