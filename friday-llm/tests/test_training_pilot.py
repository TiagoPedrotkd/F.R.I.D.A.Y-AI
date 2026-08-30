"""Tests for Fase 2 pilot training (no GPU / no HF download)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from friday_llm.evaluation.compare_runs import compare_reports
from friday_llm.export.manifest import build_manifest, file_sha256
from friday_llm.training.common import find_latest_checkpoint
from friday_llm.training.pilot.cli import run_pilot
from friday_llm.util import load_yaml, resolve_path


def test_fase2_configs_exist_and_valid():
    for name in ("fase2_pilot.yaml", "cpt_fase2_pilot.yaml", "sft_fase2_pilot.yaml"):
        cfg = load_yaml(f"friday-llm/configs/{name}")
        assert cfg.get("run_id")


def test_cpt_fase2_config_points_to_fase1_data():
    cfg = load_yaml("friday-llm/configs/cpt_fase2_pilot.yaml")
    assert resolve_path(cfg["data_file"]).is_file()
    assert cfg["resume_from_checkpoint"] is True


def test_sft_fase2_config_points_to_fase1_sft():
    cfg = load_yaml("friday-llm/configs/sft_fase2_pilot.yaml")
    assert resolve_path(cfg["train_file"]).is_file()
    assert resolve_path(cfg["eval_file"]).is_file()


def test_find_latest_checkpoint(tmp_path: Path):
    (tmp_path / "checkpoint-10").mkdir()
    (tmp_path / "checkpoint-10" / "trainer_state.json").write_text("{}", encoding="utf-8")
    (tmp_path / "checkpoint-25").mkdir()
    (tmp_path / "checkpoint-25" / "trainer_state.json").write_text("{}", encoding="utf-8")
    latest = find_latest_checkpoint(tmp_path)
    assert latest is not None
    assert latest.endswith("checkpoint-25")


def test_compare_reports_without_pilot_eval():
    baseline = resolve_path("friday-llm/reports/baseline_phi4.json")
    if not baseline.is_file():
        pytest.skip("baseline not present")
    cmp = compare_reports(baseline, tmp_path_eval := Path("nonexistent_eval.json"))
    assert cmp["baseline"]["pass_rate"] is not None
    assert cmp["pilot"] is None


def test_compare_reports_with_fixtures(tmp_path: Path):
    base = {
        "model": "microsoft/phi-4",
        "pass_rate": 0.5,
        "mean_latency_s": 10.0,
        "results": [
            {"expect_tool": "get_current_datetime", "tool_ok": True},
            {"expect_tool": None, "tool_ok": True},
        ],
    }
    pilot = {
        "model": "pilot-model",
        "pass_rate": 0.6,
        "mean_latency_s": 8.0,
        "results": [
            {"expect_tool": "get_current_datetime", "tool_ok": True},
            {"expect_tool": "get_world_news", "tool_ok": False},
        ],
    }
    b_path = tmp_path / "base.json"
    p_path = tmp_path / "pilot.json"
    b_path.write_text(json.dumps(base), encoding="utf-8")
    p_path.write_text(json.dumps(pilot), encoding="utf-8")
    cmp = compare_reports(b_path, p_path)
    assert cmp["delta"]["pass_rate"] == 0.1
    assert cmp["baseline"]["tool_call_rate"] == 1.0
    assert cmp["pilot"]["tool_call_rate"] == 0.5


def test_manifest_sha256(tmp_path: Path):
    f = tmp_path / "adapter" / "adapter_config.json"
    f.parent.mkdir(parents=True)
    f.write_text('{"r": 16}', encoding="utf-8")
    assert file_sha256(f) == file_sha256(f)
    manifest = build_manifest(str(tmp_path / "adapter"), run_id="test")
    assert manifest["run_id"] == "test"
    assert manifest["production_model_unchanged"] is True
    assert len(manifest["files"]) == 1


def test_pilot_report_only_skip_train():
    result = run_pilot(
        "friday-llm/configs/fase2_pilot.yaml",
        only="report",
        skip_train=True,
    )
    assert result.get("run_id") == "friday-fase2-pilot"
    md = resolve_path("friday-llm/reports/phase2_pilot_report.md")
    stats = resolve_path("friday-llm/reports/phase2_pilot_stats.json")
    assert md.is_file()
    assert stats.is_file()
