"""Ingest FineWeb2 stream and local fixtures."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from friday_llm.util import content_hash, estimate_tokens, resolve_path, write_jsonl

logger = logging.getLogger(__name__)


def local_fixture_docs(path: Path) -> list[dict[str, Any]]:
    """Load synthetic CPT docs for offline / unit tests."""
    if not path.is_file():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def stream_fineweb2(
    *,
    max_samples: int = 400,
    language_hint: str = "por",
    config_name: str | None = None,
    max_tokens: int | None = None,
) -> Iterator[dict[str, Any]]:
    """Stream a small FineWeb2 subset. Fails if datasets/HF unavailable."""
    try:
        from datasets import load_dataset
    except ImportError as exc:
        raise RuntimeError(
            "Package 'datasets' required for FineWeb streaming. pip install -e '.[llm]'"
        ) from exc

    if config_name is None:
        config_name = "por_Latn" if language_hint.startswith("por") else "eng_Latn"

    ds = None
    last_exc: Exception | None = None
    candidates: list[tuple[str, str]] = []
    if config_name:
        candidates.append(("HuggingFaceFW/fineweb-2", config_name))
        candidates.append(("HuggingFaceFW/fineweb", config_name))
    if language_hint.startswith("eng"):
        candidates.extend(
            [
                ("HuggingFaceFW/fineweb-2", "eng_Latn"),
                ("HuggingFaceFW/fineweb", "sample-10BT"),
                ("HuggingFaceFW/fineweb", "default"),
            ]
        )
    else:
        candidates.extend(
            [
                ("HuggingFaceFW/fineweb-2", "por_Latn"),
                ("HuggingFaceFW/fineweb", "sample-10BT"),
            ]
        )
    seen: set[tuple[str, str]] = set()
    tried: list[str] = []
    for name, cfg in candidates:
        key = (name, cfg)
        if key in seen:
            continue
        seen.add(key)
        label = f"{name}:{cfg}"
        tried.append(label)
        try:
            ds = load_dataset(name, cfg, split="train", streaming=True)
            break
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
            logger.warning("Could not open %s: %s", label, exc)
            ds = None
    if ds is None:
        raise RuntimeError(f"Could not stream FineWeb from {tried}") from last_exc

    n = 0
    token_total = 0
    for row in ds:
        text = (row.get("text") or "").strip()
        if len(text) < 200:
            continue
        lang = str(row.get("language") or row.get("lang") or language_hint)
        doc = {
            "document_id": content_hash(text)[:16],
            "text": text,
            "source": "fineweb2",
            "url": row.get("url") or row.get("source") or "",
            "crawl": str(row.get("dump") or row.get("crawl") or "fineweb-stream"),
            "captured_at": str(row.get("date") or row.get("timestamp") or ""),
            "language": lang,
            "license": "ODC-By_verify_card",
            "metadata": {
                "streamed_at": datetime.now(timezone.utc).isoformat(),
                "fineweb_config": config_name,
            },
        }
        yield doc
        n += 1
        token_total += estimate_tokens(text)
        if n >= max_samples:
            break
        if max_tokens is not None and token_total >= max_tokens:
            break


def stream_fineweb2_multilang(
    configs: list[dict[str, Any]],
    *,
    max_documents: int = 500,
    max_tokens: int = 2_000_000,
) -> list[dict[str, Any]]:
    """Stream multiple FineWeb2 language configs up to global budgets."""
    docs: list[dict[str, Any]] = []
    token_total = 0
    for entry in configs:
        if len(docs) >= max_documents or token_total >= max_tokens:
            break
        name = str(entry.get("name") or "por_Latn")
        lang = str(entry.get("language") or "por")
        per_lang = int(entry.get("max_samples") or 200)
        remaining_docs = max_documents - len(docs)
        remaining_tokens = max_tokens - token_total
        if remaining_docs <= 0 or remaining_tokens <= 0:
            break
        for doc in stream_fineweb2(
            max_samples=min(per_lang, remaining_docs),
            language_hint=lang,
            config_name=name,
            max_tokens=remaining_tokens,
        ):
            docs.append(doc)
            token_total += estimate_tokens(doc.get("text") or "")
            if len(docs) >= max_documents or token_total >= max_tokens:
                break
    return docs


def write_raw_batch(docs: list[dict[str, Any]], out_path: Path) -> Path:
    out_path = resolve_path(out_path)
    write_jsonl(out_path, docs)
    return out_path
