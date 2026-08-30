"""Fase 6 export orchestrator: validate → merge → gguf → manifest → eval → report."""

from __future__ import annotations

import argparse
import json
import logging
from datetime import datetime, timezone
from typing import Any

from friday_llm.evaluation.compare_runs import compare_reports
from friday_llm.evaluation.run_baseline import run_baseline
from friday_llm.export.gguf import export_gguf_pipeline, find_llama_cpp
from friday_llm.export.manifest import build_manifest
from friday_llm.export.merge import merge_to_hf, validate_adapters
from friday_llm.training.common import select_model_id
from friday_llm.util import load_yaml, resolve_path

logger = logging.getLogger(__name__)


def _write_phase6_report(
    cfg: dict[str, Any],
    *,
    validation: dict | None,
    merge_report: dict | None,
    gguf_report: dict | None,
    manifest: dict | None,
    eval_comparison: dict | None,
    eval_gate_passed: bool | None,
) -> dict[str, Any]:
    stats: dict[str, Any] = {
        "run_id": cfg.get("run_id"),
        "finished_at": datetime.now(timezone.utc).isoformat(),
        "validation": validation,
        "merge": merge_report,
        "gguf": gguf_report,
        "manifest": {
            "path": cfg.get("manifest_path"),
            "gguf_status": manifest.get("gguf_status") if manifest else None,
            "gguf_file_count": len(manifest.get("gguf_files") or []) if manifest else 0,
        },
        "eval_comparison": eval_comparison,
        "eval_gate_passed": eval_gate_passed,
        "production_model_unchanged": True,
        "production_model": cfg.get("production_model") or "microsoft/phi-4",
        "rollback": manifest.get("rollback") if manifest else None,
        "notes": str(cfg.get("notes") or ""),
    }
    json_path = resolve_path(cfg.get("report_json") or "friday-llm/reports/phase6_export_stats.json")
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(stats, ensure_ascii=False, indent=2), encoding="utf-8")

    md_path = resolve_path(cfg.get("report_md") or "friday-llm/reports/phase6_export_report.md")
    lines = [
        "# Fase 6 — Export modelo final",
        "",
        f"**Run:** `{cfg.get('run_id')}`  ",
        f"**Gerado:** {stats['finished_at']}",
        "",
        "## Validação",
        "",
    ]
    if validation:
        lines += [
            f"- SFT: `{validation.get('sft_adapter')}`",
            f"- CPT: `{validation.get('cpt_adapter') or '—'}`",
            f"- Merge CPT: {validation.get('merge_cpt')}",
        ]
        for w in validation.get("warnings") or []:
            lines.append(f"- Aviso: {w}")
    lines += ["", "## Merge HF", ""]
    if merge_report:
        lines += [
            f"- Base: `{merge_report.get('base_model')}`",
            f"- Output: `{merge_report.get('merged_hf_dir')}`",
            f"- CPT fundido: {merge_report.get('merged_cpt')}",
        ]
    lines += ["", "## GGUF", ""]
    if gguf_report:
        lines.append(f"- Status: **{gguf_report.get('status')}**")
        for f in gguf_report.get("files") or []:
            lines.append(f"- `{f.get('quant')}` → `{f.get('path')}`")
        for err in gguf_report.get("errors") or []:
            lines.append(f"- Erro: {err}")
    else:
        lines.append("_GGUF não gerado._")
    lines += ["", "## Manifesto", ""]
    if manifest:
        lines += [
            f"- Ficheiro: `{cfg.get('manifest_path')}`",
            f"- GGUF status: `{manifest.get('gguf_status')}`",
            f"- Rollback: repor `{manifest.get('rollback', {}).get('env_var')}` = "
            f"`{manifest.get('rollback', {}).get('production_value')}`",
        ]
    lines += ["", "## Avaliação vs baseline", ""]
    if eval_comparison:
        b = eval_comparison.get("baseline") or {}
        p = eval_comparison.get("pilot") or {}
        d = eval_comparison.get("delta") or {}
        lines += [
            "| Métrica | Phi-4 | Modelo exportado | Delta |",
            "|---------|-------|------------------|-------|",
            f"| pass_rate | {b.get('pass_rate', '—')} | {p.get('pass_rate', '—')} | {d.get('pass_rate', '—')} |",
            f"| mean_latency_s | {b.get('mean_latency_s', '—')} | {p.get('mean_latency_s', '—')} | {d.get('mean_latency_s', '—')} |",
            "",
            f"- Gate eval: **{'PASS' if eval_gate_passed else 'FAIL / não corrido'}**",
        ]
    else:
        lines.append("_Eval LM Studio não corrida. Usar `--run-eval` com modelo carregado._")
    lines += [
        "",
        "## LM Studio",
        "",
        "1. Importar `friday-llm/export/gguf/*-Q4_K_M.gguf`",
        "2. Testar com `$env:LM_STUDIO_MODEL = \"<model-id>\"`",
        "3. Rollback: ver [`export/rollback.md`](../export/rollback.md)",
        "",
    ]
    md_path.write_text("\n".join(lines), encoding="utf-8")
    logger.info("Phase 6 export report → %s", md_path)
    return stats


def run_fase6(
    config_path: str,
    *,
    only: str | None = None,
    run_eval: bool | None = None,
) -> dict[str, Any]:
    cfg = load_yaml(config_path)
    if run_eval is not None:
        cfg["run_eval"] = run_eval

    steps = ["validate", "merge", "gguf", "manifest", "eval", "report"]
    if only:
        steps = [only]

    base_cfg = load_yaml(cfg["model_config"])
    use_smoke = bool(cfg.get("use_smoke_model", False))
    base_model = select_model_id(base_cfg, use_smoke)
    out_cfg = cfg.get("output") or {}
    llama_cfg = cfg.get("llama_cpp") or {}
    eval_cfg = cfg.get("eval") or {}

    validation: dict | None = None
    merge_report: dict | None = None
    gguf_report: dict | None = None
    manifest: dict | None = None
    eval_comparison: dict | None = None
    eval_gate_passed: bool | None = None

    if "validate" in steps:
        validation = validate_adapters(
            cfg["sft_adapter"],
            cpt_adapter=cfg.get("cpt_adapter"),
            merge_cpt=bool(cfg.get("merge_cpt", True)),
        )

    if "merge" in steps:
        validation = validation or validate_adapters(
            cfg["sft_adapter"],
            cpt_adapter=cfg.get("cpt_adapter"),
            merge_cpt=bool(cfg.get("merge_cpt", True)),
        )
        merge_report = merge_to_hf(
            base_model,
            cfg["sft_adapter"],
            out_cfg.get("merged_hf") or "friday-llm/export/merged-friday-v1",
            cpt_adapter=cfg.get("cpt_adapter") if validation.get("merge_cpt") else None,
            merge_cpt=bool(validation.get("merge_cpt")),
        )

    if "gguf" in steps:
        merged = (merge_report or {}).get("merged_hf_dir") or out_cfg.get("merged_hf")
        gguf_report = export_gguf_pipeline(
            merged,
            out_cfg.get("gguf_dir") or "friday-llm/export/gguf",
            out_cfg.get("gguf_basename") or "friday-model-v1",
            list(cfg.get("quantization") or ["Q4_K_M"]),
            llama_cpp_path=llama_cfg.get("path") or None,
            skip_if_missing=bool(llama_cfg.get("skip_if_missing", True)),
        )

    if "manifest" in steps:
        gguf_files = (gguf_report or {}).get("files")
        gguf_status = (gguf_report or {}).get("status")
        if gguf_status == "skipped":
            gguf_status = "skipped"
        manifest = build_manifest(
            cfg["sft_adapter"],
            run_id=str(cfg.get("run_id") or "fase6-export"),
            merged_hf_dir=(merge_report or {}).get("merged_hf_dir") or out_cfg.get("merged_hf"),
            gguf_files=gguf_files,
            gguf_status=gguf_status,
            base_model=base_model,
            production_model=str(cfg.get("production_model") or "microsoft/phi-4"),
            manifest_path=cfg.get("manifest_path"),
        )

    if "eval" in steps and cfg.get("run_eval"):
        run_baseline(
            str(cfg.get("eval_path") or "friday-llm/data/evaluation/friday_eval.jsonl"),
            str(eval_cfg.get("candidate_out") or "friday-llm/reports/phase6_eval_final.json"),
        )

    eval_out = resolve_path(eval_cfg.get("candidate_out") or "friday-llm/reports/phase6_eval_final.json")
    eval_comparison = compare_reports(
        eval_cfg.get("baseline_path") or "friday-llm/reports/baseline_phi4.json",
        eval_out,
    )
    if eval_comparison.get("pilot") and eval_comparison.get("delta") is not None:
        min_delta = float(eval_cfg.get("min_pass_rate_delta") or -0.05)
        delta = float((eval_comparison.get("delta") or {}).get("pass_rate") or -999)
        eval_gate_passed = delta >= min_delta

    if "report" in steps or only is None:
        if validation is None:
            try:
                validation = validate_adapters(
                    cfg["sft_adapter"],
                    cpt_adapter=cfg.get("cpt_adapter"),
                    merge_cpt=bool(cfg.get("merge_cpt", True)),
                )
            except FileNotFoundError:
                validation = {"valid": False}
        if manifest is None:
            mp = resolve_path(cfg.get("manifest_path") or "friday-llm/reports/export_manifest.json")
            if mp.is_file():
                manifest = json.loads(mp.read_text(encoding="utf-8"))
        return _write_phase6_report(
            cfg,
            validation=validation,
            merge_report=merge_report,
            gguf_report=gguf_report,
            manifest=manifest,
            eval_comparison=eval_comparison,
            eval_gate_passed=eval_gate_passed,
        )

    return {
        "validation": validation,
        "merge": merge_report,
        "gguf": gguf_report,
        "manifest": manifest,
        "eval_comparison": eval_comparison,
        "eval_gate_passed": eval_gate_passed,
        "llama_cpp_found": find_llama_cpp(llama_cfg.get("path") or None) is not None,
    }


def main(argv: list[str] | None = None) -> None:
    logging.basicConfig(level=logging.INFO)
    p = argparse.ArgumentParser(description="FRIDAY LLM Fase 6 export")
    p.add_argument("--config", default="friday-llm/configs/fase6_export.yaml")
    p.add_argument(
        "--only",
        choices=["validate", "merge", "gguf", "manifest", "eval", "report"],
        default=None,
    )
    p.add_argument("--run-eval", action="store_true")
    args = p.parse_args(argv)
    result = run_fase6(args.config, only=args.only, run_eval=args.run_eval if args.run_eval else None)
    print(json.dumps(result, ensure_ascii=True, indent=2, default=str))


if __name__ == "__main__":
    main()
