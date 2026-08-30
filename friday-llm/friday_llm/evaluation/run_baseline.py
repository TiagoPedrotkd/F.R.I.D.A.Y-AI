"""Baseline evaluation against LM Studio (production Phi-4 by default)."""

from __future__ import annotations

import argparse
import json
import logging
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from friday_llm.util import read_jsonl, resolve_path

logger = logging.getLogger(__name__)

KNOWN_TOOLS = {
    "get_current_datetime",
    "get_current_time",
    "get_world_news",
    "get_news",
    "get_world_finance_news",
    "get_finance",
    "get_country_briefing",
    "list_supported_countries",
    "open_world_monitor",
    "open_finance_world_monitor",
    "search_web",
    "search_docs",
    "fetch_url",
    "get_system_info",
    "word_count",
    "format_json",
    "summarize",
    "explain_code",
    "remember",
    "recall",
    "tell_joke",
}


def _client():
    from openai import OpenAI

    base = os.getenv("LM_STUDIO_BASE_URL_HOST", "http://localhost:1234/v1")
    key = os.getenv("LM_STUDIO_API_KEY", "lm-studio")
    return OpenAI(base_url=base, api_key=key, timeout=60.0, max_retries=0)


def _model_id() -> str:
    return os.getenv("LM_STUDIO_MODEL", "microsoft/phi-4")


def _tool_schemas_minimal() -> list[dict[str, Any]]:
    return [
        {
            "type": "function",
            "function": {
                "name": "get_current_datetime",
                "description": "Current date/time",
                "parameters": {"type": "object", "properties": {}},
            },
        },
        {
            "type": "function",
            "function": {
                "name": "get_world_news",
                "description": "News headlines by country",
                "parameters": {
                    "type": "object",
                    "properties": {"country": {"type": "string"}},
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "get_world_finance_news",
                "description": "Finance headlines",
                "parameters": {
                    "type": "object",
                    "properties": {"country": {"type": "string"}},
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "get_system_info",
                "description": "Local system info",
                "parameters": {"type": "object", "properties": {}},
            },
        },
        {
            "type": "function",
            "function": {
                "name": "search_web",
                "description": "Web search",
                "parameters": {
                    "type": "object",
                    "properties": {"query": {"type": "string"}},
                    "required": ["query"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "search_docs",
                "description": "Search authorized internal project documents",
                "parameters": {
                    "type": "object",
                    "properties": {"query": {"type": "string"}},
                    "required": ["query"],
                },
            },
        },
    ]


def _extract_tool_names(message: Any) -> list[str]:
    names: list[str] = []
    tool_calls = getattr(message, "tool_calls", None) or []
    for tc in tool_calls:
        fn = getattr(tc, "function", None)
        if fn and getattr(fn, "name", None):
            names.append(fn.name)
    content = (getattr(message, "content", None) or "") if message else ""
    if isinstance(content, str) and "call_tool" in content:
        m = re.search(r'"name"\s*:\s*"([^"]+)"', content)
        if m:
            names.append(m.group(1))
    return names


def _score_item(item: dict[str, Any], message: Any, latency_s: float) -> dict[str, Any]:
    content = getattr(message, "content", None) or ""
    if not isinstance(content, str):
        content = str(content)
    tools = _extract_tool_names(message)
    expect = item.get("expect_tool")
    tool_ok = True
    if expect:
        aliases = {expect}
        if expect == "get_current_datetime":
            aliases.add("get_current_time")
        if expect == "get_world_news":
            aliases.add("get_news")
        if expect == "get_world_finance_news":
            aliases.add("get_finance")
        tool_ok = any(t in aliases for t in tools)
    phantom = [t for t in tools if t not in KNOWN_TOOLS]
    voice_ok = True
    if item.get("category") == "voice_style":
        voice_ok = len(content) < 600 and "#" not in content and "```" not in content
    return {
        "id": item.get("id"),
        "category": item.get("category"),
        "language": item.get("language"),
        "latency_s": round(latency_s, 3),
        "tool_ok": tool_ok,
        "tools_called": tools,
        "phantom_tools": phantom,
        "voice_ok": voice_ok,
        "reply_preview": content[:240],
        "pass": tool_ok and not phantom and voice_ok,
    }


def run_baseline(
    eval_path: str = "friday-llm/data/evaluation/friday_eval.jsonl",
    out_path: str = "friday-llm/reports/baseline_phi4.json",
    *,
    limit: int | None = None,
) -> dict[str, Any]:
    items = read_jsonl(resolve_path(eval_path))
    if limit:
        items = items[:limit]
    client = _client()
    model = _model_id()
    # ping
    models = client.models.list()
    available = [m.id for m in models.data]
    system = (
        "Tu es a F.R.I.D.A.Y. Portugues europeu por defeito. "
        "Respostas curtas para voz. Usa tools para dados actuais. "
        "Nao inventes ferramentas."
    )
    results = []
    for item in items:
        t0 = time.perf_counter()
        try:
            resp = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": item["input"]},
                ],
                tools=_tool_schemas_minimal(),
                tool_choice="auto",
                max_tokens=256,
                temperature=0.3,
            )
            message = resp.choices[0].message
            latency = time.perf_counter() - t0
            results.append(_score_item(item, message, latency))
        except Exception as exc:  # noqa: BLE001
            results.append(
                {
                    "id": item.get("id"),
                    "error": str(exc),
                    "pass": False,
                    "latency_s": round(time.perf_counter() - t0, 3),
                }
            )

    passed = sum(1 for r in results if r.get("pass"))
    report = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "model": model,
        "available_models": available,
        "eval_path": eval_path,
        "n": len(results),
        "passed": passed,
        "pass_rate": round(passed / len(results), 3) if results else 0.0,
        "mean_latency_s": round(
            sum(r.get("latency_s", 0) for r in results) / len(results), 3
        )
        if results
        else 0.0,
        "results": results,
        "notes": (
            "Baseline only. Does not prove overall intelligence. "
            "Compare future CPT/SFT/RAG runs against this file."
        ),
    }
    out = resolve_path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info("Wrote %s (pass_rate=%s)", out, report["pass_rate"])
    return report


def main(argv: list[str] | None = None) -> None:
    logging.basicConfig(level=logging.INFO)
    p = argparse.ArgumentParser()
    p.add_argument("--eval", default="friday-llm/data/evaluation/friday_eval.jsonl")
    p.add_argument("--out", default="friday-llm/reports/baseline_phi4.json")
    p.add_argument("--limit", type=int, default=None)
    args = p.parse_args(argv)
    report = run_baseline(args.eval, args.out, limit=args.limit)
    print(json.dumps({k: report[k] for k in report if k != "results"}, indent=2))
    print(f"full report: {args.out}")


if __name__ == "__main__":
    main()
