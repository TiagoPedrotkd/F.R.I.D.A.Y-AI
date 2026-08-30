"""Select best CPT checkpoint by eval_loss."""

from __future__ import annotations

import argparse
import json
import logging
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from friday_llm.training.common import list_checkpoints
from friday_llm.util import read_jsonl, resolve_path

logger = logging.getLogger(__name__)


def _metrics_from_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = read_jsonl(path)
    return [r for r in rows if r.get("eval_loss") is not None]


def pick_best_checkpoint(
    run_dir: str | Path,
    *,
    metrics_path: str | Path | None = None,
) -> dict[str, Any]:
    """Return best checkpoint row (lowest eval_loss; tie → latest step)."""
    out_dir = resolve_path(run_dir)
    candidates: list[dict[str, Any]] = []

    if metrics_path:
        mp = resolve_path(metrics_path)
        if mp.is_file():
            candidates = _metrics_from_jsonl(mp)

    if not candidates:
        candidates = [c for c in list_checkpoints(out_dir) if c.get("eval_loss") is not None]

    if not candidates:
        raise FileNotFoundError(f"No checkpoints with eval_loss in {out_dir}")

    best = min(
        candidates,
        key=lambda r: (float(r["eval_loss"]), -int(r.get("step") or 0)),
    )
    return best


def copy_best_adapter(
    run_dir: str | Path,
    dest_adapter_dir: str | Path,
    *,
    metrics_path: str | Path | None = None,
    selection_path: str | Path | None = None,
) -> dict[str, Any]:
    best = pick_best_checkpoint(run_dir, metrics_path=metrics_path)
    src = Path(str(best.get("checkpoint_path") or ""))
    if not src.is_dir():
        raise FileNotFoundError(f"Checkpoint dir missing: {src}")

    dest = resolve_path(dest_adapter_dir)
    if dest.exists():
        shutil.rmtree(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(src, dest)

    selection = {
        "selected_at": datetime.now(timezone.utc).isoformat(),
        "step": best.get("step"),
        "eval_loss": best.get("eval_loss"),
        "train_loss": best.get("train_loss"),
        "source_checkpoint": str(src),
        "dest_adapter": str(dest),
    }
    sel_path = resolve_path(
        selection_path or dest.parent / "selection.json"
    )
    sel_path.write_text(json.dumps(selection, indent=2), encoding="utf-8")
    logger.info("Best checkpoint step=%s eval_loss=%s → %s", best.get("step"), best.get("eval_loss"), dest)
    return selection


def main(argv: list[str] | None = None) -> None:
    logging.basicConfig(level=logging.INFO)
    p = argparse.ArgumentParser(description="Select best CPT checkpoint")
    p.add_argument("--run-dir", default="friday-llm/checkpoints/cpt-fase3")
    p.add_argument(
        "--dest",
        default="friday-llm/checkpoints/cpt-fase3-best/adapter",
    )
    p.add_argument(
        "--metrics",
        default="friday-llm/reports/checkpoint_metrics.jsonl",
    )
    p.add_argument("--selection", default="")
    args = p.parse_args(argv)
    selection = copy_best_adapter(
        args.run_dir,
        args.dest,
        metrics_path=args.metrics or None,
        selection_path=args.selection or None,
    )
    print(json.dumps(selection, indent=2))


if __name__ == "__main__":
    main()
