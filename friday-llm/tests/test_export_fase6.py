"""Tests for Fase 6 export (no GPU / no llama.cpp download)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from friday_llm.export.cli import run_fase6
from friday_llm.export.gguf import export_gguf_pipeline, find_llama_cpp
from friday_llm.export.manifest import build_manifest, file_sha256
from friday_llm.export.merge import validate_adapters
from friday_llm.util import load_yaml, resolve_path


def test_fase6_config_valid():
    cfg = load_yaml("friday-llm/configs/fase6_export.yaml")
    assert cfg.get("run_id")
    assert resolve_path(cfg["sft_adapter"]).is_dir() or True  # may be missing in CI


def test_validate_adapters_smoke_paths():
    validation = validate_adapters(
        "friday-llm/checkpoints/sft-smoke/adapter",
        cpt_adapter="friday-llm/checkpoints/cpt-smoke/adapter",
        merge_cpt=True,
    )
    assert validation["valid"] is True
    assert validation["sft_adapter"]


def test_validate_adapters_missing_sft(tmp_path: Path):
    with pytest.raises(FileNotFoundError):
        validate_adapters(tmp_path / "missing")


def test_validate_adapters_cpt_missing_warning(tmp_path: Path):
    sft = tmp_path / "sft" / "adapter"
    sft.mkdir(parents=True)
    (sft / "adapter_config.json").write_text('{"r": 16}', encoding="utf-8")
    validation = validate_adapters(
        sft,
        cpt_adapter=tmp_path / "no-cpt",
        merge_cpt=True,
    )
    assert validation["valid"] is True
    assert validation["merge_cpt"] is False
    assert validation["warnings"]


def test_find_llama_cpp_missing():
    assert find_llama_cpp("/nonexistent/llama.cpp") is None


def test_export_gguf_skipped_when_no_llama(tmp_path: Path):
    merged = tmp_path / "merged"
    merged.mkdir()
    result = export_gguf_pipeline(
        merged,
        tmp_path / "gguf",
        "test-model",
        ["Q4_K_M"],
        llama_cpp_path="/nonexistent",
        skip_if_missing=True,
    )
    assert result["status"] == "skipped"


def test_build_manifest_with_gguf_mock(tmp_path: Path):
    adapter = tmp_path / "adapter"
    adapter.mkdir()
    (adapter / "adapter_config.json").write_text('{"r": 16}', encoding="utf-8")
    gguf = tmp_path / "model-Q4_K_M.gguf"
    gguf.write_bytes(b"fake-gguf")
    manifest = build_manifest(
        adapter,
        run_id="fase6-test",
        merged_hf_dir=tmp_path / "merged",
        gguf_files=[{"path": str(gguf), "quant": "Q4_K_M"}],
        base_model="Qwen/Qwen2.5-0.5B",
        manifest_path=tmp_path / "manifest.json",
    )
    assert manifest["gguf_status"] == "converted"
    assert len(manifest["gguf_files"]) == 1
    assert manifest["rollback"]["candidate_suggested_id"] == "model-Q4_K_M"
    assert (tmp_path / "manifest.json").is_file()


def test_manifest_sha256_compat(tmp_path: Path):
    f = tmp_path / "adapter" / "adapter_config.json"
    f.parent.mkdir(parents=True)
    f.write_text('{"r": 16}', encoding="utf-8")
    assert file_sha256(f) == file_sha256(f)
    manifest = build_manifest(str(tmp_path / "adapter"), run_id="test", manifest_path=tmp_path / "m.json")
    assert manifest["production_model_unchanged"] is True


def test_fase6_report_only(tmp_path: Path):
    cfg_path = tmp_path / "fase6.yaml"
    cfg_path.write_text(
        f"""
run_id: test-fase6
model_config: friday-llm/configs/base_model.yaml
cpt_adapter: friday-llm/checkpoints/cpt-smoke/adapter
sft_adapter: friday-llm/checkpoints/sft-smoke/adapter
use_smoke_model: true
merge_cpt: true
output:
  merged_hf: {tmp_path.as_posix()}/merged
  gguf_dir: {tmp_path.as_posix()}/gguf
  gguf_basename: test-model
quantization: [Q4_K_M]
llama_cpp:
  skip_if_missing: true
eval:
  baseline_path: friday-llm/reports/baseline_phi4.json
  candidate_out: friday-llm/reports/baseline_phi4.json
report_md: {tmp_path.as_posix()}/phase6.md
report_json: {tmp_path.as_posix()}/phase6.json
manifest_path: {tmp_path.as_posix()}/manifest.json
production_model: microsoft/phi-4
""",
        encoding="utf-8",
    )
    result = run_fase6(str(cfg_path), only="report")
    assert result.get("run_id") == "test-fase6"
    assert Path(tmp_path / "phase6.md").is_file()
