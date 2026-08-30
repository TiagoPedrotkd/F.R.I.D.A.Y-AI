"""Tests for incremental CPT planner."""

from __future__ import annotations

from pathlib import Path

from friday_llm.training.incremental.planner import (
    IncrementalState,
    prepare_day,
    steps_for_new_docs,
)
from friday_llm.util import write_jsonl


def test_steps_for_new_docs():
    assert steps_for_new_docs(10) == 40
    assert steps_for_new_docs(1) == 20  # min_steps
    assert steps_for_new_docs(0) == 0


def test_prepare_day_cumulative(tmp_path: Path):
    source = tmp_path / "source.jsonl"
    rows = [{"text": f"doc {i} " * 20, "content_hash": f"h{i}"} for i in range(30)]
    write_jsonl(source, rows)

    st = IncrementalState(
        source=str(source),
        cumulative=str(tmp_path / "cum.jsonl"),
        manifest=str(tmp_path / "manifest.jsonl"),
        used_hashes=str(tmp_path / "used.json"),
        output_dir=str(tmp_path / "out"),
        pool_total=30,
        config_dir=str(tmp_path / "configs"),
        progress_json=str(tmp_path / "progress.json"),
        progress_md=str(tmp_path / "progress.md"),
        data_file_rel=str(tmp_path / "cum.jsonl").replace("\\", "/"),
        output_dir_rel=str(tmp_path / "out").replace("\\", "/"),
    )
    p1 = prepare_day(1, 10, state=st, write_script=False)
    assert p1["added_this_day"] == 10
    assert p1["cumulative_docs"] == 10
    assert p1["max_steps"] == 40

    p2 = prepare_day(2, 5, state=st, write_script=False)
    assert p2["added_this_day"] == 5
    assert p2["cumulative_docs"] == 15
    assert p2["docs_used"] == 15
    # planned max from day 1 (40) + 20 even without a checkpoint yet
    assert p2["planned_base"] == 40
    assert p2["max_steps"] == 60
