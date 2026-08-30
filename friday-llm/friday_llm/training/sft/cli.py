"""Fase 4 SFT orchestrator: build → approve → train → select → eval → report."""

from __future__ import annotations

import argparse
import json
import logging
from datetime import datetime, timezone
from typing import Any

from friday_llm.evaluation.eval_by_category import compare_with_categories
from friday_llm.evaluation.run_baseline import run_baseline
from friday_llm.pipeline.build_datasets.sft_fase4_builder import write_fase4_datasets
from friday_llm.training.continued_pretraining.select_checkpoint import copy_best_adapter
from friday_llm.training.sft.approval import approve_sft_dataset
from friday_llm.training.sft.run import run_sft
from friday_llm.util import load_yaml, resolve_path

logger = logging.getLogger(__name__)


def _write_phase4_report(
    cfg: dict[str, Any],
    *,
    build_meta: dict | None,
    approval: dict | None,
    sft_report: dict | None,
    selection: dict | None,
    eval_comparison: dict | None,
) -> dict[str, Any]:
    stats: dict[str, Any] = {
        "run_id": cfg.get("run_id"),
        "finished_at": datetime.now(timezone.utc).isoformat(),
        "build": build_meta,
        "approval": approval,
        "sft": sft_report,
        "selection": selection,
        "eval_comparison": eval_comparison,
        "production_model_unchanged": True,
        "lm_studio_default": "microsoft/phi-4",
        "notes": str(cfg.get("notes") or ""),
    }
    json_path = resolve_path(cfg.get("report_json") or "friday-llm/reports/phase4_sft_stats.json")
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(stats, ensure_ascii=False, indent=2), encoding="utf-8")

    sft_cfg = load_yaml(cfg["sft_config"])
    md_path = resolve_path(cfg.get("report_md") or "friday-llm/reports/phase4_sft_report.md")
    lines = [
        "# Fase 4 — Relatório SFT (FRIDAY LLM)",
        "",
        f"**Run:** `{cfg.get('run_id')}`  ",
        f"**Gerado:** {stats['finished_at']}",
        "",
        "## Dataset",
        "",
    ]
    if build_meta:
        lines += [
            f"- Train: **{build_meta.get('train')}** | Holdout: **{build_meta.get('holdout')}**",
            f"- Categorias: `{json.dumps(build_meta.get('categories', {}), ensure_ascii=False)}`",
            f"- Eval leak dropped: {build_meta.get('eval_leak_dropped', 0)}",
        ]
    if approval:
        lines += [
            "",
            f"- Aprovado: **{approval.get('approved')}**",
            f"- Hash: `{str(approval.get('content_hash', ''))[:16]}…`",
        ]
    lines += ["", "## Treino SFT", ""]
    if sft_report:
        lines += [
            f"- Modelo: `{sft_report.get('base_model')}` ({sft_report.get('quant_mode')})",
            f"- CPT adapter: `{sft_report.get('adapter_path')}`",
            f"- Train/eval loss: {sft_report.get('train_loss')} / {sft_report.get('eval_loss')}",
            f"- Skipped: {sft_report.get('skipped_train', False)}",
        ]
    if selection:
        lines += [
            "",
            "## Checkpoint seleccionado",
            "",
            f"- Step **{selection.get('step')}** | eval_loss **{selection.get('eval_loss')}**",
            f"- Adapter: `{cfg.get('best_adapter_dir')}`",
        ]
    lines += ["", "## Avaliação vs baseline", ""]
    if eval_comparison:
        b = eval_comparison.get("baseline") or {}
        p = eval_comparison.get("pilot") or {}
        d = eval_comparison.get("delta") or {}
        lines += [
            "| Métrica | Phi-4 baseline | Pós-SFT | Delta |",
            "|---------|----------------|---------|-------|",
            f"| pass_rate | {b.get('pass_rate', '—')} | {p.get('pass_rate', '—')} | {d.get('pass_rate', '—')} |",
            f"| tool_call_rate | {b.get('tool_call_rate', '—')} | {p.get('tool_call_rate', '—')} | {d.get('tool_call_rate', '—')} |",
            "",
            "### Por categoria (baseline)",
            "",
            f"```json\n{json.dumps(eval_comparison.get('baseline_by_category', {}), ensure_ascii=False, indent=2)}\n```",
            "",
            "### Por categoria (pós-SFT)",
            "",
            f"```json\n{json.dumps(eval_comparison.get('candidate_by_category') or {}, ensure_ascii=False, indent=2)}\n```",
        ]
    else:
        lines.append("_Eval LM Studio não corrida. Usar `--run-eval` com modelo carregado._")
    lines += [
        "",
        "## Avisos",
        "",
        "- Dataset curado ≠ comportamento completo de produção.",
        "- Phi-4 em produção permanece inalterado.",
        "",
    ]
    md_path.write_text("\n".join(lines), encoding="utf-8")
    logger.info("Phase 4 report → %s", md_path)
    return stats


def run_fase4(
    config_path: str,
    *,
    only: str | None = None,
    resume: bool = False,
    run_eval: bool | None = None,
) -> dict[str, Any]:
    cfg = load_yaml(config_path)
    if run_eval is not None:
        cfg["run_eval"] = run_eval
    sft_cfg = load_yaml(cfg["sft_config"])
    train_file = str(sft_cfg.get("train_file"))
    holdout_file = str(sft_cfg.get("eval_file"))

    steps = ["build", "approve", "train", "select", "eval", "report"]
    if only:
        steps = [only]

    build_meta: dict | None = None
    approval: dict | None = None
    sft_report: dict | None = None
    selection: dict | None = None

    if "build" in steps:
        build_meta = write_fase4_datasets(seed=int(cfg.get("seed") or 42))

    if "approve" in steps:
        approval = approve_sft_dataset(
            train_file,
            holdout_file,
            out_path=str(cfg.get("approval_path") or "friday-llm/reports/sft_approval.json"),
        )

    if "train" in steps:
        sft_report = run_sft(cfg["sft_config"], force_resume=resume)

    if "select" in steps:
        selection = copy_best_adapter(
            sft_cfg.get("output_dir") or "friday-llm/checkpoints/sft-fase4",
            cfg.get("best_adapter_dir") or "friday-llm/checkpoints/sft-fase4-best/adapter",
            metrics_path=sft_cfg.get("checkpoint_metrics_path"),
            selection_path=cfg.get("selection_path"),
        )

    eval_comparison = None
    if "eval" in steps and cfg.get("run_eval"):
        run_baseline(
            str(cfg.get("eval_path") or "friday-llm/data/evaluation/friday_eval.jsonl"),
            str(cfg.get("eval_out_path") or "friday-llm/reports/phase4_eval_sft.json"),
        )

    eval_out = resolve_path(cfg.get("eval_out_path") or "friday-llm/reports/phase4_eval_sft.json")
    eval_comparison = compare_with_categories(
        cfg.get("baseline_path") or "friday-llm/reports/baseline_phi4.json",
        eval_out,
    )

    if "report" in steps or only is None:
        if build_meta is None:
            bp = resolve_path("friday-llm/reports/fase4_sft_build_stats.json")
            if bp.is_file():
                build_meta = json.loads(bp.read_text(encoding="utf-8"))
        if approval is None:
            ap = resolve_path(cfg.get("approval_path") or "friday-llm/reports/sft_approval.json")
            if ap.is_file():
                approval = json.loads(ap.read_text(encoding="utf-8"))
        if sft_report is None:
            rp = resolve_path(sft_cfg.get("report_path") or "friday-llm/reports/sft_fase4.json")
            if rp.is_file():
                sft_report = json.loads(rp.read_text(encoding="utf-8"))
        if selection is None:
            sp = resolve_path(cfg.get("selection_path") or "friday-llm/checkpoints/sft-fase4-best/selection.json")
            if sp.is_file():
                selection = json.loads(sp.read_text(encoding="utf-8"))
        return _write_phase4_report(
            cfg,
            build_meta=build_meta,
            approval=approval,
            sft_report=sft_report,
            selection=selection,
            eval_comparison=eval_comparison,
        )

    return {
        "build": build_meta,
        "approval": approval,
        "sft": sft_report,
        "selection": selection,
        "eval_comparison": eval_comparison,
    }


def main(argv: list[str] | None = None) -> None:
    logging.basicConfig(level=logging.INFO)
    p = argparse.ArgumentParser(description="FRIDAY LLM Fase 4 SFT")
    p.add_argument("--config", default="friday-llm/configs/fase4_sft.yaml")
    p.add_argument(
        "--only",
        choices=["build", "approve", "train", "select", "eval", "report"],
        default=None,
    )
    p.add_argument("--resume", action="store_true")
    p.add_argument("--run-eval", action="store_true")
    args = p.parse_args(argv)
    result = run_fase4(
        args.config,
        only=args.only,
        resume=args.resume,
        run_eval=args.run_eval if args.run_eval else None,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
