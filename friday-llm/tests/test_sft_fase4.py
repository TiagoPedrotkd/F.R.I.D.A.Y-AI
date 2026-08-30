"""Tests for Fase 4 SFT (no GPU / no HF download)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from friday_llm.evaluation.eval_by_category import category_breakdown, compare_with_categories
from friday_llm.pipeline.build_datasets.sft_fase4_builder import build_fase4_dataset, write_fase4_datasets
from friday_llm.training.continued_pretraining.select_checkpoint import copy_best_adapter
from friday_llm.training.sft.approval import approve_sft_dataset, validate_sft_approval
from friday_llm.training.sft.cli import run_fase4
from friday_llm.util import load_yaml, read_jsonl, resolve_path, write_jsonl


def _write_mock_checkpoint(tmp_path: Path, step: int, eval_loss: float, train_loss: float) -> Path:
    ckpt = tmp_path / f"checkpoint-{step}"
    ckpt.mkdir(parents=True)
    state = {
        "global_step": step,
        "log_history": [
            {"step": step, "loss": train_loss},
            {"step": step, "eval_loss": eval_loss},
        ],
    }
    (ckpt / "trainer_state.json").write_text(json.dumps(state), encoding="utf-8")
    (ckpt / "adapter_config.json").write_text('{"r": 16}', encoding="utf-8")
    return ckpt


def test_fase4_configs_valid():
    sft = load_yaml("friday-llm/configs/sft_fase4.yaml")
    f4 = load_yaml("friday-llm/configs/fase4_sft.yaml")
    assert sft.get("phase") == "fase4"
    assert sft.get("require_approval") is True
    assert sft.get("use_smoke_model") is False
    assert f4.get("sft_config")


def test_build_fase4_dataset_categories():
    train, holdout, meta = build_fase4_dataset(seed=42)
    cats = set(meta["categories"])
    for required in ("conversation", "personality", "tool_calling", "safety"):
        assert required in cats
    assert len(train) > 0
    assert len(holdout) > 0
    for row in train + holdout:
        assert row.get("category")
        msgs = row.get("messages") or []
        assert msgs and msgs[0].get("role") == "system"


def test_write_fase4_datasets(tmp_path: Path):
    train_path = tmp_path / "train.jsonl"
    holdout_path = tmp_path / "holdout.jsonl"
    stats_path = tmp_path / "stats.json"
    meta = write_fase4_datasets(
        train_path=str(train_path),
        holdout_path=str(holdout_path),
        stats_path=str(stats_path),
        seed=7,
    )
    assert train_path.is_file()
    assert holdout_path.is_file()
    assert stats_path.is_file()
    assert meta["train"] == len(read_jsonl(train_path))


def test_approve_sft_dataset(tmp_path: Path):
    train, holdout, _ = build_fase4_dataset(seed=1)
    train_path = tmp_path / "train.jsonl"
    holdout_path = tmp_path / "holdout.jsonl"
    write_jsonl(train_path, train)
    write_jsonl(holdout_path, holdout)
    out = tmp_path / "approval.json"
    manifest = approve_sft_dataset(train_path, holdout_path, out_path=out)
    assert manifest["approved"] is True
    validate_sft_approval(train_path, holdout_path, approval_path=out)


def test_approve_rejects_missing_category(tmp_path: Path):
    row = {
        "category": "conversation",
        "messages": [
            {"role": "system", "content": "sys"},
            {"role": "user", "content": "hi"},
            {"role": "assistant", "content": "hello"},
        ],
    }
    train_path = tmp_path / "train.jsonl"
    write_jsonl(train_path, [row])
    with pytest.raises(ValueError, match="NOT approved"):
        approve_sft_dataset(train_path, tmp_path / "holdout.jsonl", out_path=tmp_path / "a.json")


def test_category_breakdown():
    report = {
        "results": [
            {"category": "safety", "pass": True, "expect_tool": False},
            {"category": "safety", "pass": False, "expect_tool": False},
            {"category": "tool_calling", "pass": True, "expect_tool": True, "tool_ok": True},
        ]
    }
    by_cat = category_breakdown(report)
    assert by_cat["safety"]["n"] == 2
    assert by_cat["safety"]["pass_rate"] == 0.5
    assert by_cat["tool_calling"]["tool_call_rate"] == 1.0


def test_compare_with_categories(tmp_path: Path):
    baseline = {
        "pass_rate": 0.5,
        "results": [{"category": "safety", "pass": True}],
    }
    candidate = {
        "pass_rate": 0.6,
        "results": [{"category": "safety", "pass": True}, {"category": "safety", "pass": False}],
    }
    b_path = tmp_path / "baseline.json"
    c_path = tmp_path / "candidate.json"
    b_path.write_text(json.dumps(baseline), encoding="utf-8")
    c_path.write_text(json.dumps(candidate), encoding="utf-8")
    cmp = compare_with_categories(b_path, c_path)
    assert cmp["baseline_by_category"]["safety"]["n"] == 1
    assert cmp["candidate_by_category"]["safety"]["n"] == 2


def test_copy_best_sft_checkpoint(tmp_path: Path):
    _write_mock_checkpoint(tmp_path, 20, eval_loss=1.8, train_loss=2.0)
    _write_mock_checkpoint(tmp_path, 40, eval_loss=1.5, train_loss=1.9)
    dest = tmp_path / "best" / "adapter"
    sel = copy_best_adapter(tmp_path, dest)
    assert sel["step"] == 40
    assert (dest / "adapter_config.json").is_file()


def test_run_sft_blocks_without_approval():
    from friday_llm.training.sft.run import run_sft

    approval = resolve_path("friday-llm/reports/sft_approval.json")
    backup = None
    if approval.is_file():
        backup = approval.read_text(encoding="utf-8")
        approval.unlink()
    try:
        with pytest.raises(FileNotFoundError, match="approval"):
            run_sft("friday-llm/configs/sft_fase4.yaml")
    finally:
        if backup is not None:
            approval.write_text(backup, encoding="utf-8")


def test_fase4_report_only(tmp_path: Path):
    cfg_path = tmp_path / "fase4.yaml"
    cfg_path.write_text(
        f"""
run_id: test-fase4
seed: 42
sft_config: friday-llm/configs/sft_fase4.yaml
approval_path: {tmp_path.as_posix()}/sft_approval.json
best_adapter_dir: {tmp_path.as_posix()}/best/adapter
selection_path: {tmp_path.as_posix()}/best/selection.json
baseline_path: friday-llm/reports/baseline_phi4.json
eval_out_path: friday-llm/reports/baseline_phi4.json
report_md: {tmp_path.as_posix()}/phase4.md
report_json: {tmp_path.as_posix()}/phase4.json
run_eval: false
""",
        encoding="utf-8",
    )
    result = run_fase4(str(cfg_path), only="report")
    assert result.get("run_id") == "test-fase4"
    assert Path(tmp_path / "phase4.md").is_file()
