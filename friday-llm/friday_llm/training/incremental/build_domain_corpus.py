"""Build a small domain CPT JSONL from repo markdown docs."""

from __future__ import annotations

import argparse
import re
from pathlib import Path

from friday_llm.util import content_hash, resolve_path, write_jsonl

_DEFAULT_GLOBS = (
    "docs/**/*.md",
    "friday-llm/docs/**/*.md",
    "README.md",
    "friday-llm/README.md",
)


def _chunk_markdown(text: str, *, max_chars: int = 2500) -> list[str]:
    parts = re.split(r"\n(?=#{1,3} )", text.strip())
    chunks: list[str] = []
    buf = ""
    for part in parts:
        part = part.strip()
        if not part:
            continue
        if len(buf) + len(part) + 2 <= max_chars:
            buf = f"{buf}\n\n{part}".strip() if buf else part
        else:
            if buf:
                chunks.append(buf)
            if len(part) <= max_chars:
                buf = part
            else:
                for i in range(0, len(part), max_chars):
                    chunks.append(part[i : i + max_chars])
                buf = ""
    if buf:
        chunks.append(buf)
    return chunks


def build_domain_corpus(
    *,
    repo_root: Path | None = None,
    out_path: str = "friday-llm/data/pretraining/incremental/domain_docs.jsonl",
    globs: tuple[str, ...] = _DEFAULT_GLOBS,
) -> dict:
    root = repo_root or resolve_path(".")
    rows: list[dict] = []
    seen: set[str] = set()
    for pattern in globs:
        for path in sorted(root.glob(pattern)):
            if not path.is_file():
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except OSError:
                continue
            rel = str(path.relative_to(root)).replace("\\", "/")
            for i, chunk in enumerate(_chunk_markdown(text)):
                h = content_hash(f"{rel}:{i}:{chunk}")
                if h in seen:
                    continue
                seen.add(h)
                rows.append(
                    {
                        "text": chunk,
                        "content_hash": h,
                        "source": "repo_docs",
                        "path": rel,
                        "chunk": i,
                    }
                )
    out = resolve_path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    write_jsonl(out, rows)
    return {"out": str(out), "docs": len(rows)}


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser()
    p.add_argument(
        "--out",
        default="friday-llm/data/pretraining/incremental/domain_docs.jsonl",
    )
    args = p.parse_args(argv)
    summary = build_domain_corpus(out_path=args.out)
    print(summary)


if __name__ == "__main__":
    main()
