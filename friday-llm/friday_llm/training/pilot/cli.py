"""Fase 2 pilot orchestrator: CPT → SFT → eval → manifest → report."""

from __future__ import annotations

import argparse
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from friday_llm.evaluation.compare_runs import compare_reports
from friday_llm.evaluation.run_baseline import run_baseline
from friday_llm.export.manifest import build_manifest
from friday_llm.training.continued_pretraining.run import run_cpt
from friday_llm.training.sft.run import run_sft
from friday_llm.util import load_yaml, resolve_path

logger = logging.getLogger(__name__)


def _write_pilot_report(
    cfg: dict[str, Any],
    *,
    cpt_report: dict | None,
    sft_report: dict | None,
    comparison: dict,
    manifest: dict | None,
) -> dict[str, Any]:
    stats: dict[str, Any] = {
        "run_id": cfg.get("run_id"),
        "finished_at": datetime.now(timezone.utc).isoformat(),
        "cpt": cpt_report,
        "sft": sft_report,
        "eval_comparison": comparison,
        "manifest": {
            "adapter_dir": manifest.get("adapter_dir") if manifest else None,
            "gguf_status": manifest.get("gguf_status") if manifest else None,
            "file_count": len(manifest.get("files") or []) if manifest else 0,
        },
        "production_model_unchanged": True,
        "lm_studio_default": "microsoft/phi-4",
        "notes": str(cfg.get("notes") or ""),
    }
    json_path = resolve_path(cfg.get("report_json") or "friday-llm/reports/phase2_pilot_stats.json")
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(stats, ensure_ascii=False, indent=2), encoding="utf-8")

    md_path = resolve_path(cfg.get("report_md") or "friday-llm/reports/phase2_pilot_report.md")
    b = comparison.get("baseline") or {}
    p = comparison.get("pilot") or {}
    d = comparison.get("delta") or {}
    lines = [
        "# Fase 2 — Relatório Piloto (FRIDAY LLM)",
        "",
        f"**Run:** `{cfg.get('run_id')}`  ",
        f"**Gerado:** {stats['finished_at']}",
        "",
        "## Treino",
        "",
    ]
    if cpt_report:
        lines += [
            f"- CPT: `{cpt_report.get('output_dir')}` — loss {cpt_report.get('train_loss'):.4f}",
            f"  - Modelo: {cpt_report.get('base_model')} ({cpt_report.get('quant_mode')})",
            f"  - Docs: {cpt_report.get('n_source_docs')} | Resume: {cpt_report.get('resumed_from')}",
        ]
    if sft_report:
        lines += [
            f"- SFT: `{sft_report.get('output_dir')}` — loss {sft_report.get('train_loss'):.4f}",
            f"  - Train/eval: {sft_report.get('n_train')}/{sft_report.get('n_eval')}",
            f"  - Resume: {sft_report.get('resumed_from')}",
        ]
    lines += [
        "",
        "## Avaliação vs baseline",
        "",
        "| Métrica | Phi-4 baseline | Piloto pós-SFT | Delta |",
        "|---------|----------------|----------------|-------|",
        f"| pass_rate | {b.get('pass_rate', '—')} | {p.get('pass_rate', '—')} | {d.get('pass_rate', '—')} |",
        f"| mean_latency_s | {b.get('mean_latency_s', '—')} | {p.get('mean_latency_s', '—')} | {d.get('mean_latency_s', '—')} |",
        f"| tool_call_rate | {b.get('tool_call_rate', '—')} | {p.get('tool_call_rate', '—')} | {d.get('tool_call_rate', '—')} |",
        "",
        "## Export LM Studio",
        "",
        f"- Adapter: `{cfg.get('manifest_adapter')}`",
        f"- Manifest: `friday-llm/reports/export_manifest.json`",
        f"- Guia: [`export/lm_studio_guide.md`](../export/lm_studio_guide.md)",
        "",
        "## Avisos",
        "",
        "- Subset piloto **não** equivale a conhecimento geral.",
        "- `LM_STUDIO_MODEL` em produção permanece `microsoft/phi-4`.",
        "- Eval piloto requer modelo carregado manualmente no LM Studio.",
        "",
    ]
    md_path.write_text("\n".join(lines), encoding="utf-8")
    logger.info("Pilot report → %s", md_path)
    return stats


def run_pilot(
    config_path: str,
    *,
    only: str | None = None,
    resume: bool = False,
    skip_train: bool = False,
    run_eval: bool | None = None,
) -> dict[str, Any]:
    cfg = load_yaml(config_path)
    if run_eval is not None:
        cfg["run_eval"] = run_eval
    cpt_report: dict | None = None
    sft_report: dict | None = None
    manifest: dict | None = None

    steps = ["cpt", "sft", "eval", "manifest", "report"]
    if only:
        steps = [only]
        if only == "report":
            steps = ["report"]

    if not skip_train and "cpt" in steps:
        cpt_report = run_cpt(cfg["cpt_config"], force_resume=resume)
    if not skip_train and "sft" in steps:
        sft_report = run_sft(cfg["sft_config"], force_resume=resume)

    pilot_eval_path = resolve_path(cfg.get("eval_out_path") or "friday-llm/reports/phase2_eval_pilot.json")
    if "eval" in steps and cfg.get("run_eval"):
        run_baseline(
            str(cfg.get("eval_path") or "friday-llm/data/evaluation/friday_eval.jsonl"),
            str(pilot_eval_path),
        )

    if "manifest" in steps:
        adapter = str(
            cfg.get("manifest_adapter") or "friday-llm/checkpoints/sft-fase2-pilot/adapter"
        )
        manifest = build_manifest(adapter)

    comparison = compare_reports(
        cfg.get("baseline_path") or "friday-llm/reports/baseline_phi4.json",
        pilot_eval_path,
    )

    if "report" in steps or only is None:
        # load existing CPT/SFT reports if we skipped training
        if cpt_report is None:
            cpt_path = resolve_path("friday-llm/reports/cpt_fase2_pilot.json")
            if cpt_path.is_file():
                cpt_report = json.loads(cpt_path.read_text(encoding="utf-8"))
        if sft_report is None:
            sft_path = resolve_path("friday-llm/reports/sft_fase2_pilot.json")
            if sft_path.is_file():
                sft_report = json.loads(sft_path.read_text(encoding="utf-8"))
        stats = _write_pilot_report(
            cfg,
            cpt_report=cpt_report,
            sft_report=sft_report,
            comparison=comparison,
            manifest=manifest,
        )
        return stats

    return {
        "cpt": cpt_report,
        "sft": sft_report,
        "manifest": manifest,
        "comparison": comparison,
    }


def main(argv: list[str] | None = None) -> None:
    logging.basicConfig(level=logging.INFO)
    p = argparse.ArgumentParser(description="FRIDAY LLM Fase 2 pilot")
    p.add_argument("--config", default="friday-llm/configs/fase2_pilot.yaml")
    p.add_argument(
        "--only",
        choices=["cpt", "sft", "eval", "manifest", "report"],
        default=None,
    )
    p.add_argument("--resume", action="store_true", help="Resume from latest checkpoint")
    p.add_argument(
        "--skip-train",
        action="store_true",
        help="Skip CPT/SFT (report/manifest/eval only)",
    )
    p.add_argument(
        "--run-eval",
        action="store_true",
        help="Run LM Studio eval (requires loaded model)",
    )
    args = p.parse_args(argv)
    result = run_pilot(
        args.config,
        only=args.only,
        resume=args.resume,
        skip_train=args.skip_train,
        run_eval=args.run_eval if args.run_eval else None,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
