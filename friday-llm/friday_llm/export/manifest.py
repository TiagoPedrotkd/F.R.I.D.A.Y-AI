"""Write export manifest with adapter, merged HF, and GGUF hashes."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from friday_llm.util import resolve_path


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _hash_dir_files(root: Path) -> list[dict[str, Any]]:
    files: list[dict[str, Any]] = []
    if not root.is_dir():
        return files
    for p in sorted(root.rglob("*")):
        if not p.is_file():
            continue
        try:
            rel = str(p.relative_to(resolve_path(".")))
        except ValueError:
            rel = str(p)
        files.append(
            {
                "path": rel,
                "bytes": p.stat().st_size,
                "sha256": file_sha256(p),
            }
        )
    return files


def _gguf_entries(gguf_files: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for item in gguf_files or []:
        p = resolve_path(item.get("path") or "")
        if not p.is_file():
            continue
        entries.append(
            {
                "path": str(p),
                "quant": item.get("quant"),
                "bytes": p.stat().st_size,
                "sha256": file_sha256(p),
            }
        )
    return entries


def build_manifest(
    adapter_dir: str,
    *,
    run_id: str = "fase2-pilot",
    merged_hf_dir: str | Path | None = None,
    gguf_files: list[dict[str, Any]] | None = None,
    gguf_status: str | None = None,
    base_model: str | None = None,
    production_model: str = "microsoft/phi-4",
    manifest_path: str | Path | None = None,
) -> dict:
    root = resolve_path(adapter_dir)
    adapter_files = _hash_dir_files(root)
    gguf_entries = _gguf_entries(gguf_files)

    if gguf_status is None:
        if gguf_entries:
            gguf_status = "converted"
        else:
            gguf_status = "not_converted"

    suggested_id = None
    for g in gguf_entries:
        if g.get("quant") == "Q4_K_M":
            suggested_id = Path(str(g["path"])).stem
            break
    if not suggested_id and gguf_entries:
        suggested_id = Path(str(gguf_entries[0]["path"])).stem

    manifest = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "run_id": run_id,
        "adapter_dir": str(root),
        "merged_hf_dir": str(resolve_path(merged_hf_dir)) if merged_hf_dir else None,
        "base_model": base_model,
        "gguf_files": gguf_entries,
        "gguf_status": gguf_status,
        "production_model_unchanged": True,
        "lm_studio_default": production_model,
        "rollback": {
            "env_var": "LM_STUDIO_MODEL",
            "production_value": production_model,
            "candidate_suggested_id": suggested_id,
        },
        "files": adapter_files,
        "notes": (
            "GGUF conversion requires llama.cpp locally. "
            "Do not auto-switch LM_STUDIO_MODEL."
        ),
    }
    out = resolve_path(manifest_path or "friday-llm/reports/export_manifest.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser()
    p.add_argument(
        "--adapter",
        default="friday-llm/checkpoints/sft-fase2-pilot/adapter",
    )
    p.add_argument("--run-id", default="fase2-pilot")
    p.add_argument("--merged", default="")
    p.add_argument("--gguf-dir", default="")
    args = p.parse_args(argv)
    gguf_files = None
    gguf_status = None
    if args.gguf_dir:
        gdir = resolve_path(args.gguf_dir)
        if gdir.is_dir():
            gguf_files = [{"path": str(p), "quant": p.stem.split("-")[-1]} for p in gdir.glob("*.gguf")]
            gguf_status = "converted" if gguf_files else "not_converted"
    print(
        json.dumps(
            build_manifest(
                args.adapter,
                run_id=args.run_id,
                merged_hf_dir=args.merged or None,
                gguf_files=gguf_files,
                gguf_status=gguf_status,
            ),
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
