"""Supervised fine-tuning with CPT adapter chain and resume."""

from __future__ import annotations

import json
import logging
from collections import Counter
from datetime import datetime, timezone

from friday_llm.training.common import (
    adapter_dir_from_path,
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
from friday_llm.training.sft.approval import validate_sft_approval
from friday_llm.util import read_jsonl, resolve_path

logger = logging.getLogger(__name__)


def messages_to_text(tokenizer, messages: list[dict]) -> str:
    if hasattr(tokenizer, "apply_chat_template"):
        try:
            safe = []
            for m in messages:
                role = m.get("role", "user")
                content = m.get("content") or ""
                if m.get("tool_calls"):
                    content = content or json.dumps(m["tool_calls"], ensure_ascii=False)
                if role == "tool":
                    safe.append(
                        {
                            "role": "tool",
                            "content": str(content),
                            "tool_call_id": m.get("tool_call_id") or "call_1",
                        }
                    )
                    continue
                safe.append(
                    {
                        "role": role
                        if role in ("system", "user", "assistant", "tool")
                        else "user",
                        "content": content,
                    }
                )
            return tokenizer.apply_chat_template(
                safe, tokenize=False, add_generation_prompt=False
            )
        except Exception:  # noqa: BLE001
            pass
    parts = []
    for m in messages:
        parts.append(f"{m.get('role')}: {m.get('content') or m.get('tool_calls')}")
    return "\n".join(parts)


def _default_notes(cfg: dict) -> str:
    if cfg.get("phase") == "fase4":
        return "Fase 4 SFT — personality, tools, safety; production model unchanged."
    return "SFT run — production model unchanged."


def run_sft(
    config_path: str,
    *,
    force_resume: bool = False,
    skip_if_complete: bool = True,
) -> dict:
    cfg, base_cfg = load_run_config(config_path)
    train_file = str(cfg.get("train_file") or "friday-llm/data/sft/seed_sft.jsonl")
    eval_file = str(cfg.get("eval_file") or "friday-llm/data/sft/seed_sft_holdout.jsonl")

    if cfg.get("require_approval"):
        validate_sft_approval(
            train_file,
            eval_file,
            approval_path=str(
                cfg.get("approval_path") or "friday-llm/reports/sft_approval.json"
            ),
        )

    use_smoke = bool(cfg.get("use_smoke_model", True))
    model_id = select_model_id(base_cfg, use_smoke)

    train_rows = read_jsonl(resolve_path(train_file))
    if not train_rows:
        train_rows = read_jsonl(resolve_path("friday-llm/data/sft/seed_sft.jsonl"))
    eval_rows = read_jsonl(resolve_path(eval_file)) or train_rows[
        : max(1, len(train_rows) // 5)
    ]

    out_dir = resolve_path(cfg["output_dir"])
    out_dir.mkdir(parents=True, exist_ok=True)
    max_steps = int(cfg.get("max_steps") or 20)

    if skip_if_complete and training_complete(out_dir, max_steps) and not force_resume:
        logger.info("SFT already complete at %s", out_dir)
        return _build_report_from_disk(cfg, model_id, skipped=True)

    from datasets import Dataset
    from peft import PeftModel, get_peft_model
    from transformers import DataCollatorForLanguageModeling, Trainer, TrainerCallback

    tokenizer = load_tokenizer(model_id)
    model, quant_mode = load_base_model(model_id, base_cfg)

    adapter_dir = adapter_dir_from_path(cfg.get("adapter_path") or "")
    if adapter_dir.is_dir() and (adapter_dir / "adapter_config.json").is_file():
        logger.info("Loading CPT adapter from %s", adapter_dir)
        model = PeftModel.from_pretrained(model, str(adapter_dir), is_trainable=True)
    else:
        logger.warning("No CPT adapter at %s; training fresh LoRA on base", adapter_dir)
        model = get_peft_model(model, lora_config_from_base(base_cfg))

    seq_length = int(cfg.get("seq_length") or 1024)

    def rows_to_ds(rows):
        texts = [
            messages_to_text(tokenizer, r.get("messages") or [])
            for r in rows
            if r.get("messages")
        ]
        return Dataset.from_list([{"text": t} for t in texts if t.strip()])

    def tok(batch):
        return tokenizer(
            batch["text"],
            truncation=True,
            max_length=seq_length,
            padding="max_length",
        )

    train_ds = rows_to_ds(train_rows).map(tok, batched=True, remove_columns=["text"])
    eval_ds = rows_to_ds(eval_rows).map(tok, batched=True, remove_columns=["text"])

    args = build_training_args(cfg, out_dir, quant_mode)
    resume_ckpt = resolve_resume_checkpoint(cfg, force_resume=force_resume)
    metrics_path = resolve_path(
        cfg.get("checkpoint_metrics_path") or "friday-llm/reports/sft_checkpoint_metrics.jsonl"
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

    categories = Counter(str(r.get("category") or "other") for r in train_rows)

    report = {
        "run_id": cfg.get("run_id"),
        "phase": cfg.get("phase") or "sft",
        "finished_at": datetime.now(timezone.utc).isoformat(),
        "base_model": model_id,
        "output_dir": str(out_dir),
        "adapter_path": str(adapter_dir) if adapter_dir.is_dir() else "",
        "train_file": train_file,
        "train_loss": float(train_result.training_loss),
        "eval_loss": float(metrics.get("eval_loss", -1)),
        "n_train": len(train_ds),
        "n_eval": len(eval_ds),
        "quant_mode": quant_mode,
        "resumed_from": resume_ckpt,
        "checkpoints": list_checkpoints(out_dir),
        "categories_train": dict(categories),
        "skipped_train": False,
        "notes": _default_notes(cfg),
    }
    report_path = resolve_path(
        cfg.get("report_path") or "friday-llm/reports/sft_fase2_pilot.json"
    )
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    logger.info("SFT report → %s", report_path)
    return report


def _build_report_from_disk(cfg: dict, model_id: str, *, skipped: bool) -> dict:
    out_dir = resolve_path(cfg["output_dir"])
    report_path = resolve_path(cfg.get("report_path") or "friday-llm/reports/sft_fase4.json")
    ckpts = list_checkpoints(out_dir)
    eval_loss = min((c["eval_loss"] for c in ckpts if c.get("eval_loss") is not None), default=-1)
    report = {
        "run_id": cfg.get("run_id"),
        "phase": cfg.get("phase") or "sft",
        "finished_at": datetime.now(timezone.utc).isoformat(),
        "base_model": model_id,
        "output_dir": str(out_dir),
        "eval_loss": eval_loss,
        "checkpoints": ckpts,
        "skipped_train": skipped,
        "notes": _default_notes(cfg),
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report
