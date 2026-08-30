"""Shared training helpers for CPT and SFT."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from friday_llm.util import load_yaml, resolve_path

logger = logging.getLogger(__name__)


def select_model_id(base_cfg: dict[str, Any], use_smoke: bool) -> str:
    if use_smoke:
        return str(base_cfg.get("smoke_model_id") or base_cfg["model_id"])
    return str(base_cfg["model_id"])


def lora_config_from_base(base_cfg: dict[str, Any]):
    from peft import LoraConfig

    return LoraConfig(
        r=int(base_cfg.get("lora_r") or 16),
        lora_alpha=int(base_cfg.get("lora_alpha") or 32),
        lora_dropout=float(base_cfg.get("lora_dropout") or 0.05),
        bias="none",
        task_type="CAUSAL_LM",
        target_modules=list(base_cfg.get("target_modules") or ["q_proj", "v_proj"]),
    )


def find_latest_checkpoint(output_dir: Path) -> str | None:
    """Return path to latest checkpoint-* dir, or None."""
    if not output_dir.is_dir():
        return None
    checkpoints = sorted(
        (p for p in output_dir.iterdir() if p.is_dir() and p.name.startswith("checkpoint-")),
        key=lambda p: int(p.name.split("-")[-1]) if p.name.split("-")[-1].isdigit() else 0,
    )
    if not checkpoints:
        return None
    latest = checkpoints[-1]
    if (latest / "trainer_state.json").is_file() or (latest / "adapter_config.json").is_file():
        return str(latest)
    return None


def read_trainer_state(checkpoint_dir: Path) -> dict[str, Any]:
    state_path = checkpoint_dir / "trainer_state.json"
    if not state_path.is_file():
        return {}
    return json.loads(state_path.read_text(encoding="utf-8"))


def list_checkpoints(output_dir: Path) -> list[dict[str, Any]]:
    """List checkpoint-* dirs with step and eval_loss from trainer_state."""
    if not output_dir.is_dir():
        return []
    rows: list[dict[str, Any]] = []
    for path in sorted(output_dir.iterdir()):
        if not path.is_dir() or not path.name.startswith("checkpoint-"):
            continue
        step_str = path.name.split("-")[-1]
        step = int(step_str) if step_str.isdigit() else 0
        state = read_trainer_state(path)
        eval_loss = None
        train_loss = None
        for entry in reversed(state.get("log_history") or []):
            if eval_loss is None and "eval_loss" in entry:
                eval_loss = entry["eval_loss"]
            if train_loss is None and "loss" in entry:
                train_loss = entry["loss"]
            if eval_loss is not None and train_loss is not None:
                break
        rows.append(
            {
                "checkpoint_path": str(path),
                "step": state.get("global_step") or step,
                "eval_loss": eval_loss,
                "train_loss": train_loss,
            }
        )
    return rows


def append_checkpoint_metric(
    metrics_path: Path,
    *,
    step: int,
    eval_loss: float | None,
    train_loss: float | None,
    checkpoint_path: str,
) -> None:
    metrics_path.parent.mkdir(parents=True, exist_ok=True)
    row = {
        "step": step,
        "eval_loss": eval_loss,
        "train_loss": train_loss,
        "checkpoint_path": checkpoint_path,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    with metrics_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def training_complete(output_dir: Path, max_steps: int) -> bool:
    """True if latest checkpoint reached max_steps."""
    ckpt = find_latest_checkpoint(output_dir)
    if not ckpt:
        return False
    state = read_trainer_state(Path(ckpt))
    return int(state.get("global_step") or 0) >= max_steps


def resolve_resume_checkpoint(cfg: dict[str, Any], *, force_resume: bool = False) -> str | None:
    if not (force_resume or cfg.get("resume_from_checkpoint")):
        return None
    out_dir = resolve_path(cfg["output_dir"])
    max_steps = int(cfg.get("max_steps") or 0)
    if max_steps and training_complete(out_dir, max_steps):
        logger.warning("Training already reached max_steps=%s; skipping resume train", max_steps)
        return None
    ckpt = find_latest_checkpoint(out_dir)
    if ckpt:
        logger.info("Resuming from checkpoint %s", ckpt)
    return ckpt


def load_base_model(model_id: str, base_cfg: dict[str, Any]):
    """Load causal LM with 4-bit QLoRA prep or fp16 fallback."""
    try:
        import torch
        from peft import prepare_model_for_kbit_training
        from transformers import AutoModelForCausalLM, BitsAndBytesConfig
    except ImportError as exc:
        raise RuntimeError("Install llm extras: pip install -e '.[llm]'") from exc

    quant_mode = "nf4"
    try:
        bnb = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.float16,
            bnb_4bit_use_double_quant=True,
        )
        model = AutoModelForCausalLM.from_pretrained(
            model_id,
            quantization_config=bnb,
            device_map="auto",
            trust_remote_code=True,
        )
        model = prepare_model_for_kbit_training(model)
    except Exception as exc:  # noqa: BLE001
        logger.warning("4-bit load failed (%s); falling back to fp16 LoRA", exc)
        quant_mode = "fp16"
        model = AutoModelForCausalLM.from_pretrained(
            model_id,
            torch_dtype=torch.float16,
            device_map="auto",
            trust_remote_code=True,
        )
    return model, quant_mode


def load_tokenizer(model_id: str):
    from transformers import AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained(model_id, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    return tokenizer


def build_training_args(cfg: dict[str, Any], out_dir: Path, quant_mode: str):
    from transformers import TrainingArguments

    max_steps = int(cfg.get("max_steps") or 20)
    save_steps = int(cfg.get("save_steps") or max_steps)
    eval_steps = int(cfg.get("eval_steps") or save_steps)
    warmup = cfg.get("warmup_steps")
    if warmup is None:
        warmup = max(1, int(0.03 * max_steps))

    kwargs: dict[str, Any] = {
        "output_dir": str(out_dir),
        "max_steps": max_steps,
        "per_device_train_batch_size": int(cfg.get("per_device_train_batch_size") or 1),
        "gradient_accumulation_steps": int(cfg.get("gradient_accumulation_steps") or 4),
        "learning_rate": float(cfg.get("learning_rate") or 2e-5),
        "warmup_steps": int(warmup),
        "logging_steps": int(cfg.get("logging_steps") or 1),
        "save_steps": save_steps,
        "eval_strategy": "steps",
        "eval_steps": eval_steps,
        "fp16": True if quant_mode == "fp16" else bool(cfg.get("fp16")),
        "bf16": bool(cfg.get("bf16")),
        "gradient_checkpointing": bool(cfg.get("gradient_checkpointing", True)),
        "report_to": [],
        "seed": int(cfg.get("seed") or 42),
        "remove_unused_columns": False,
    }
    if cfg.get("save_total_limit") is not None:
        kwargs["save_total_limit"] = int(cfg["save_total_limit"])
    if cfg.get("load_best_model_at_end"):
        kwargs["load_best_model_at_end"] = True
        kwargs["metric_for_best_model"] = str(cfg.get("metric_for_best_model") or "eval_loss")
        kwargs["greater_is_better"] = bool(cfg.get("greater_is_better", False))
    return TrainingArguments(**kwargs)


def load_run_config(config_path: str) -> tuple[dict[str, Any], dict[str, Any]]:
    cfg = load_yaml(config_path)
    base_cfg = load_yaml(cfg["model_config"])
    return cfg, base_cfg


def adapter_dir_from_path(adapter_path: str | Path) -> Path:
    adapter = resolve_path(adapter_path)
    if adapter.name == "adapter":
        return adapter
    return adapter / "adapter"
