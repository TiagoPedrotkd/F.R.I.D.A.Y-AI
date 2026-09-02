"""Feedback aggregation: nightly reports + hard-case export for eval/SFT."""

from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
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


def build_feedback_report(
    feedback_path: str | Path,
    *,
    out_dir: str | Path | None = None,
) -> dict[str, Any]:
    path = Path(feedback_path)
    rows = _read_jsonl(path)
    ratings = Counter(str(r.get("rating") or "") for r in rows)
    down = [r for r in rows if str(r.get("rating")) == "down"]
    hard_cases: list[dict[str, Any]] = []
    for r in down:
        hard_cases.append(
            {
                "user": r.get("user_text") or "",
                "assistant": r.get("reply_text") or "",
                "comment": r.get("comment") or "",
                "grounding_score": r.get("grounding_score"),
                "session_id": r.get("session_id"),
                "ts": r.get("ts"),
                "source": "feedback_down",
            }
        )

    report = {
        "built_at": datetime.now(timezone.utc).isoformat(),
        "feedback_path": str(path),
        "total": len(rows),
        "ratings": dict(ratings),
        "down_rate": round(len(down) / max(1, len(rows)), 3),
        "hard_cases": len(hard_cases),
    }

    dest = Path(out_dir) if out_dir else path.parent / "reports"
    dest.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    report_path = dest / f"feedback_report_{stamp}.json"
    hard_path = dest / f"hard_cases_{stamp}.jsonl"
    report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    with hard_path.open("w", encoding="utf-8") as fh:
        for row in hard_cases:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    report["report_path"] = str(report_path)
    report["hard_cases_path"] = str(hard_path)
    return report


def main() -> None:
    import argparse

    p = argparse.ArgumentParser(description="Build feedback report + hard cases")
    p.add_argument("--feedback", default="data/feedback/feedback.jsonl")
    p.add_argument("--out-dir", default="data/feedback/reports")
    args = p.parse_args()
    out = build_feedback_report(args.feedback, out_dir=args.out_dir)
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
