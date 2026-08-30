"""Eval report aggregation by category."""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from friday_llm.util import resolve_path


def category_breakdown(report: dict[str, Any]) -> dict[str, dict[str, Any]]:
    by_cat: dict[str, list[dict]] = defaultdict(list)
    for row in report.get("results") or []:
        cat = str(row.get("category") or "unknown")
        by_cat[cat].append(row)

    out: dict[str, dict[str, Any]] = {}
    for cat, rows in sorted(by_cat.items()):
        passed = sum(1 for r in rows if r.get("pass"))
        tool_rows = [r for r in rows if r.get("expect_tool") is not None]
        tool_ok = sum(1 for r in tool_rows if r.get("tool_ok"))
        out[cat] = {
            "n": len(rows),
            "passed": passed,
            "pass_rate": round(passed / len(rows), 3) if rows else 0.0,
            "tool_call_rate": round(tool_ok / len(tool_rows), 3) if tool_rows else None,
        }
    return out


def compare_with_categories(
    baseline_path: str | Path,
    candidate_path: str | Path,
) -> dict[str, Any]:
    from friday_llm.evaluation.compare_runs import compare_reports

    base = json.loads(resolve_path(baseline_path).read_text(encoding="utf-8"))
    comparison = compare_reports(baseline_path, candidate_path)

    candidate = None
    cp = resolve_path(candidate_path)
    if cp.is_file():
        candidate = json.loads(cp.read_text(encoding="utf-8"))

    return {
        **comparison,
        "baseline_by_category": category_breakdown(base),
        "candidate_by_category": category_breakdown(candidate) if candidate else None,
    }
