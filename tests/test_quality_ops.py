"""Tests for continuous quality + product polish."""

from __future__ import annotations

import json
from pathlib import Path

from friday.llm.planner import _should_invoke_llm_planner, plan_steps_hybrid
from friday.llm.vision import pick_vision_model
from friday.quality.feedback_to_datasets import (
    export_feedback_datasets,
    hard_case_to_eval_item,
    hard_case_to_sft_row,
)
from friday.quality.metrics_dashboard import (
    append_turn_metric,
    summarize_metrics,
    write_dashboard,
)


def test_hard_case_to_sft_and_eval():
    row = {
        "user_text": "Qual o preco do bitcoin?",
        "reply_text": "Esta a 1 milhao com certeza.",
        "comment": "inventou",
        "rating": "down",
    }
    sft = hard_case_to_sft_row(row)
    assert sft and len(sft["messages"]) >= 4
    assert sft["messages"][0]["role"] == "system"
    ev = hard_case_to_eval_item(row, idx=1)
    assert ev and ev["category"] == "feedback_hard"
    assert "bitcoin" in ev["input"].casefold()


def test_export_feedback_datasets(tmp_path: Path):
    fb = tmp_path / "feedback.jsonl"
    fb.write_text(
        json.dumps(
            {
                "rating": "down",
                "user_text": "noticias de hoje",
                "reply_text": "nao sei",
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    out = export_feedback_datasets(
        fb,
        sft_out=tmp_path / "sft.jsonl",
        eval_out=tmp_path / "eval.jsonl",
        report_dir=tmp_path / "reports",
    )
    assert out["sft_rows"] == 1
    assert out["eval_rows"] == 1
    assert Path(out["sft_path"]).is_file()
    assert Path(out["eval_latest"]).is_file()


def test_metrics_dashboard(tmp_path: Path):
    path = tmp_path / "turns.jsonl"
    append_turn_metric({"path": "stream", "total_ms": 120, "tools": []}, path=path)
    append_turn_metric(
        {
            "path": "stream_tools",
            "total_ms": 400,
            "tools": [{"name": "search_docs", "ms": 50, "ok": True}],
        },
        path=path,
    )
    summary = summarize_metrics(path)
    assert summary["n"] == 2
    assert summary["mean_total_ms"] == 260.0
    dash = write_dashboard(tmp_path / "dashboard.html", path=path)
    assert Path(dash["dashboard_html"]).is_file()
    html = Path(dash["dashboard_html"]).read_text(encoding="utf-8")
    assert "FRIDAY" in html
    assert "search_docs" in html


def test_planner_aggressive_triggers():
    assert _should_invoke_llm_planner(
        "pesquisa o manual e depois a web", mode="hint"
    )
    assert _should_invoke_llm_planner(
        "pesquisa docs sobre VLAN e calcula 2+2", mode="aggressive"
    )
    assert not _should_invoke_llm_planner("ola", mode="aggressive")
    # Without client, hybrid returns []
    assert plan_steps_hybrid("ola", mode="aggressive") == []


def test_pick_vision_prefers_small_loaded():
    picked = pick_vision_model(
        ["microsoft/phi-4", "qwen2-vl-7b-instruct", "moondream-2b"]
    )
    assert picked and "moondream" in picked.casefold()
