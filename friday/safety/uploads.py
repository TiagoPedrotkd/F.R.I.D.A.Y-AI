"""Upload validation: magic bytes, quotas, safe metadata."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

_SAFE_NAME = re.compile(r"[^A-Za-z0-9._\- ]+")

# (magic, mime, kind, extensions)
_SIGNATURES: list[tuple[bytes, str, str, tuple[str, ...]]] = [
    (b"\x89PNG\r\n\x1a\n", "image/png", "image", (".png",)),
    (b"\xff\xd8\xff", "image/jpeg", "image", (".jpg", ".jpeg")),
    (b"GIF87a", "image/gif", "image", (".gif",)),
    (b"GIF89a", "image/gif", "image", (".gif",)),
    (b"RIFF", "image/webp", "image", (".webp",)),  # need WEBP at offset 8
    (b"%PDF", "application/pdf", "pdf", (".pdf",)),
]


@dataclass
class ValidatedUpload:
    kind: str
    mime: str
    filename: str
    extracted: str
    vision: bool = False


def safe_filename(name: str) -> str:
    raw = Path(name or "upload.bin").name
    cleaned = _SAFE_NAME.sub("", raw).strip()[:120]
    return cleaned or "upload.bin"


def detect_kind(data: bytes, filename: str, content_type: str | None) -> tuple[str, str]:
    """Return (kind, mime) from magic bytes; fall back to extension/content-type."""
    name = filename.casefold()
    ct = (content_type or "").split(";")[0].strip().casefold()

    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image", "image/png"
    if data.startswith(b"\xff\xd8\xff"):
        return "image", "image/jpeg"
    if data.startswith(b"GIF87a") or data.startswith(b"GIF89a"):
        return "image", "image/gif"
    if len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image", "image/webp"
    if data.startswith(b"%PDF"):
        return "pdf", "application/pdf"

    # Text: printable UTF-8 / ASCII dominance
    if name.endswith((".txt", ".md", ".csv", ".json", ".py")) or ct.startswith("text/"):
        return "text", ct or "text/plain"
    if name.endswith((".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp")):
        # Client claimed image but magic failed — reject as binary
        return "file", ct or "application/octet-stream"
    if name.endswith(".pdf") or ct == "application/pdf":
        return "file", ct or "application/octet-stream"
    return "file", ct or "application/octet-stream"


def extract_text_payload(data: bytes, kind: str, filename: str) -> str:
    if kind == "text":
        return data.decode("utf-8", errors="replace")[:12000]
    if kind == "pdf":
        return _extract_pdf(data, filename)
    if kind == "image":
        return f"[Imagem pronta para vision: {filename}]"
    return f"[Ficheiro anexado: {filename}]"


def _extract_pdf(data: bytes, filename: str) -> str:
    try:
        from pypdf import PdfReader  # type: ignore
        import io

        reader = PdfReader(io.BytesIO(data))
        parts: list[str] = []
        for page in reader.pages[:20]:
            t = page.extract_text() or ""
            if t.strip():
                parts.append(t.strip())
        text = "\n".join(parts).strip()
        if text:
            return text[:8000]
    except Exception:
        pass
    # Fallback: avoid latin-1 garbage dump
    return f"[PDF anexado: {filename} — texto nao extraido]"


def session_upload_bytes(upload_dir: Path) -> int:
    if not upload_dir.is_dir():
        return 0
    total = 0
    for p in upload_dir.rglob("*"):
        if p.is_file():
            try:
                total += p.stat().st_size
            except OSError:
                pass
    return total
