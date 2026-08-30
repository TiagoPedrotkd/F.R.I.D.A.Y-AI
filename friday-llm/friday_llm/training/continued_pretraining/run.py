"""Continued pretraining (CPT) with resume and Fase 3 metrics."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from friday_llm.training.common import (
    append_checkpoint_metric,
    build_training_args,
    list_checkpoints,
    load_base_model,
    load_run_config,
    load_tokenizer,
    lora_config_from_base,
    resolve_resume_checkpoint,
    select_model_id,
    training_complete,
)
from friday_llm.training.corpus.approval import validate_approval
from friday_llm.util import read_jsonl, resolve_path

logger = logging.getLogger(__name__)


def _load_cpt_rows(cfg: dict) -> list[dict]:
    if cfg.get("data_file"):
        path = resolve_path(cfg["data_file"])
        rows = read_jsonl(path)
        if rows:
            return rows
    rows: list[dict] = []
    glob_hint = str(cfg.get("data_glob") or "friday-llm/data/pretraining/*.jsonl")
    if "*" in glob_hint:
        parent = resolve_path(glob_hint.rsplit("*", 1)[0])
        for path in sorted(parent.glob("*.jsonl")):
            rows.extend(read_jsonl(path))
    if not rows:
        raise FileNotFoundError(
            "No CPT data — set data_file or run Fase 1 build_datasets first"
        )
    return rows


def _sync_checkpoint_metrics(cfg: dict, out_dir: Path) -> None:
    metrics_path = resolve_path(
        cfg.get("checkpoint_metrics_path") or "friday-llm/reports/checkpoint_metrics.jsonl"
    )
    for row in list_checkpoints(out_dir):
        if row.get("eval_loss") is None:
            continue
        append_checkpoint_metric(
            metrics_path,
            step=int(row.get("step") or 0),
            eval_loss=row.get("eval_loss"),
            train_loss=row.get("train_loss"),
            checkpoint_path=str(row.get("checkpoint_path") or ""),
        )


def _default_notes(cfg: dict) -> str:
    if cfg.get("phase") == "fase3":
        return "Fase 3 CPT — approved corpus; checkpoint selection enabled."
    return "CPT run — subset only; not general knowledge training."


def run_cpt(config_path: str, *, force_resume: bool = False, skip_if_complete: bool = True) -> dict:
    cfg, base_cfg = load_run_config(config_path)
    data_file = str(cfg.get("data_file") or "")

    if cfg.get("require_approval"):
        approval_path = str(cfg.get("approval_path") or "friday-llm/reports/corpus_approval.json")
        validate_approval(data_file, approval_path=approval_path)

    use_smoke = bool(cfg.get("use_smoke_model", True))
    model_id = select_model_id(base_cfg, use_smoke)
    rows = _load_cpt_rows(cfg)

    out_dir = resolve_path(cfg["output_dir"])
    out_dir.mkdir(parents=True, exist_ok=True)
    max_steps = int(cfg.get("max_steps") or 20)

    if skip_if_complete and training_complete(out_dir, max_steps) and not force_resume:
        logger.info("CPT already complete at %s", out_dir)
        _sync_checkpoint_metrics(cfg, out_dir)
        return _build_report_from_disk(cfg, base_cfg, model_id, skipped=True)

    from datasets import Dataset
    from peft import get_peft_model
    from transformers import DataCollatorForLanguageModeling, Trainer, TrainerCallback

    tokenizer = load_tokenizer(model_id)
    model, quant_mode = load_base_model(model_id, base_cfg)
    model = get_peft_model(model, lora_config_from_base(base_cfg))

    seq_length = int(cfg.get("seq_length") or 512)

    def tok(batch):
        return tokenizer(
            batch["text"],
            truncation=True,
            max_length=seq_length,
            padding="max_length",
        )

    texts = [r["text"] for r in rows if r.get("text")]
    ds = Dataset.from_list([{"text": t} for t in texts])
    split = ds.train_test_split(test_size=0.1, seed=int(cfg.get("seed") or 42))
    train_ds = split["train"].map(tok, batched=True, remove_columns=["text"])
    eval_ds = split["test"].map(tok, batched=True, remove_columns=["text"])

    args = build_training_args(cfg, out_dir, quant_mode)
    resume_ckpt = resolve_resume_checkpoint(cfg, force_resume=force_resume)
    metrics_path = resolve_path(
        cfg.get("checkpoint_metrics_path") or "friday-llm/reports/checkpoint_metrics.jsonl"
    )

    class MetricsCallback(TrainerCallback):
        def on_save(self, args, state, control, **kwargs):  # noqa: ANN001, ARG002
            ckpt_dir = out_dir / f"checkpoint-{state.global_step}"
            eval_loss = None
            train_loss = None
            for entry in reversed(state.log_history):
                if eval_loss is None and "eval_loss" in entry:
                    eval_loss = entry["eval_loss"]
                if train_loss is None and "loss" in entry:
                    train_loss = entry["loss"]
            if ckpt_dir.is_dir():
                append_checkpoint_metric(
                    metrics_path,
                    step=state.global_step,
                    eval_loss=eval_loss,
                    train_loss=train_loss,
                    checkpoint_path=str(ckpt_dir),
                )

    trainer = Trainer(
        model=model,
        args=args,
        train_dataset=train_ds,
        eval_dataset=eval_ds,
        data_collator=DataCollatorForLanguageModeling(tokenizer=tokenizer, mlm=False),
        callbacks=[MetricsCallback()],
    )
    train_result = trainer.train(resume_from_checkpoint=resume_ckpt)
    metrics = trainer.evaluate()
    adapter_out = out_dir / "adapter"
    trainer.save_model(str(adapter_out))
    tokenizer.save_pretrained(str(adapter_out))

    _sync_checkpoint_metrics(cfg, out_dir)

    report = {
        "run_id": cfg.get("run_id"),
        "phase": cfg.get("phase") or "cpt",
        "finished_at": datetime.now(timezone.utc).isoformat(),
        "base_model": model_id,
        "output_dir": str(out_dir),
        "data_file": data_file,
        "n_source_docs": len(texts),
        "train_loss": float(train_result.training_loss),
        "eval_loss": float(metrics.get("eval_loss", -1)),
        "n_train_docs": len(train_ds),
        "n_eval_docs": len(eval_ds),
        "max_steps": args.max_steps,
        "quant_mode": quant_mode,
        "resumed_from": resume_ckpt,
        "checkpoints": list_checkpoints(out_dir),
        "skipped_train": False,
        "notes": _default_notes(cfg),
    }
    report_path = resolve_path(
        cfg.get("report_path") or "friday-llm/reports/cpt_fase2_pilot.json"
    )
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    logger.info("CPT report → %s", report_path)
    return report


def _build_report_from_disk(
    cfg: dict,
    base_cfg: dict,
    model_id: str,
    *,
    skipped: bool,
) -> dict:
    out_dir = resolve_path(cfg["output_dir"])
    report_path = resolve_path(cfg.get("report_path") or "friday-llm/reports/cpt_fase3.json")
    ckpts = list_checkpoints(out_dir)
    eval_loss = min((c["eval_loss"] for c in ckpts if c.get("eval_loss") is not None), default=-1)
    report = {
        "run_id": cfg.get("run_id"),
        "phase": cfg.get("phase") or "cpt",
        "finished_at": datetime.now(timezone.utc).isoformat(),
        "base_model": model_id,
        "output_dir": str(out_dir),
        "data_file": str(cfg.get("data_file") or ""),
        "eval_loss": eval_loss,
        "max_steps": int(cfg.get("max_steps") or 0),
        "checkpoints": ckpts,
        "skipped_train": skipped,
        "notes": _default_notes(cfg),
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report
