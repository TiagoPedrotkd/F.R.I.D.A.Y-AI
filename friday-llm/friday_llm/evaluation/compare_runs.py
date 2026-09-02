"""Compare baseline vs pilot eval reports."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from friday_llm.util import resolve_path


def _tool_call_rate(report: dict[str, Any]) -> float:
    results = report.get("results") or []
    with_expect = [r for r in results if r.get("expect_tool")]
    if not with_expect:
        return 0.0
    ok = sum(1 for r in with_expect if r.get("tool_ok"))
    return round(ok / len(with_expect), 3)


def compare_reports(
    baseline_path: str | Path,
    pilot_path: str | Path,
) -> dict[str, Any]:
    baseline = json.loads(resolve_path(baseline_path).read_text(encoding="utf-8"))
    pilot_path = resolve_path(pilot_path)
    if not pilot_path.is_file():
        return {
            "baseline": {
                "path": str(resolve_path(baseline_path)),
                "model": baseline.get("model"),
                "pass_rate": baseline.get("pass_rate"),
                "mean_latency_s": baseline.get("mean_latency_s"),
                "tool_call_rate": _tool_call_rate(baseline),
            },
            "pilot": None,
            "delta": None,
            "notes": "Pilot eval not run yet. Load model in LM Studio and run with run_eval=true.",
        }
    pilot = json.loads(pilot_path.read_text(encoding="utf-8"))
    b_rate = float(baseline.get("pass_rate") or 0)
    p_rate = float(pilot.get("pass_rate") or 0)
    b_lat = float(baseline.get("mean_latency_s") or 0)
    p_lat = float(pilot.get("mean_latency_s") or 0)
    b_tools = _tool_call_rate(baseline)
    p_tools = _tool_call_rate(pilot)
    return {
        "baseline": {
            "path": str(resolve_path(baseline_path)),
            "model": baseline.get("model"),
            "pass_rate": b_rate,
            "mean_latency_s": b_lat,
            "tool_call_rate": b_tools,
        },
        "pilot": {
            "path": str(pilot_path),
            "model": pilot.get("model"),
            "pass_rate": p_rate,
            "mean_latency_s": p_lat,
            "tool_call_rate": p_tools,
        },
        "delta": {
            "pass_rate": round(p_rate - b_rate, 3),
            "mean_latency_s": round(p_lat - b_lat, 3),
            "tool_call_rate": round(p_tools - b_tools, 3),
        },
    }


def main(argv: list[str] | None = None) -> None:
    import argparse
    import sys

    p = argparse.ArgumentParser(description="Compare baseline vs candidate eval reports")
    p.add_argument("--baseline", required=True)
    p.add_argument("--candidate", required=True)
    p.add_argument("--out", default="")
    p.add_argument("--min-delta", type=float, default=-0.05)
    args = p.parse_args(argv)
    report = compare_reports(args.baseline, args.candidate)
    text = json.dumps(report, ensure_ascii=False, indent=2)
    print(text)
    if args.out:
        out = resolve_path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text, encoding="utf-8")
    delta = (report.get("delta") or {}).get("pass_rate")
    if delta is not None and float(delta) < float(args.min_delta):
        print(f"GATE FAIL: pass_rate delta {delta} < {args.min_delta}", file=sys.stderr)
        sys.exit(2)
    print("GATE OK" if delta is not None else "GATE SKIP (no pilot)")


if __name__ == "__main__":
    main()
