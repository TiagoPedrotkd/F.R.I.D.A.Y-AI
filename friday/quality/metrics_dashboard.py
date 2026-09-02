"""Persist turn metrics and render a simple ops dashboard."""

from __future__ import annotations

import json
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_DEFAULT = Path("data/metrics/turns.jsonl")


def metrics_path() -> Path:
    return _DEFAULT


def append_turn_metric(record: dict[str, Any], path: Path | None = None) -> None:
    dest = path or metrics_path()
    dest.parent.mkdir(parents=True, exist_ok=True)
    row = {"ts": time.time(), **record}
    with dest.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")


def _read(path: Path) -> list[dict[str, Any]]:
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


def summarize_metrics(
    path: Path | None = None,
    *,
    last_n: int = 500,
) -> dict[str, Any]:
    rows = _read(path or metrics_path())[-last_n:]
    if not rows:
        return {
            "n": 0,
            "built_at": datetime.now(timezone.utc).isoformat(),
            "paths": {},
            "tools": {},
            "mean_total_ms": 0,
            "p95_total_ms": 0,
        }

    totals = [float(r.get("total_ms") or 0) for r in rows]
    totals_sorted = sorted(totals)
    p95 = totals_sorted[int(0.95 * (len(totals_sorted) - 1))] if totals_sorted else 0
    paths = Counter(str(r.get("path") or "unknown") for r in rows)
    tools: Counter[str] = Counter()
    tool_fail = 0
    tool_ok = 0
    for r in rows:
        for t in r.get("tools") or []:
            if isinstance(t, dict):
                tools[str(t.get("name") or "?")] += 1
                if t.get("ok"):
                    tool_ok += 1
                else:
                    tool_fail += 1
            elif isinstance(t, str):
                tools[t] += 1

    return {
        "n": len(rows),
        "built_at": datetime.now(timezone.utc).isoformat(),
        "mean_total_ms": round(sum(totals) / max(1, len(totals)), 1),
        "p95_total_ms": round(p95, 1),
        "paths": dict(paths),
        "tools": dict(tools.most_common(20)),
        "tool_ok": tool_ok,
        "tool_fail": tool_fail,
        "source": str(path or metrics_path()),
    }


def render_dashboard_html(summary: dict[str, Any] | None = None) -> str:
    s = summary or summarize_metrics()
    paths = s.get("paths") or {}
    tools = s.get("tools") or {}
    path_rows = "".join(
        f"<tr><td>{k}</td><td>{v}</td></tr>" for k, v in paths.items()
    )
    tool_rows = "".join(
        f"<tr><td>{k}</td><td>{v}</td></tr>" for k, v in tools.items()
    )
    return f"""<!doctype html>
<html lang="pt">
<head>
  <meta charset="utf-8"/>
  <title>FRIDAY ops metrics</title>
  <style>
    body {{ font-family: ui-sans-serif, system-ui, sans-serif; margin: 2rem; background:#0b1220; color:#e8fbff; }}
    h1 {{ font-weight: 600; letter-spacing: .04em; }}
    .cards {{ display:flex; gap:1rem; flex-wrap:wrap; margin: 1.5rem 0; }}
    .card {{ background:#121a2b; border:1px solid #2a3b55; padding:1rem 1.25rem; min-width:10rem; }}
    .card b {{ display:block; font-size:1.6rem; margin-top:.35rem; }}
    table {{ border-collapse: collapse; width: min(640px, 100%); margin-bottom: 1.5rem; }}
    th, td {{ border-bottom: 1px solid #243247; text-align:left; padding:.45rem .3rem; }}
    .muted {{ color:#8fb3c4; font-size:.9rem; }}
  </style>
</head>
<body>
  <h1>FRIDAY — métricas</h1>
  <p class="muted">Gerado {s.get('built_at')} · fonte {s.get('source')}</p>
  <div class="cards">
    <div class="card">Turns<b>{s.get('n', 0)}</b></div>
    <div class="card">Média ms<b>{s.get('mean_total_ms', 0)}</b></div>
    <div class="card">p95 ms<b>{s.get('p95_total_ms', 0)}</b></div>
    <div class="card">Tools OK/Fail<b>{s.get('tool_ok', 0)}/{s.get('tool_fail', 0)}</b></div>
  </div>
  <h2>Paths</h2>
  <table><thead><tr><th>path</th><th>n</th></tr></thead><tbody>{path_rows or '<tr><td colspan=2>sem dados</td></tr>'}</tbody></table>
  <h2>Tools</h2>
  <table><thead><tr><th>skill</th><th>n</th></tr></thead><tbody>{tool_rows or '<tr><td colspan=2>sem dados</td></tr>'}</tbody></table>
</body>
</html>
"""


def write_dashboard(
    out_html: str | Path = "data/metrics/dashboard.html",
    path: Path | None = None,
) -> dict[str, Any]:
    summary = summarize_metrics(path)
    dest = Path(out_html)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(render_dashboard_html(summary), encoding="utf-8")
    summary_path = dest.with_suffix(".json")
    summary_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return {**summary, "dashboard_html": str(dest), "dashboard_json": str(summary_path)}


def main() -> None:
    import argparse

    p = argparse.ArgumentParser(description="Build FRIDAY metrics dashboard")
    p.add_argument("--out", default="data/metrics/dashboard.html")
    args = p.parse_args()
    print(json.dumps(write_dashboard(args.out), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
