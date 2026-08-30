"""Prepare LLM text for natural TTS playback (spoken channel only)."""

from __future__ import annotations

import re
from urllib.parse import urlparse

_MAX_TTS_CHARS = 1200

_URL_RE = re.compile(r"https?://[^\s<>\"']+", re.I)
_MD_HEADING = re.compile(r"^#{1,6}\s+", re.M)
_LIST_ITEM = re.compile(r"^\s*[-*•]\s+", re.M)
_NUMBERED = re.compile(r"^\s*\d+[.)]\s+", re.M)


def _domain_of(url: str, *, lang: str = "pt") -> str:
    try:
        host = urlparse(url).netloc or ""
        host = host.removeprefix("www.")
        if host:
            return host
    except Exception:
        pass
    return "external link" if lang.startswith("en") else "ligacao externa"


def prepare_speech_text(
    text: str,
    max_chars: int = _MAX_TTS_CHARS,
    *,
    lang: str = "pt",
) -> str:
    """
    Normalize text for TTS without changing the written reply elsewhere.

    Strips markdown/code, turns short lists into spoken phrases, replaces
    long URLs with a domain mention, and truncates softly at sentence bounds.
    """
    cleaned = (text or "").strip()
    if not cleaned:
        return ""

    lang_key = (lang or "pt").lower()
    if lang_key.startswith("en"):
        url_fmt = "link to {domain}"
    else:
        url_fmt = "ligacao a {domain}"

    cleaned = re.sub(r"```.*?```", " ", cleaned, flags=re.DOTALL)
    cleaned = _MD_HEADING.sub("", cleaned)
    cleaned = re.sub(r"\*\*([^*]+)\*\*", r"\1", cleaned)
    cleaned = re.sub(r"\*([^*]+)\*", r"\1", cleaned)
    cleaned = re.sub(r"`([^`]+)`", r"\1", cleaned)
    cleaned = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", cleaned)

    cleaned = _URL_RE.sub(
        lambda m: url_fmt.format(domain=_domain_of(m.group(0), lang=lang_key)),
        cleaned,
    )

    # Convert list-like lines into spoken clauses
    lines = cleaned.splitlines()
    spoken_parts: list[str] = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        line = _LIST_ITEM.sub("", line)
        line = _NUMBERED.sub("", line)
        spoken_parts.append(line)
    cleaned = ". ".join(spoken_parts) if spoken_parts else cleaned

    cleaned = re.sub(r"[#|_~<>{}]", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    cleaned = re.sub(r"\s+([,.!?;:])", r"\1", cleaned)
    cleaned = re.sub(r"\.{2,}", ".", cleaned)

    if len(cleaned) <= max_chars:
        return cleaned

    cut = cleaned[:max_chars]
    for sep in (". ", "? ", "! ", "; "):
        idx = cut.rfind(sep)
        if idx > max_chars // 2:
            return cut[: idx + 1].strip()
    return cut[: max_chars - 3].rstrip() + "..."
