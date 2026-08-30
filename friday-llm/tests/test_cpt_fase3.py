"""Tests for Fase 3 CPT (no GPU / no HF download)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from friday_llm.training.common import (
    append_checkpoint_metric,
    find_latest_checkpoint,
    list_checkpoints,
    training_complete,
)
from friday_llm.training.continued_pretraining.select_checkpoint import (
    copy_best_adapter,
    pick_best_checkpoint,
)
from friday_llm.training.corpus.approval import approve_corpus, validate_approval
from friday_llm.training.cpt.cli import run_fase3
from friday_llm.util import load_yaml, resolve_path, write_jsonl


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


def test_fase3_configs_valid():
    cpt = load_yaml("friday-llm/configs/cpt_fase3.yaml")
    f3 = load_yaml("friday-llm/configs/fase3_cpt.yaml")
    assert cpt.get("phase") == "fase3"
    assert cpt.get("require_approval") is True
    assert cpt.get("use_smoke_model") is False
    assert f3.get("cpt_config")


def test_cpt_fase3_data_file_exists():
    cfg = load_yaml("friday-llm/configs/cpt_fase3.yaml")
    assert resolve_path(cfg["data_file"]).is_file()


def test_approve_corpus_writes_manifest(tmp_path: Path):
    data = tmp_path / "cpt.jsonl"
    write_jsonl(
        data,
        [{"text": "A F.R.I.D.A.Y. usa RAG e tools. " * 30, "metadata": {"source": "test"}}],
    )
    catalog = tmp_path / "catalog.jsonl"
    write_jsonl(
        catalog,
        [
            {
                "dataset_id": "fineweb2-fase1-cpt",
                "name": "Test CPT",
                "source": "test",
                "license": "Apache-2.0",
                "allowed_use": "research_training_with_attribution",
                "contains_personal_data": False,
                "processing_status": "ready",
                "included_in_training": True,
            }
        ],
    )
    out = tmp_path / "approval.json"
    manifest = approve_corpus(data, catalog_path=catalog, out_path=out)
    assert manifest["approved"] is True
    assert out.is_file()
    validate_approval(data, approval_path=out)


def test_approve_rejects_forbidden_path(tmp_path: Path):
    bad = tmp_path / "friday_eval.jsonl"
    write_jsonl(bad, [{"text": "x" * 200}])
    with pytest.raises(ValueError, match="forbidden"):
        approve_corpus(bad, catalog_path=tmp_path / "missing.jsonl", out_path=tmp_path / "a.json")


def test_list_checkpoints_and_pick_best(tmp_path: Path):
    _write_mock_checkpoint(tmp_path, 50, eval_loss=2.5, train_loss=3.0)
    _write_mock_checkpoint(tmp_path, 100, eval_loss=2.1, train_loss=2.8)
    rows = list_checkpoints(tmp_path)
    assert len(rows) == 2
    best = pick_best_checkpoint(tmp_path)
    assert best["step"] == 100
    assert best["eval_loss"] == 2.1


def test_copy_best_adapter(tmp_path: Path):
    _write_mock_checkpoint(tmp_path, 50, eval_loss=2.5, train_loss=3.0)
    _write_mock_checkpoint(tmp_path, 100, eval_loss=2.0, train_loss=2.7)
    dest = tmp_path / "best" / "adapter"
    sel = copy_best_adapter(tmp_path, dest)
    assert dest.is_dir()
    assert (dest / "adapter_config.json").is_file()
    assert sel["step"] == 100


def test_append_checkpoint_metric(tmp_path: Path):
    path = tmp_path / "metrics.jsonl"
    append_checkpoint_metric(path, step=10, eval_loss=1.5, train_loss=2.0, checkpoint_path="/ckpt")
    append_checkpoint_metric(path, step=20, eval_loss=1.2, train_loss=1.8, checkpoint_path="/ckpt2")
    lines = path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 2


def test_training_complete(tmp_path: Path):
    _write_mock_checkpoint(tmp_path, 300, eval_loss=2.0, train_loss=2.5)
    assert training_complete(tmp_path, 300) is True
    assert training_complete(tmp_path, 400) is False


def test_find_latest_checkpoint(tmp_path: Path):
    _write_mock_checkpoint(tmp_path, 50, eval_loss=2.5, train_loss=3.0)
    _write_mock_checkpoint(tmp_path, 100, eval_loss=2.1, train_loss=2.8)
    latest = find_latest_checkpoint(tmp_path)
    assert latest is not None
    assert latest.endswith("checkpoint-100")


def test_run_cpt_blocks_without_approval():
    from friday_llm.training.continued_pretraining.run import run_cpt

    approval = resolve_path("friday-llm/reports/corpus_approval.json")
    backup = None
    if approval.is_file():
        backup = approval.read_text(encoding="utf-8")
        approval.unlink()
    try:
        with pytest.raises(FileNotFoundError, match="approval"):
            run_cpt("friday-llm/configs/cpt_fase3.yaml")
    finally:
        if backup is not None:
            approval.write_text(backup, encoding="utf-8")


def test_fase3_report_only(tmp_path: Path, monkeypatch):
    approval_path = tmp_path / "corpus_approval.json"
    approval_path.write_text(
        json.dumps(
            {
                "approved": True,
                "file_path": "x",
                "content_hash": "abc",
                "document_count": 10,
                "token_count_est": 1000,
            }
        ),
        encoding="utf-8",
    )
    cfg_path = tmp_path / "fase3.yaml"
    cfg_path.write_text(
        f"""
run_id: test-fase3
cpt_config: friday-llm/configs/cpt_fase3.yaml
approval_path: {approval_path.as_posix()}
best_adapter_dir: {tmp_path.as_posix()}/best/adapter
selection_path: {tmp_path.as_posix()}/best/selection.json
report_md: {tmp_path.as_posix()}/phase3.md
report_json: {tmp_path.as_posix()}/phase3.json
""",
        encoding="utf-8",
    )
    result = run_fase3(str(cfg_path), only="report")
    assert result.get("run_id") == "test-fase3"
    assert Path(tmp_path / "phase3.md").is_file()
