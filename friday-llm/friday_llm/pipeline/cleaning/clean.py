"""Text cleaning for CPT corpus."""

from __future__ import annotations

import re
import unicodedata
from collections import Counter
from dataclasses import dataclass, field
from typing import Any

from friday_llm.pipeline.quality.gates import basic_quality_ok
from friday_llm.util import content_hash, looks_like_pii


@dataclass
class CleanStats:
    input_docs: int = 0
    kept: int = 0
    reasons: Counter[str] = field(default_factory=Counter)

    def to_dict(self) -> dict[str, Any]:
        return {
            "input_docs": self.input_docs,
            "kept": self.kept,
            "dropped": self.input_docs - self.kept,
            "reasons": dict(self.reasons),
        }


def normalize_unicode(text: str) -> str:
    text = unicodedata.normalize("NFKC", text)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def strip_boilerplate(text: str) -> str:
    lines = []
    for line in text.split("\n"):
        low = line.strip().casefold()
        if low in {"cookie policy", "accept cookies", "subscribe", "sign in", "log in"}:
            continue
        if len(line.strip()) <= 2:
            continue
        lines.append(line)
    return "\n".join(lines).strip()


def detect_language_hint(text: str) -> str:
    """Very light heuristic — not a replacement for langid in production."""
    sample = text[:2000].casefold()
    pt_markers = ("ção", "ões", "não", "também", "porque", "está", "português")
    en_markers = (" the ", " and ", " with ", " that ", " this ")
    pt = sum(1 for m in pt_markers if m in sample)
    en = sum(1 for m in en_markers if m in sample)
    if pt > en and pt > 0:
        return "por"
    if en > pt and en > 0:
        return "eng"
    return "und"


def classify_pt_variant(text: str) -> str:
    sample = text.casefold()
    br = sum(
        1
        for m in ("você", "voce ", "celular", "ônibus", "onibus", "legal,", "aí sim")
        if m in sample
    )
    pt = sum(
        1
        for m in ("telemóvel", "autocarro", "pequeno-almoço", "fixe", "pá ")
        if m in sample
    )
    if pt > br:
        return "pt-PT"
    if br > pt:
        return "pt-BR"
    return "pt-und"


def clean_document(
    doc: dict[str, Any],
    *,
    min_chars: int = 200,
    max_chars: int = 50_000,
    drop_pii: bool = True,
    check_quality: bool = True,
    contamination_checker: Any | None = None,
    stats: CleanStats | None = None,
) -> dict[str, Any] | None:
    stats = stats or CleanStats()
    stats.input_docs += 1
    text = doc.get("text") or ""
    if not isinstance(text, str):
        stats.reasons["not_text"] += 1
        return None
    text = normalize_unicode(text)
    text = strip_boilerplate(text)
    if len(text) < min_chars:
        stats.reasons["too_short"] += 1
        return None
    if len(text) > max_chars:
        text = text[:max_chars]
        stats.reasons["truncated"] += 1
    if drop_pii and looks_like_pii(text):
        stats.reasons["pii"] += 1
        return None
    if check_quality and not basic_quality_ok({"text": text}):
        stats.reasons["low_quality"] += 1
        return None
    if contamination_checker is not None and contamination_checker(text):
        stats.reasons["eval_leak"] += 1
        return None
    lang = doc.get("language") or detect_language_hint(text)
    variant = doc.get("variant") or (
        classify_pt_variant(text) if lang.startswith("por") or lang == "pt" else ""
    )
    out = {
        "document_id": doc.get("document_id") or content_hash(text)[:16],
        "text": text,
        "source": doc.get("source", "unknown"),
        "url": doc.get("url", ""),
        "crawl": doc.get("crawl", ""),
        "captured_at": doc.get("captured_at", ""),
        "language": lang,
        "variant": variant,
        "license": doc.get("license", "unknown_or_declared"),
        "content_hash": content_hash(text),
        "metadata": doc.get("metadata") or {},
    }
    stats.kept += 1
    return out
