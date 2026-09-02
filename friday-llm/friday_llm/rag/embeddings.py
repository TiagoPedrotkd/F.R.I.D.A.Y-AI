"""Lightweight sentence embeddings without sentence-transformers (Windows-safe)."""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_DEFAULT_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

# Short ids commonly put in .env without the HF org prefix
_ALIASES = {
    "paraphrase-multilingual-minilm-l12-v2": _DEFAULT_MODEL,
    "all-minilm-l6-v2": "sentence-transformers/all-MiniLM-L6-v2",
    "all-mpnet-base-v2": "sentence-transformers/all-mpnet-base-v2",
}


def normalize_embedding_model(model_name: str | None) -> str:
    """Resolve short / local / HF embedding model ids."""
    raw = (model_name or "").strip() or _DEFAULT_MODEL
    key = raw.casefold()
    if key in _ALIASES:
        return _ALIASES[key]
    path = Path(raw)
    if path.exists():
        return str(path)
    if "/" not in raw:
        return f"sentence-transformers/{raw}"
    return raw


def load_embedding_model(model_name: str) -> tuple[Any, Any]:
    """Load tokenizer + encoder for mean-pooled embeddings."""
    # Avoid TF / Flax paths that pull broken numpy↔dtype combos on some Windows envs
    os.environ.setdefault("TRANSFORMERS_NO_TF", "1")
    os.environ.setdefault("TRANSFORMERS_NO_FLAX", "1")
    os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

    import torch
    from transformers import AutoModel, AutoTokenizer

    resolved = normalize_embedding_model(model_name)
    if resolved != (model_name or "").strip():
        logger.info("Embedding model resolved: %s → %s", model_name, resolved)

    tokenizer = AutoTokenizer.from_pretrained(resolved)
    model = AutoModel.from_pretrained(resolved)
    model.eval()
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model.to(device)
    return tokenizer, model


def encode_texts(
    tokenizer: Any,
    model: Any,
    texts: list[str],
    *,
    batch_size: int = 32,
) -> list[list[float]]:
    """Mean-pool token embeddings and L2-normalize (torch tensors only)."""
    import torch
    import torch.nn.functional as F

    device = next(model.parameters()).device
    out: list[list[float]] = []
    for start in range(0, len(texts), batch_size):
        batch = texts[start : start + batch_size]
        encoded = tokenizer(
            batch,
            padding=True,
            truncation=True,
            max_length=512,
            return_tensors="pt",
        )
        encoded = {k: v.to(device) for k, v in encoded.items()}
        with torch.no_grad():
            hidden = model(**encoded).last_hidden_state
            mask = encoded["attention_mask"].unsqueeze(-1).expand(hidden.size()).float()
            summed = (hidden * mask).sum(dim=1)
            counts = mask.sum(dim=1).clamp(min=1e-9)
            pooled = summed / counts
            normed = F.normalize(pooled, p=2, dim=1)
        # Explicit float list avoids numpy StringDType / ABI edge cases with Chroma
        out.extend([[float(x) for x in row] for row in normed.detach().cpu().tolist()])
    return out
