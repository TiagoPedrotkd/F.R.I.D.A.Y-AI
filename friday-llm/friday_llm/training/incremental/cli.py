"""CLI: prepare incremental CPT days and optionally train."""

from __future__ import annotations

import argparse
import json
import logging
import sys

from friday_llm.training.continued_pretraining.run import run_cpt
from friday_llm.training.incremental.planner import prepare_day, read_progress

logger = logging.getLogger(__name__)


def main(argv: list[str] | None = None) -> None:
    logging.basicConfig(level=logging.INFO)
    p = argparse.ArgumentParser(
        description="FRIDAY incremental CPT — docs first, flexible duration"
    )
    p.add_argument("--day", type=int, default=None, help="Day number (>=1)")
    p.add_argument("--add", type=int, default=None, help="How many new docs to add")
    p.add_argument(
        "--steps-per-doc",
        type=int,
        default=4,
        help="Optimizer steps budget per new doc (default 4)",
    )
    p.add_argument("--min-steps", type=int, default=20)
    p.add_argument(
        "--smoke",
        action="store_true",
        help="Use Qwen2.5-0.5B instead of 7B (fast check)",
    )
    p.add_argument(
        "--train",
        action="store_true",
        help="Run CPT immediately after preparing the day",
    )
    p.add_argument(
        "--status",
        action="store_true",
        help="Print progress.json and exit",
    )
    p.add_argument(
        "--prefer-domain",
        action="store_true",
        help="Prefer AI/assistant/local-domain docs from the pool",
    )
    args = p.parse_args(argv)

    if args.status:
        print(json.dumps(read_progress(), ensure_ascii=False, indent=2))
        return

    if args.day is None or args.add is None:
        p.error("--day and --add are required (unless --status)")

    progress = prepare_day(
        args.day,
        args.add,
        steps_per_doc=args.steps_per_doc,
        min_steps=args.min_steps,
        use_smoke_model=args.smoke,
        prefer_domain=args.prefer_domain,
    )
    print(json.dumps(progress, ensure_ascii=False, indent=2))

    if args.train:
        rel = f"friday-llm/configs/incremental/cpt_day_{args.day}.yaml"
        report = run_cpt(rel, force_resume=False)
        print(json.dumps(report, ensure_ascii=False, indent=2, default=str))
        if report.get("error") or report.get("status") == "failed":
            sys.exit(1)


if __name__ == "__main__":
    main()
