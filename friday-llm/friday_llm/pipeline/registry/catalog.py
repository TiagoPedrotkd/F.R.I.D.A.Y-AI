"""Dataset catalog validation and updates."""

from __future__ import annotations

import argparse
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from friday_llm.util import content_hash, estimate_tokens, read_jsonl, resolve_path, write_jsonl

logger = logging.getLogger(__name__)

_REQUIRED_FIELDS = {
    "dataset_id",
    "name",
    "source",
    "license",
    "allowed_use",
    "contains_personal_data",
    "processing_status",
    "included_in_training",
}


def validate_entry(entry: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for field in _REQUIRED_FIELDS:
        if field not in entry:
            errors.append(f"missing {field}")
    status = entry.get("processing_status")
    if status not in {
        "registered",
        "raw",
        "cleaned",
        "deduplicated",
        "ready",
        "excluded",
    }:
        errors.append(f"invalid processing_status: {status}")
    return errors


def load_catalog(path: str | Path) -> list[dict[str, Any]]:
    return read_jsonl(resolve_path(path))


def save_catalog(path: str | Path, rows: list[dict[str, Any]]) -> None:
    write_jsonl(resolve_path(path), rows)


def _aggregate_hash(path: Path, sample: int = 50) -> str:
    rows = read_jsonl(path)
    if not rows:
        return ""
    blob = json.dumps(rows[:sample], ensure_ascii=False, sort_keys=True)
    return content_hash(blob)


def _count_tokens_jsonl(path: Path) -> int:
    total = 0
    for row in read_jsonl(path):
        if "text" in row:
            total += estimate_tokens(str(row["text"]))
        elif "messages" in row:
            for msg in row.get("messages") or []:
                total += estimate_tokens(str(msg.get("content") or ""))
    return total


def update_catalog_from_build(
    catalog_path: str | Path,
    *,
    cpt_path: str | Path | None = None,
    sft_train_path: str | Path | None = None,
    sft_holdout_path: str | Path | None = None,
    rag_path: str | Path | None = None,
    eval_path: str | Path | None = None,
    build_date: str | None = None,
) -> list[dict[str, Any]]:
    """Update known dataset entries with counts/hashes from Fase 1 build."""
    path = resolve_path(catalog_path)
    rows = load_catalog(path)
    by_id = {r["dataset_id"]: r for r in rows}
    today = build_date or datetime.now(timezone.utc).date().isoformat()

    if cpt_path and resolve_path(cpt_path).is_file():
        p = resolve_path(cpt_path)
        docs = read_jsonl(p)
        entry = by_id.get("fineweb2-hq-por-pilot") or by_id.get("fineweb2-fase1-cpt")
        if entry is None:
            entry = {
                "dataset_id": "fineweb2-fase1-cpt",
                "name": "FineWeb2 CPT Fase 1 (por+eng stream)",
                "source": "HuggingFaceFW/fineweb-2",
                "source_url": "https://huggingface.co/datasets/HuggingFaceFW/fineweb-2",
                "license": "ODC-By (verify dataset card)",
                "allowed_use": "research_training_with_attribution",
                "language": "por+eng",
                "region_variant": "mixed_pt",
                "contains_personal_data": False,
                "included_in_training": True,
                "notes": "Fase 1 streamed subset; not full FineWeb2.",
            }
            rows.append(entry)
            by_id[entry["dataset_id"]] = entry
        entry["document_count"] = len(docs)
        entry["token_count"] = _count_tokens_jsonl(p)
        entry["content_hash"] = _aggregate_hash(p)
        entry["processing_status"] = "ready"
        entry["download_date"] = today
        entry["version_or_crawl"] = "fase1-por-eng-stream"

    if sft_train_path and resolve_path(sft_train_path).is_file():
        p = resolve_path(sft_train_path)
        train = read_jsonl(p)
        entry = by_id.get("friday-sft-seed-v0") or by_id.get("friday-sft-fase1")
        if entry is None:
            entry = {
                "dataset_id": "friday-sft-fase1",
                "name": "FRIDAY SFT Fase 1 (registry templates)",
                "source": "curated_in_repo",
                "source_url": str(p),
                "license": "Apache-2.0",
                "allowed_use": "training",
                "language": "pt+en",
                "region_variant": "pt-PT",
                "contains_personal_data": False,
                "included_in_training": True,
                "notes": "Seed + SkillRegistry templates; tools validated.",
            }
            rows.append(entry)
            by_id[entry["dataset_id"]] = entry
        holdout_n = 0
        if sft_holdout_path and resolve_path(sft_holdout_path).is_file():
            holdout_n = len(read_jsonl(resolve_path(sft_holdout_path)))
        entry["document_count"] = len(train) + holdout_n
        entry["token_count"] = _count_tokens_jsonl(p)
        entry["content_hash"] = _aggregate_hash(p)
        entry["processing_status"] = "ready"
        entry["download_date"] = today
        entry["version_or_crawl"] = "fase1-v1"

    if rag_path and resolve_path(rag_path).is_file():
        p = resolve_path(rag_path)
        chunks = read_jsonl(p)
        entry = by_id.get("friday-rag-docs-v0") or by_id.get("friday-rag-fase1")
        if entry is None:
            entry = {
                "dataset_id": "friday-rag-fase1",
                "name": "FRIDAY RAG chunks (repo docs)",
                "source": "repo_docs_authorized",
                "source_url": "docs/",
                "license": "Apache-2.0",
                "allowed_use": "rag_only",
                "language": "pt",
                "region_variant": "pt-PT",
                "contains_personal_data": False,
                "included_in_training": False,
                "notes": "Chunked markdown from docs/; not for CPT.",
            }
            rows.append(entry)
            by_id[entry["dataset_id"]] = entry
        entry["document_count"] = len(chunks)
        entry["token_count"] = _count_tokens_jsonl(p)
        entry["content_hash"] = _aggregate_hash(p)
        entry["processing_status"] = "ready"
        entry["download_date"] = today
        entry["version_or_crawl"] = "fase1-chunks"

    if eval_path and resolve_path(eval_path).is_file():
        p = resolve_path(eval_path)
        entry = by_id.get("friday-eval-v0")
        if entry:
            entry["document_count"] = len(read_jsonl(p))
            entry["processing_status"] = "ready"
            entry["download_date"] = today

    for entry in rows:
        errs = validate_entry(entry)
        if errs:
            logger.warning("Catalog entry %s: %s", entry.get("dataset_id"), errs)

    save_catalog(path, rows)
    return rows


def main(argv: list[str] | None = None) -> None:
    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser(description="FRIDAY dataset catalog")
    parser.add_argument(
        "--catalog",
        default="friday-llm/data/registry/datasets.jsonl",
    )
    parser.add_argument("--update", action="store_true", help="Validate catalog only")
    parser.add_argument("--cpt", default="")
    parser.add_argument("--sft-train", default="")
    parser.add_argument("--sft-holdout", default="")
    parser.add_argument("--rag", default="")
    parser.add_argument("--eval", default="friday-llm/data/evaluation/friday_eval.jsonl")
    args = parser.parse_args(argv)

    if args.cpt:
        rows = update_catalog_from_build(
            args.catalog,
            cpt_path=args.cpt or None,
            sft_train_path=args.sft_train or None,
            sft_holdout_path=args.sft_holdout or None,
            rag_path=args.rag or None,
            eval_path=args.eval or None,
        )
        print(json.dumps({"updated": len(rows)}, indent=2))
        return

    rows = load_catalog(args.catalog)
    issues = {r["dataset_id"]: validate_entry(r) for r in rows}
    print(json.dumps({"entries": len(rows), "issues": issues}, indent=2))


if __name__ == "__main__":
    main()
