"""Merge CPT + SFT LoRA adapters into a single HF model for GGUF export."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from friday_llm.training.common import adapter_dir_from_path
from friday_llm.util import resolve_path

logger = logging.getLogger(__name__)


def _adapter_ready(path: str | Path | None) -> Path | None:
    if not path:
        return None
    root = adapter_dir_from_path(path)
    if root.is_dir() and (root / "adapter_config.json").is_file():
        return root
    return None


def validate_adapters(
    sft_adapter: str | Path,
    *,
    cpt_adapter: str | Path | None = None,
    merge_cpt: bool = True,
) -> dict[str, Any]:
    """Validate adapter paths before merge."""
    sft = _adapter_ready(sft_adapter)
    if sft is None:
        raise FileNotFoundError(f"SFT adapter missing or invalid: {sft_adapter}")

    cpt = _adapter_ready(cpt_adapter) if merge_cpt else None
    warnings: list[str] = []
    if merge_cpt and cpt_adapter and cpt is None:
        warnings.append(f"CPT adapter not found at {cpt_adapter}; will merge SFT only.")

    return {
        "valid": True,
        "sft_adapter": str(sft),
        "cpt_adapter": str(cpt) if cpt else None,
        "merge_cpt": merge_cpt and cpt is not None,
        "warnings": warnings,
    }


def merge_to_hf(
    base_model_id: str,
    sft_adapter: str | Path,
    out_dir: str | Path,
    *,
    cpt_adapter: str | Path | None = None,
    merge_cpt: bool = True,
    device_map: str = "cpu",
) -> dict[str, Any]:
    """Merge CPT (optional) + SFT adapters into base model and save HF weights."""
    validation = validate_adapters(
        sft_adapter, cpt_adapter=cpt_adapter, merge_cpt=merge_cpt
    )
    sft_path = Path(validation["sft_adapter"])
    cpt_path = Path(validation["cpt_adapter"]) if validation["cpt_adapter"] else None

    from peft import PeftModel
    from transformers import AutoModelForCausalLM, AutoTokenizer

    logger.info("Loading base model %s on %s", base_model_id, device_map)
    tokenizer = AutoTokenizer.from_pretrained(base_model_id, trust_remote_code=True)
    model = AutoModelForCausalLM.from_pretrained(
        base_model_id,
        torch_dtype="auto",
        device_map=device_map,
        trust_remote_code=True,
    )

    merged_cpt = False
    if cpt_path is not None:
        logger.info("Merging CPT adapter from %s", cpt_path)
        model = PeftModel.from_pretrained(model, str(cpt_path), is_trainable=False)
        model = model.merge_and_unload()
        merged_cpt = True

    logger.info("Merging SFT adapter from %s", sft_path)
    model = PeftModel.from_pretrained(model, str(sft_path), is_trainable=False)
    model = model.merge_and_unload()

    dest = resolve_path(out_dir)
    dest.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(str(dest))
    tokenizer.save_pretrained(str(dest))

    report = {
        "merged_at": datetime.now(timezone.utc).isoformat(),
        "base_model": base_model_id,
        "merged_hf_dir": str(dest),
        "cpt_adapter": str(cpt_path) if cpt_path else None,
        "sft_adapter": str(sft_path),
        "merged_cpt": merged_cpt,
        "device_map": device_map,
        "warnings": validation["warnings"],
    }
    logger.info("Merged model saved → %s", dest)
    return report
