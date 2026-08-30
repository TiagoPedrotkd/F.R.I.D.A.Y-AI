"""Lightweight sentence embeddings without sentence-transformers (Windows-safe)."""

from __future__ import annotations

from typing import Any


def load_embedding_model(model_name: str) -> tuple[Any, Any]:
    """Load tokenizer + encoder for mean-pooled embeddings."""
    import torch
    from transformers import AutoModel, AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModel.from_pretrained(model_name)
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
    """Mean-pool token embeddings and L2-normalize."""
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
        out.extend(normed.cpu().tolist())
    return out
