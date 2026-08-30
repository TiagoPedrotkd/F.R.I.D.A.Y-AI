"""Chunk extracted repo documents for RAG with provenance."""

from __future__ import annotations

from typing import Any

from friday_llm.util import content_hash, estimate_tokens


def _split_paragraphs(text: str) -> list[str]:
    parts = [p.strip() for p in text.split("\n\n") if p.strip()]
    return parts or [text.strip()]


def chunk_document(
    doc: dict[str, Any],
    *,
    chunk_chars: int = 2000,
    chunk_overlap: int = 200,
) -> list[dict[str, Any]]:
    text = str(doc.get("text") or "")
    if not text:
        return []
    title = str(doc.get("title") or doc.get("document_id") or "untitled")
    source = str(doc.get("source") or "repo_docs")
    url_or_id = str(doc.get("url_or_path") or doc.get("url") or doc.get("document_id") or "")
    captured = str(doc.get("captured_at_or_version") or doc.get("captured_at") or "git")
    language = str(doc.get("language") or "pt")
    permissions = str(doc.get("permissions") or "project_docs")
    license_name = str(doc.get("license") or "Apache-2.0")

    chunks: list[dict[str, Any]] = []
    buffer = ""
    chunk_idx = 0
    for para in _split_paragraphs(text):
        candidate = f"{buffer}\n\n{para}".strip() if buffer else para
        if len(candidate) <= chunk_chars:
            buffer = candidate
            continue
        if buffer:
            chunk_idx += 1
            chunks.append(
                _chunk_row(
                    text=buffer,
                    title=title,
                    source=source,
                    url_or_id=url_or_id,
                    captured=captured,
                    language=language,
                    permissions=permissions,
                    license_name=license_name,
                    chunk_idx=chunk_idx,
                    parent_id=str(doc.get("document_id") or ""),
                )
            )
            overlap = buffer[-chunk_overlap:] if chunk_overlap else ""
            buffer = f"{overlap}\n\n{para}".strip() if overlap else para
        else:
            # Very long paragraph — hard split
            start = 0
            while start < len(para):
                piece = para[start : start + chunk_chars]
                chunk_idx += 1
                chunks.append(
                    _chunk_row(
                        text=piece,
                        title=title,
                        source=source,
                        url_or_id=url_or_id,
                        captured=captured,
                        language=language,
                        permissions=permissions,
                        license_name=license_name,
                        chunk_idx=chunk_idx,
                        parent_id=str(doc.get("document_id") or ""),
                    )
                )
                start += max(1, chunk_chars - chunk_overlap)
            buffer = ""

    if buffer.strip():
        chunk_idx += 1
        chunks.append(
            _chunk_row(
                text=buffer.strip(),
                title=title,
                source=source,
                url_or_id=url_or_id,
                captured=captured,
                language=language,
                permissions=permissions,
                license_name=license_name,
                chunk_idx=chunk_idx,
                parent_id=str(doc.get("document_id") or ""),
            )
        )
    return chunks


def _chunk_row(
    *,
    text: str,
    title: str,
    source: str,
    url_or_id: str,
    captured: str,
    language: str,
    permissions: str,
    license_name: str,
    chunk_idx: int,
    parent_id: str,
) -> dict[str, Any]:
    return {
        "text": text,
        "title": title,
        "source": source,
        "url_or_document_id": url_or_id,
        "captured_at_or_version": captured,
        "language": language,
        "permissions": permissions,
        "license": license_name,
        "content_hash": content_hash(text),
        "metadata": {
            "chunk_index": chunk_idx,
            "parent_document_id": parent_id,
            "estimated_tokens": estimate_tokens(text),
        },
    }


def chunk_documents(
    docs: list[dict[str, Any]],
    *,
    chunk_chars: int = 2000,
    chunk_overlap: int = 200,
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for doc in docs:
        out.extend(
            chunk_document(doc, chunk_chars=chunk_chars, chunk_overlap=chunk_overlap)
        )
    return out
