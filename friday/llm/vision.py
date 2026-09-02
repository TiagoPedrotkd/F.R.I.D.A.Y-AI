"""Vision / multimodal helpers for OpenAI-compatible LM Studio APIs."""

from __future__ import annotations

import base64
import mimetypes
from pathlib import Path
from typing import Any

_IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp"}

# Heuristic names for VLM ids exposed by LM Studio / Ollama
_VISION_HINTS = (
    "llava",
    "bakllava",
    "vision",
    "vl-",
    "-vl",
    "qwen2-vl",
    "qwen2.5-vl",
    "qwen-vl",
    "pixtral",
    "phi-3-vision",
    "phi-3.5-vision",
    "phi-4-multimodal",
    "phi-4-mini-reasoning",
    "gemma-3",
    "gemma3",
    "minicpm-v",
    "minicpm_v",
    "moondream",
    "internvl",
    "idefics",
    "cogvlm",
)


def is_image_path(path: str | Path) -> bool:
    return Path(path).suffix.casefold() in _IMAGE_EXTS


def guess_mime(path: str | Path, content_type: str | None = None) -> str:
    if content_type and content_type.startswith("image/"):
        return content_type.split(";")[0].strip()
    guessed, _ = mimetypes.guess_type(str(path))
    if guessed and guessed.startswith("image/"):
        return guessed
    ext = Path(path).suffix.casefold()
    return {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp",
        ".gif": "image/gif",
        ".bmp": "image/bmp",
    }.get(ext, "image/png")


def image_to_data_url(path: str | Path, *, mime: str | None = None) -> str:
    p = Path(path)
    raw = p.read_bytes()
    mt = mime or guess_mime(p)
    b64 = base64.b64encode(raw).decode("ascii")
    return f"data:{mt};base64,{b64}"


def looks_like_vision_model(model_id: str) -> bool:
    low = (model_id or "").casefold()
    return any(h in low for h in _VISION_HINTS)


# Prefer smaller / common local VLMs first on consumer GPUs (e.g. RTX 3060 12GB)
_VISION_PREF_ORDER = (
    "moondream",
    "qwen2-vl-2b",
    "qwen2.5-vl-3b",
    "minicpm-v",
    "llava-phi",
    "llava",
    "qwen2-vl",
    "qwen2.5-vl",
    "pixtral",
    "phi-3.5-vision",
    "phi-4-multimodal",
    "gemma-3",
    "internvl",
)


def pick_vision_model(
    available: list[str],
    *,
    preferred: str = "",
    fallback: str = "",
) -> str | None:
    """Pick a vision-capable model id from loaded server models."""
    pref = (preferred or "").strip()
    if pref:
        return pref
    # Prefer already-loaded smaller VLMs
    scored: list[tuple[int, str]] = []
    for mid in available:
        if not looks_like_vision_model(mid):
            continue
        low = mid.casefold()
        rank = 50
        for i, hint in enumerate(_VISION_PREF_ORDER):
            if hint in low:
                rank = i
                break
        scored.append((rank, mid))
    if scored:
        scored.sort(key=lambda x: (x[0], len(x[1])))
        return scored[0][1]
    fb = (fallback or "").strip()
    if fb and looks_like_vision_model(fb):
        return fb
    return None


def build_user_content(
    text: str,
    attachments: list[dict[str, Any]] | None,
) -> str | list[dict[str, Any]]:
    """
    Build OpenAI multimodal user content.
    Text-only when there are no image attachments.
    """
    images = [
        a
        for a in (attachments or [])
        if str(a.get("kind") or "").casefold() == "image" and a.get("path")
    ]
    if not images:
        return text

    parts: list[dict[str, Any]] = []
    body = (text or "").strip() or "Descreve e analisa a imagem anexada."
    parts.append({"type": "text", "text": body})
    for att in images:
        path = Path(str(att["path"]))
        if not path.is_file():
            parts.append(
                {
                    "type": "text",
                    "text": f"[Imagem em falta: {att.get('filename') or path.name}]",
                }
            )
            continue
        try:
            url = image_to_data_url(path, mime=att.get("mime"))
        except OSError:
            parts.append(
                {
                    "type": "text",
                    "text": f"[Nao consegui ler a imagem: {att.get('filename') or path.name}]",
                }
            )
            continue
        parts.append({"type": "image_url", "image_url": {"url": url}})
    return parts


def attachment_memory_note(attachments: list[dict[str, Any]] | None) -> str:
    """Short text note for STM history after a multimodal turn."""
    if not attachments:
        return ""
    bits: list[str] = []
    for a in attachments:
        kind = str(a.get("kind") or "file")
        name = str(a.get("filename") or Path(str(a.get("path") or "anexo")).name)
        bits.append(f"[{kind}: {name}]")
    return " ".join(bits)
