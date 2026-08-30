"""Fase 3 CPT orchestrator: approve → train → select → report."""

from __future__ import annotations

import argparse
import json
import logging
from datetime import datetime, timezone
from typing import Any

from friday_llm.training.continued_pretraining.run import run_cpt
from friday_llm.training.continued_pretraining.select_checkpoint import copy_best_adapter
from friday_llm.training.corpus.approval import approve_corpus
from friday_llm.util import load_yaml, resolve_path

logger = logging.getLogger(__name__)


def _write_phase3_report(
    cfg: dict[str, Any],
    *,
    cpt_report: dict | None,
    selection: dict | None,
    approval: dict | None,
) -> dict[str, Any]:
    stats: dict[str, Any] = {
        "run_id": cfg.get("run_id"),
        "finished_at": datetime.now(timezone.utc).isoformat(),
        "approval": approval,
        "cpt": cpt_report,
        "selection": selection,
        "production_model_unchanged": True,
        "lm_studio_default": "microsoft/phi-4",
        "notes": str(cfg.get("notes") or ""),
    }
    json_path = resolve_path(cfg.get("report_json") or "friday-llm/reports/phase3_cpt_stats.json")
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(stats, ensure_ascii=False, indent=2), encoding="utf-8")

    md_path = resolve_path(cfg.get("report_md") or "friday-llm/reports/phase3_cpt_report.md")
    ckpts = (cpt_report or {}).get("checkpoints") or []
    sel_step = (selection or {}).get("step", "—")
    sel_loss = (selection or {}).get("eval_loss", "—")
    lines = [
        "# Fase 3 — Relatório CPT (FRIDAY LLM)",
        "",
        f"**Run:** `{cfg.get('run_id')}`  ",
        f"**Gerado:** {stats['finished_at']}",
        "",
        "## Corpus aprovado",
        "",
        f"- Ficheiro: `{approval.get('file_path') if approval else '—'}`",
        f"- Documentos: **{approval.get('document_count') if approval else '—'}**",
        f"- Tokens estimados: **{approval.get('token_count_est') if approval else '—'}**",
        f"- Hash: `{approval.get('content_hash', '')[:16] if approval else ''}…`",
        "",
        "## Treino CPT",
        "",
    ]
    if cpt_report:
        lines += [
            f"- Modelo: `{cpt_report.get('base_model')}` ({cpt_report.get('quant_mode')})",
            f"- Output: `{cpt_report.get('output_dir')}`",
            f"- Train loss: {cpt_report.get('train_loss', '—')}",
            f"- Eval loss final: {cpt_report.get('eval_loss', '—')}",
            f"- Resume: {cpt_report.get('resumed_from')}",
            f"- Skipped (já completo): {cpt_report.get('skipped_train', False)}",
            "",
            "### Checkpoints",
            "",
            "| Step | eval_loss | train_loss | selected |",
            "|------|-----------|------------|----------|",
        ]
        for c in ckpts:
            mark = "yes" if c.get("step") == sel_step else ""
            lines.append(
                f"| {c.get('step', '—')} | {c.get('eval_loss', '—')} | "
                f"{c.get('train_loss', '—')} | {mark} |"
            )
    lines += [
        "",
        "## Checkpoint seleccionado",
        "",
        f"- Step: **{sel_step}** | eval_loss: **{sel_loss}**",
        f"- Adapter: `{cfg.get('best_adapter_dir')}`",
        "",
        "## Avisos",
        "",
        "- Subset ~2M tokens **não** equivale a conhecimento geral.",
        "- Phi-4 em produção permanece inalterado.",
        "",
    ]
    md_path.write_text("\n".join(lines), encoding="utf-8")
    logger.info("Phase 3 report → %s", md_path)
    return stats


def run_fase3(
    config_path: str,
    *,
    only: str | None = None,
    resume: bool = False,
) -> dict[str, Any]:
    cfg = load_yaml(config_path)
    cpt_cfg = load_yaml(cfg["cpt_config"])
    data_file = str(cpt_cfg.get("data_file") or "friday-llm/data/pretraining/cpt_fase1.jsonl")
    approval_path = str(cfg.get("approval_path") or "friday-llm/reports/corpus_approval.json")

    steps = ["approve", "train", "select", "report"]
    if only:
        steps = [only]

    approval: dict | None = None
    cpt_report: dict | None = None
    selection: dict | None = None

    if "approve" in steps:
        approval = approve_corpus(
            data_file,
            out_path=approval_path,
        )

    if "train" in steps:
        cpt_report = run_cpt(cfg["cpt_config"], force_resume=resume)

    if "select" in steps:
        selection = copy_best_adapter(
            cpt_cfg.get("output_dir") or "friday-llm/checkpoints/cpt-fase3",
            cfg.get("best_adapter_dir") or "friday-llm/checkpoints/cpt-fase3-best/adapter",
            metrics_path=cpt_cfg.get("checkpoint_metrics_path"),
            selection_path=cfg.get("selection_path"),
        )

    if "report" in steps or only is None:
        if approval is None:
            ap = resolve_path(approval_path)
            if ap.is_file():
                approval = json.loads(ap.read_text(encoding="utf-8"))
        if cpt_report is None:
            rp = resolve_path(cpt_cfg.get("report_path") or "friday-llm/reports/cpt_fase3.json")
            if rp.is_file():
                cpt_report = json.loads(rp.read_text(encoding="utf-8"))
        if selection is None:
            sp = resolve_path(cfg.get("selection_path") or "friday-llm/checkpoints/cpt-fase3-best/selection.json")
            if sp.is_file():
                selection = json.loads(sp.read_text(encoding="utf-8"))
        return _write_phase3_report(cfg, cpt_report=cpt_report, selection=selection, approval=approval)

    return {"approval": approval, "cpt": cpt_report, "selection": selection}


def main(argv: list[str] | None = None) -> None:
    logging.basicConfig(level=logging.INFO)
    p = argparse.ArgumentParser(description="FRIDAY LLM Fase 3 CPT")
    p.add_argument("--config", default="friday-llm/configs/fase3_cpt.yaml")
    p.add_argument(
        "--only",
        choices=["approve", "train", "select", "report"],
        default=None,
    )
    p.add_argument("--resume", action="store_true", help="Resume CPT from latest checkpoint")
    args = p.parse_args(argv)
    result = run_fase3(args.config, only=args.only, resume=args.resume)
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
