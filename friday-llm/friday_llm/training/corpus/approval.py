"""Approve CPT corpus against dataset catalog before training."""

from __future__ import annotations

import argparse
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from friday_llm.pipeline.registry.catalog import load_catalog
from friday_llm.util import content_hash, estimate_tokens, read_jsonl, resolve_path

logger = logging.getLogger(__name__)

_FORBIDDEN_PATH_PARTS = (
    "evaluation",
    "friday_eval",
    "data/chroma",
    "news_cache",
    "excluded",
)

_CPT_DATASET_IDS = (
    "fineweb2-fase1-cpt",
    "fineweb2-hq-por-pilot",
)


def _file_aggregate_hash(path: Path) -> str:
    rows = read_jsonl(path)
    blob = json.dumps(rows, ensure_ascii=False, sort_keys=True)
    return content_hash(blob)


def _find_cpt_catalog_entry(catalog: list[dict[str, Any]]) -> dict[str, Any] | None:
    for entry in catalog:
        if not entry.get("included_in_training"):
            continue
        if entry.get("contains_personal_data"):
            continue
        if entry.get("processing_status") != "ready":
            continue
        ds_id = str(entry.get("dataset_id") or "")
        if ds_id in _CPT_DATASET_IDS or "fineweb" in ds_id.casefold() or "cpt" in ds_id.casefold():
            return entry
        allowed = str(entry.get("allowed_use") or "")
        if "training" in allowed or "pretrain" in allowed:
            return entry
    return None


def _path_forbidden(data_path: Path) -> list[str]:
    posix = data_path.as_posix().casefold()
    return [p for p in _FORBIDDEN_PATH_PARTS if p in posix]


def approve_corpus(
    data_file: str | Path,
    *,
    catalog_path: str = "friday-llm/data/registry/datasets.jsonl",
    out_path: str = "friday-llm/reports/corpus_approval.json",
    strict_catalog_hash: bool = False,
) -> dict[str, Any]:
    """Validate CPT file against catalog; write approval manifest."""
    data_path = resolve_path(data_file)
    if not data_path.is_file():
        raise FileNotFoundError(f"CPT data file not found: {data_path}")

    forbidden = _path_forbidden(data_path)
    if forbidden:
        raise ValueError(f"Data path contains forbidden segments: {forbidden}")

    rows = read_jsonl(data_path)
    if not rows:
        raise ValueError(f"CPT file is empty: {data_path}")

    file_hash = _file_aggregate_hash(data_path)
    token_est = sum(estimate_tokens(str(r.get("text") or "")) for r in rows)

    catalog = load_catalog(catalog_path)
    entry = _find_cpt_catalog_entry(catalog)
    catalog_hash = str(entry.get("content_hash") or "") if entry else ""
    hash_ok = True
    if strict_catalog_hash and catalog_hash and catalog_hash != file_hash:
        hash_ok = False

    approved = entry is not None and hash_ok and not forbidden

    manifest: dict[str, Any] = {
        "approved": approved,
        "dataset_id": entry.get("dataset_id") if entry else None,
        "file_path": str(data_path),
        "content_hash": file_hash,
        "catalog_content_hash": catalog_hash or None,
        "hash_matches_catalog": hash_ok if catalog_hash else None,
        "document_count": len(rows),
        "token_count_est": token_est,
        "approved_at": datetime.now(timezone.utc).isoformat(),
        "catalog_entry": {
            "license": entry.get("license") if entry else None,
            "processing_status": entry.get("processing_status") if entry else None,
        },
        "notes": (
            "Corpus approved for Fase 3 CPT."
            if approved
            else "Corpus NOT approved — fix catalog or rebuild Fase 1 data."
        ),
    }

    out = resolve_path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info("Corpus approval → %s (approved=%s)", out, approved)
    if not approved:
        raise ValueError(manifest["notes"])
    return manifest


def validate_approval(
    data_file: str | Path,
    *,
    approval_path: str = "friday-llm/reports/corpus_approval.json",
) -> dict[str, Any]:
    """Ensure approval manifest exists and matches current file hash."""
    data_path = resolve_path(data_file)
    approval = resolve_path(approval_path)
    if not approval.is_file():
        raise FileNotFoundError(
            f"Missing corpus approval at {approval}. "
            "Run: python -m friday_llm.training.corpus.approval --data <cpt.jsonl>"
        )
    manifest = json.loads(approval.read_text(encoding="utf-8"))
    if not manifest.get("approved"):
        raise ValueError(f"Corpus not approved: {manifest.get('notes')}")
    current_hash = _file_aggregate_hash(data_path)
    if manifest.get("content_hash") != current_hash:
        raise ValueError(
            "CPT file changed since approval. Re-run corpus approval."
        )
    return manifest


def main(argv: list[str] | None = None) -> None:
    logging.basicConfig(level=logging.INFO)
    p = argparse.ArgumentParser(description="Approve CPT corpus for training")
    p.add_argument(
        "--data",
        default="friday-llm/data/pretraining/cpt_fase1.jsonl",
    )
    p.add_argument(
        "--catalog",
        default="friday-llm/data/registry/datasets.jsonl",
    )
    p.add_argument(
        "--out",
        default="friday-llm/reports/corpus_approval.json",
    )
    p.add_argument(
        "--strict-catalog-hash",
        action="store_true",
        help="Require file hash to match catalog content_hash",
    )
    args = p.parse_args(argv)
    manifest = approve_corpus(
        args.data,
        catalog_path=args.catalog,
        out_path=args.out,
        strict_catalog_hash=args.strict_catalog_hash,
    )
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
