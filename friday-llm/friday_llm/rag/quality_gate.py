"""RAG retrieval quality gate (recall@k / MRR on gold queries)."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from friday_llm.util import load_yaml, resolve_path

logger = logging.getLogger(__name__)


def _normalize(s: str) -> str:
    return " ".join((s or "").casefold().split())


def _hit_matches(hit_text: str, hit_id: str, expects: list[str]) -> bool:
    blob = _normalize(f"{hit_text} {hit_id}")
    for exp in expects:
        e = _normalize(exp)
        if e and e in blob:
            return True
    return False


def evaluate_retrieval(
    store: Any,
    gold_queries: list[dict[str, Any]],
    *,
    top_k: int = 3,
) -> dict[str, Any]:
    """
    gold item: {query, expect_contains: [str, ...], optional min_score}
    Expect match if any top_k hit text/id contains any expect string.
    """
    if not gold_queries:
        return {
            "ok": True,
            "skipped": True,
            "reason": "no gold queries",
            "n": 0,
        }

    hits_at_k = 0
    reciprocal_ranks: list[float] = []
    details: list[dict[str, Any]] = []

    for item in gold_queries:
        q = str(item.get("query") or "").strip()
        expects = [str(x) for x in (item.get("expect_contains") or []) if str(x).strip()]
        if not q or not expects:
            continue
        results = store.search(q, top_k=top_k)
        rank = None
        for i, h in enumerate(results, 1):
            doc_id = getattr(h, "url_or_document_id", "") or ""
            text = getattr(h, "text", "") or ""
            if _hit_matches(text, doc_id, expects):
                rank = i
                break
        if rank is not None:
            hits_at_k += 1
            reciprocal_ranks.append(1.0 / rank)
        else:
            reciprocal_ranks.append(0.0)
        details.append(
            {
                "query": q,
                "hit": rank is not None,
                "rank": rank,
                "top": [
                    {
                        "title": getattr(h, "title", ""),
                        "id": getattr(h, "url_or_document_id", ""),
                        "score": getattr(h, "score", 0),
                    }
                    for h in results[:top_k]
                ],
            }
        )

    n = len(details)
    recall = hits_at_k / max(1, n)
    mrr = sum(reciprocal_ranks) / max(1, n)
    return {
        "ok": True,
        "n": n,
        "hits_at_k": hits_at_k,
        f"recall@{top_k}": round(recall, 4),
        "mrr": round(mrr, 4),
        "details": details,
    }


def run_quality_gate(
    config_path: str,
    *,
    min_recall: float | None = None,
    min_mrr: float | None = None,
) -> dict[str, Any]:
    from friday.config import Settings
    from friday.rag.doc_store import get_doc_store, reset_doc_store

    cfg = load_yaml(config_path)
    paths = cfg.get("paths") or {}
    gate = cfg.get("quality_gate") or {}
    gold_path = resolve_path(
        gate.get("gold_queries")
        or paths.get("gold_queries")
        or "friday-llm/data/rag/gold_queries.yaml"
    )
    chunks = str(resolve_path(paths.get("chunks") or "friday-llm/data/rag/chunks.jsonl"))
    index_dir = resolve_path(paths.get("index_dir") or "data/rag_chroma")
    embedding_model = str(
        cfg.get("embedding_model")
        or "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    )
    top_k = int(gate.get("top_k") or 3)
    min_recall = float(
        min_recall if min_recall is not None else gate.get("min_recall_at_k", 0.6)
    )
    min_mrr = float(min_mrr if min_mrr is not None else gate.get("min_mrr", 0.4))

    gold: list[dict[str, Any]] = []
    if gold_path.suffix in (".yaml", ".yml") and gold_path.is_file():
        data = load_yaml(str(gold_path))
        if isinstance(data, list):
            gold = list(data)
        elif isinstance(data, dict):
            gold = list(data.get("queries") or [])
    elif gold_path.suffix == ".jsonl" and gold_path.is_file():
        for line in gold_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                gold.append(json.loads(line))

    chroma_ok = (index_dir / "chroma").is_dir()
    settings = Settings(
        RAG_ENABLED=True,
        RAG_BACKEND="embedding" if chroma_ok else "keyword",
        RAG_CORPUS_PATH=chunks,
        RAG_INDEX_DIR=str(index_dir),
        RAG_EMBEDDING_MODEL=embedding_model,
    )
    reset_doc_store()
    store = get_doc_store(settings)
    metrics = evaluate_retrieval(store, gold, top_k=top_k)
    recall = float(metrics.get(f"recall@{top_k}") or 0.0)
    mrr = float(metrics.get("mrr") or 0.0)
    passed = bool(metrics.get("n", 0) == 0) or (
        recall >= min_recall and mrr >= min_mrr
    )
    out = {
        **metrics,
        "backend": store.backend,
        "min_recall_at_k": min_recall,
        "min_mrr": min_mrr,
        "passed": passed,
        "gold_path": str(gold_path),
    }
    report = resolve_path(
        gate.get("report_json") or "friday-llm/reports/rag_quality_gate.json"
    )
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    out["report_path"] = str(report)
    if not passed:
        logger.error(
            "RAG quality gate FAILED recall@%s=%.3f (min %.3f) mrr=%.3f (min %.3f)",
            top_k,
            recall,
            min_recall,
            mrr,
            min_mrr,
        )
    else:
        logger.info(
            "RAG quality gate passed recall@%s=%.3f mrr=%.3f backend=%s",
            top_k,
            recall,
            mrr,
            store.backend,
        )
    return out
