"""Approve SFT dataset before Fase 4 training."""

from __future__ import annotations

import argparse
import json
import logging
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from friday_llm.pipeline.build_datasets.sft_builder import validate_sft_tools
from friday_llm.pipeline.quality.contamination import (
    build_forbidden_corpus,
    is_eval_contaminated,
)
from friday_llm.util import content_hash, read_jsonl, resolve_path

logger = logging.getLogger(__name__)

_REQUIRED_CATEGORIES = (
    "conversation",
    "personality",
    "tool_calling",
    "safety",
)


def _file_hash(paths: list[Path]) -> str:
    blob = []
    for p in sorted(paths):
        blob.extend(read_jsonl(p))
    return content_hash(json.dumps(blob, ensure_ascii=False, sort_keys=True))


def _check_eval_leak(rows: list[dict], eval_path: str) -> list[str]:
    forbidden_hashes, forbidden_shingles = build_forbidden_corpus(eval_path, None)
    leaks: list[str] = []
    for i, row in enumerate(rows):
        for msg in row.get("messages") or []:
            if msg.get("role") != "user":
                continue
            content = str(msg.get("content") or "")
            if content and is_eval_contaminated(
                content,
                forbidden_hashes=forbidden_hashes,
                forbidden_shingles=forbidden_shingles,
            ):
                leaks.append(f"row_{i}:{content[:40]}")
    return leaks


def approve_sft_dataset(
    train_file: str | Path,
    holdout_file: str | Path,
    *,
    eval_path: str = "friday-llm/data/evaluation/friday_eval.jsonl",
    out_path: str = "friday-llm/reports/sft_approval.json",
) -> dict[str, Any]:
    train_path = resolve_path(train_file)
    holdout_path = resolve_path(holdout_file)
    if not train_path.is_file():
        raise FileNotFoundError(f"Missing SFT train file: {train_path}")

    train_rows = read_jsonl(train_path)
    holdout_rows = read_jsonl(holdout_path) if holdout_path.is_file() else []
    all_rows = train_rows + holdout_rows

    if not train_rows:
        raise ValueError("SFT train file is empty")

    invalid_tools = validate_sft_tools(all_rows)
    leaks = _check_eval_leak(all_rows, eval_path)
    categories = Counter(str(r.get("category") or "other") for r in all_rows)
    missing_cats = [c for c in _REQUIRED_CATEGORIES if categories.get(c, 0) == 0]

    approved = not invalid_tools and not leaks and not missing_cats

    manifest: dict[str, Any] = {
        "approved": approved,
        "train_file": str(train_path),
        "holdout_file": str(holdout_path),
        "content_hash": _file_hash([train_path, holdout_path] if holdout_path.is_file() else [train_path]),
        "train_count": len(train_rows),
        "holdout_count": len(holdout_rows),
        "categories": dict(categories),
        "missing_categories": missing_cats,
        "invalid_tools": invalid_tools,
        "eval_leaks": leaks,
        "approved_at": datetime.now(timezone.utc).isoformat(),
        "notes": (
            "SFT dataset approved for Fase 4."
            if approved
            else "SFT NOT approved — fix tools, categories, or eval leaks."
        ),
    }

    out = resolve_path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info("SFT approval → %s (approved=%s)", out, approved)
    if not approved:
        raise ValueError(manifest["notes"])
    return manifest


def validate_sft_approval(
    train_file: str | Path,
    holdout_file: str | Path,
    *,
    approval_path: str = "friday-llm/reports/sft_approval.json",
) -> dict[str, Any]:
    train_path = resolve_path(train_file)
    holdout_path = resolve_path(holdout_file)
    approval = resolve_path(approval_path)
    if not approval.is_file():
        raise FileNotFoundError(
            f"Missing SFT approval at {approval}. Run sft approval first."
        )
    manifest = json.loads(approval.read_text(encoding="utf-8"))
    if not manifest.get("approved"):
        raise ValueError(f"SFT not approved: {manifest.get('notes')}")
    paths = [train_path]
    if holdout_path.is_file():
        paths.append(holdout_path)
    current_hash = _file_hash(paths)
    if manifest.get("content_hash") != current_hash:
        raise ValueError("SFT files changed since approval. Re-run approval.")
    return manifest


def main(argv: list[str] | None = None) -> None:
    logging.basicConfig(level=logging.INFO)
    p = argparse.ArgumentParser(description="Approve Fase 4 SFT dataset")
    p.add_argument("--train", default="friday-llm/data/sft/fase4_sft_train.jsonl")
    p.add_argument("--holdout", default="friday-llm/data/sft/fase4_sft_holdout.jsonl")
    p.add_argument("--eval", default="friday-llm/data/evaluation/friday_eval.jsonl")
    p.add_argument("--out", default="friday-llm/reports/sft_approval.json")
    args = p.parse_args(argv)
    manifest = approve_sft_dataset(
        args.train, args.holdout, eval_path=args.eval, out_path=args.out
    )
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
