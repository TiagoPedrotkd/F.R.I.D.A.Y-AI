"""Fase 5 RAG orchestrator: build → index → smoke → report."""

from __future__ import annotations

import argparse
import json
import logging
from datetime import datetime, timezone
from typing import Any

from friday_llm.rag.index import build_rag_corpus, index_rag_corpus, smoke_search
from friday_llm.rag.quality_gate import run_quality_gate
from friday_llm.util import load_yaml, resolve_path

logger = logging.getLogger(__name__)


def _write_report(cfg: dict[str, Any], *, build: dict | None, index: dict | None, smoke: dict | None) -> dict[str, Any]:
    stats: dict[str, Any] = {
        "run_id": cfg.get("run_id"),
        "finished_at": datetime.now(timezone.utc).isoformat(),
        "build": build,
        "index": index,
        "smoke": smoke,
        "memory_separate_from_rag": True,
        "memory_path": "data/chroma/",
        "rag_index_path": str(resolve_path((cfg.get("paths") or {}).get("index_dir") or "data/rag_chroma")),
        "notes": (
            "Document RAG indexado em data/rag_chroma/ (coleccao friday_docs). "
            "Memoria pessoal permanece em data/chroma/ (friday_memory)."
        ),
    }
    json_path = resolve_path(cfg.get("stats_json") or "friday-llm/reports/phase5_rag_stats.json")
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(stats, ensure_ascii=False, indent=2), encoding="utf-8")

    md_path = resolve_path(cfg.get("report_md") or "friday-llm/reports/phase5_rag_report.md")
    lines = [
        "# Fase 5 — RAG e integração",
        "",
        f"**Run:** `{cfg.get('run_id')}`  ",
        f"**Gerado:** {stats['finished_at']}",
        "",
        "## Corpus",
        "",
    ]
    if build:
        lines += [
            f"- Documentos repo: **{build.get('repo_documents')}** | seeds: **{build.get('seed_documents')}**",
            f"- Chunks: **{build.get('chunks')}** → `{build.get('chunks_path')}`",
        ]
    if index:
        lines += [
            "",
            "## Índice vetorial",
            "",
            f"- Modelo: `{index.get('embedding_model')}`",
            f"- Chunks indexados: **{index.get('chunk_count')}**",
            f"- Pasta: `{index.get('index_dir')}`",
        ]
    if smoke:
        lines += [
            "",
            "## Smoke (keyword/embedding)",
            "",
            f"- Backend: `{smoke.get('backend')}`",
            "",
            "```json",
            json.dumps(smoke.get("queries") or {}, ensure_ascii=False, indent=2),
            "```",
        ]
    lines += [
        "",
        "## Integração agente",
        "",
        "- Skill `search_docs` no ToolRunner (CLI + agent-api)",
        "- Router: documento/manual → RAG; notícias/hora → tools",
        "- Phi-4 em produção inalterado (`LM_STUDIO_MODEL`)",
        "",
    ]
    md_path.write_text("\n".join(lines), encoding="utf-8")
    logger.info("Phase 5 RAG report → %s", md_path)
    return stats


def run_fase5(
    config_path: str,
    *,
    only: str | None = None,
    query: str | None = None,
    skip_index: bool = False,
) -> dict[str, Any]:
    cfg = load_yaml(config_path)
    steps = ["build", "index", "smoke", "report"]
    if only:
        steps = [only]

    build_meta: dict | None = None
    index_meta: dict | None = None
    smoke_meta: dict | None = None

    if "build" in steps:
        build_meta = build_rag_corpus(config_path)

    if "index" in steps and not skip_index:
        try:
            index_meta = index_rag_corpus(config_path)
        except Exception as exc:
            logger.warning("Index skipped or failed: %s", exc)
            index_meta = {"error": str(exc)}

    if "smoke" in steps:
        smoke_meta = smoke_search(config_path, query=query)

    gate_meta: dict | None = None
    if "gate" in steps:
        gate_meta = run_quality_gate(config_path)
        if not gate_meta.get("passed", False):
            raise SystemExit(2)

    if "report" in steps or only is None:
        if build_meta is None:
            bp = resolve_path(cfg.get("report_json") or "friday-llm/reports/phase5_rag_build.json")
            if bp.is_file():
                build_meta = json.loads(bp.read_text(encoding="utf-8"))
        if index_meta is None:
            ip = resolve_path((cfg.get("paths") or {}).get("index_dir") or "data/rag_chroma")
            meta_file = ip / "index_meta.json"
            if meta_file.is_file():
                index_meta = json.loads(meta_file.read_text(encoding="utf-8"))
        stats = _write_report(cfg, build=build_meta, index=index_meta, smoke=smoke_meta)
        if gate_meta:
            stats["gate"] = gate_meta
        return stats

    return {"build": build_meta, "index": index_meta, "smoke": smoke_meta, "gate": gate_meta}


def main(argv: list[str] | None = None) -> None:
    logging.basicConfig(level=logging.INFO)
    p = argparse.ArgumentParser(description="FRIDAY LLM Fase 5 RAG")
    p.add_argument("--config", default="friday-llm/configs/fase5_rag.yaml")
    p.add_argument("--only", choices=["build", "index", "smoke", "gate", "report"], default=None)
    p.add_argument("--query", default=None)
    p.add_argument("--skip-index", action="store_true")
    args = p.parse_args(argv)
    result = run_fase5(
        args.config,
        only=args.only,
        query=args.query,
        skip_index=args.skip_index,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
